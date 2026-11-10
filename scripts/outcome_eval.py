"""Outcome eval: did the AI's strategies contain the amendment that really got the claim granted?

No hand-written rubric. The answer is what happened (data/precedents: claim before/after the
first response, and whether the next examiner action granted or refused it).

uv run python scripts/outcome_eval.py prepare --limit 30     # inputs → data/eval/outcome/cases.jsonl
uv run python scripts/outcome_eval.py run --label sonnet     # AI strategies for claim 1
uv run python scripts/outcome_eval.py grade sonnet           # judge + 3 levels vs. majority guess

Levels: 1 amend-or-argue, 2 how (dependent-claim merge / specification feature / argue only),
3 the actually added feature is in one of the AI's strategies. Refused amendments count against
level 3 ("recommended the amendment that failed").
"""

import argparse
import html
import json
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path

import anthropic
import httpx
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_gold_cases import UA, google_publication  # noqa: E402

from backend.config import Settings  # noqa: E402
from backend.errors import DocumentError, ProviderError  # noqa: E402
from backend.improvements.models import ImprovementRequest  # noqa: E402
from backend.improvements.service import generate_improvement  # noqa: E402
from backend.jurisdictions.korean import analyze_korean  # noqa: E402
from backend.precedents import repository  # noqa: E402
from backend.precedents.kipris import (  # noqa: E402
    PUBLICATION_SERVICE,
    Kipris,
    KiprisError,
)

OUT = ROOT / "data/eval/outcome"
INPUTS = OUT / "inputs"
RUNS = ROOT / "data/outputs/outcome_runs"
# Rubric gold cases and prompt-v2 examples stay out: they are judged elsewhere or seen by the model.
SKIP = {p.stem for p in (ROOT / "data/eval/kr").glob("*.json")} | {"1020140003628", "1020140002563"}
METHOD = {"none": "argue", "dependent_merge": "merge", "spec_limitation": "spec"}


def squash(text):
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", text or "")))


def claim(text, number=1):
    """One claim out of '[청구항 1] … [청구항 2] …'."""
    m = re.search(rf"\[청구항\s*{number}\]\s*(.*?)(?=\[청구항\s*\d+\]|$)", text or "", re.S)
    return m[1].strip() if m else ""


def candidates():
    """First-response cases on novelty / inventive step with claim 1 changed or argued."""
    rows = [
        c
        for c in repository.real_cases()
        if str(c.get("round")) == "1"
        and c["category"] in {"inventive_step", "novelty"}
        and c["outcome"] in {"resolved", "unresolved"}
        and c.get("response_method") in METHOD
        and c["application"] not in SKIP
        and claim(c.get("claims_before"))
    ]
    one = {}
    for c in sorted(rows, key=lambda c: c["case_id"]):
        one.setdefault(c["application"], c)  # several statutes per notice → one case per app
    return list(one.values())


def publication_pdf(api, app):
    """공개공보 full text for an application number (one counted call, then cached)."""
    path = api.cache / "pdf" / f"PUB_{app}.pdf"
    if path.exists():
        return path
    try:
        text = api._publication("getPubFullTextInfoSearch", {"applicationNumber": app}, app)
    except KiprisError:
        text = ""  # every key out of quota or not subscribed to 공보
    url = re.search(r"<path>([^<]+)</path>", text)
    if not url:
        # Same A publication from Google Patents (as build_gold_cases.py does), no KIPRIS quota.
        try:
            _, pdf_url = google_publication(app)
            content = httpx.get(pdf_url, headers=UA, timeout=60).content
        except (RuntimeError, KeyError, IndexError, ValueError, httpx.HTTPError) as exc:
            raise KiprisError(f"공개공보 전문 없음 (KIPRIS·Google Patents): {exc}") from exc
        if not content.startswith(b"%PDF"):
            raise KiprisError("Google Patents 응답이 PDF가 아닙니다.")
        path.write_bytes(content)
        return path
    try:
        return Path(api.document_pdf(html.unescape(url[1]), f"PUB_{app}"))
    except KiprisError:
        (api.cache / PUBLICATION_SERVICE / "getPubFullTextInfoSearch" / f"{app}.xml").unlink(
            missing_ok=True
        )
        raise


def first_claim_from_pdf(path):
    import pymupdf

    text = "".join(p.get_text() for p in pymupdf.open(path))
    m = re.search(r"청구항\s*1\s*\n(.*?)(?:\n\s*청구항\s*2\s*\n|\n\s*발명의\s*설명)", text, re.S)
    return m[1] if m else ""


def notice_pdf(api, case):
    notices = api.items("OP", "advancedSearchInfo", case["application"])
    date = case["oa_date"].replace("-", "")
    match = [n for n in notices if n["sendDate"] == date] or sorted(
        notices, key=lambda n: n["sendDate"]
    )[:1]
    first = match[0]
    return Path(
        api.document_pdf(first["filePath"], f"OP_{case['application']}_{first['sendNumber']}")
    )


def prepare(args):
    api = Kipris()
    pool = candidates()
    random.Random(0).shuffle(pool)
    done = {}
    path = OUT / "cases.jsonl"
    if path.exists():
        done = {r["application"]: r for r in map(json.loads, path.open(encoding="utf-8"))}
    # Balanced by real response, granted first: refused ones only check "don't repeat the failure".
    order = sorted(pool, key=lambda c: (c["outcome"] != "resolved",))
    by_kind = {}
    for c in order:
        by_kind.setdefault((c["outcome"], c["response_method"]), []).append(c)
    picked = []
    while len(picked) < len(pool):
        for kind in sorted(by_kind):
            if by_kind[kind]:
                picked.append(by_kind[kind].pop(0))
    picked.sort(key=lambda c: c["outcome"] != "resolved")
    OUT.mkdir(parents=True, exist_ok=True)
    ok = sum(1 for r in done.values() if r.get("ok"))
    for case in picked:
        if ok >= args.limit:
            break
        app = case["application"]
        if app in done and not re.search(
            r"오류 (?:22|31)|한도|전문 없음$", done[app].get("skip", "")
        ):
            continue  # quota / missing-publication refusals are retried (next key, Google Patents)
        record = {"application": app, "case_id": case["case_id"], "ok": False}
        try:
            pub = publication_pdf(api, app)
            if (
                squash(first_claim_from_pdf(pub))[:120]
                != squash(claim(case["claims_before"]))[:120]
            ):
                record["skip"] = "공개공보 청구항 1이 거절 당시 청구항 1과 다름 (자진보정)"
            else:
                oa = notice_pdf(api, case)
                record |= {
                    "ok": True,
                    "patent": str(pub.relative_to(ROOT)).replace("\\", "/"),
                    "office_action": str(oa.relative_to(ROOT)).replace("\\", "/"),
                    "category": case["category"],
                    "oa_date": case["oa_date"],
                    "outcome": case["outcome"],
                    "method": METHOD[case["response_method"]],
                    "claim_before": claim(case["claims_before"]),
                    "claim_after": claim(case["claims_after"]),
                }
                ok += 1
        except (KiprisError, KeyError, IndexError) as exc:
            record["skip"] = f"KIPRIS: {exc}"
        done[app] = record
        print(app, "ok" if record["ok"] else record["skip"], flush=True)
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in done.values()),
            encoding="utf-8",
        )
    print(f"usable {ok} / tried {len(done)} / pool {len(pool)}")


def cases():
    return [r for r in map(json.loads, (OUT / "cases.jsonl").open(encoding="utf-8")) if r["ok"]]


def run_one(case, settings):
    patent, oa = ROOT / case["patent"], ROOT / case["office_action"]
    try:
        result = analyze_korean(
            patent.read_bytes(), patent.name, oa.read_bytes(), oa.name, settings.max_document_chars
        )
    except DocumentError as exc:
        return {"ok": False, "error": "analysis: " + str(exc)}
    # The model must never see this application's own later outcome as a "similar case".
    for document in result.documents:
        document.source_metadata["application_number"] = case["application"]
    rejected = {n for r in result.rejections if r.action_type == "rejection" for n in r.claims}
    if 1 not in rejected:
        return {"ok": False, "error": "analysis: 청구항 1이 거절 대상으로 추출되지 않음"}
    try:
        response = generate_improvement(
            ImprovementRequest(analysis=result, claim_number=1, require_llm=True), settings
        )
    except (ProviderError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "strategies": [
            {k: s[k] for k in ("action_type", "title", "description", "target_elements")}
            for s in response.suggestion.model_dump()["strategies"]
        ],
        "example": response.suggestion.optional_example.text,
    }


def ran_ok(label):
    """Applications another run analysed and answered (to compare models on the same cases)."""
    return {
        r["application"]
        for r in (json.loads(p.read_text(encoding="utf-8")) for p in (RUNS / label).glob("1*.json"))
        if r["ok"]
    }


def run(args):
    settings = Settings()
    out = RUNS / args.label
    out.mkdir(parents=True, exist_ok=True)
    todo = cases()
    if args.like:
        todo = [c for c in todo if c["application"] in ran_ok(args.like)]
    for case in todo[: args.limit or None]:
        path = out / f"{case['application']}.json"
        if path.exists():
            continue
        started = time.time()
        record = {"application": case["application"]} | run_one(case, settings)
        record["seconds"] = round(time.time() - started)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(
            case["application"],
            record.get("error") or f"{len(record['strategies'])} strategies",
            flush=True,
        )


class StrategyVerdict(BaseModel):
    index: int
    kind: str  # argue | merge | spec | other
    match: str  # same | partial | none
    reason: str


class Verdict(BaseModel):
    strategies: list[StrategyVerdict]


JUDGE = """한국 특허 의견제출통지서에 대한 AI 대응 전략을 실제 출원인의 대응과 비교합니다.

[거절 당시 청구항 1]
{before}

[실제 출원인이 제출한 청구항 1]
{after}

[AI 전략들]
{strategies}

각 AI 전략마다 판단하세요.
- kind: "argue"(청구항을 바꾸지 않고 반박), "merge"(기존 종속항의 구성을 독립항에 합침),
  "spec"(명세서의 구성을 새로 추가해 한정), "other"(명확화 등 그 밖의 보정).
- match: 이 전략이 추가하자는 구성을 실제 출원인이 청구항 1에 추가한 기술적 구성과 비교.
  "same": 표현이 달라도 실질적으로 같은 기술 내용. "partial": 같은 구성요소를 같은 방향으로 구체화하지만
  핵심 한정(수치·관계·구조 등)이 다름. "none": 다른 구성이거나 반박만이라 추가하는 구성이 없음.
- reason: 한 문장."""


def judge(client, case, record):
    listing = "\n\n".join(
        f"{i}. [{s['action_type']}] {s['title']}\n{s['description']}"
        for i, s in enumerate(record["strategies"])
    )
    response = client.messages.parse(
        model="claude-sonnet-5-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": JUDGE.format(
                    before=case["claim_before"], after=case["claim_after"], strategies=listing
                ),
            }
        ],
        output_format=Verdict,
    )
    return [v.model_dump() for v in response.parsed_output.strategies]


def grade(args):
    client = anthropic.Anthropic(api_key=Settings().anthropic_api_key or None)
    out = RUNS / args.label
    rows = []
    only = ran_ok(args.like) if args.like else None
    for case in cases():
        path = out / f"{case['application']}.json"
        if not path.exists() or (only is not None and case["application"] not in only):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if not record["ok"]:
            rows.append({"case": case, "error": record["error"]})
            continue
        if "verdicts" not in record:
            record["verdicts"] = judge(client, case, record)
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        rows.append({"case": case, "verdicts": record["verdicts"]})
    report(rows, args.label)


def report(rows, label):
    graded = [r for r in rows if "verdicts" in r and r["verdicts"]]
    granted = [r for r in graded if r["case"]["outcome"] == "resolved"]
    refused = [r for r in graded if r["case"]["outcome"] == "unresolved"]

    def top(r):
        return r["verdicts"][0]["kind"]

    def amend(kind):
        return "argue" if kind == "argue" else "amend"

    lv1 = sum(amend(top(r)) == amend(r["case"]["method"]) for r in granted)
    lv2 = sum(top(r) == r["case"]["method"] for r in granted)
    amended = [r for r in granted if r["case"]["method"] != "argue"]

    def hit(r, levels):
        return any(v["match"] in levels for v in r["verdicts"][:3])

    lv3 = sum(hit(r, {"same"}) for r in amended)
    lv3_partial = sum(hit(r, {"same", "partial"}) for r in amended)
    repeat = sum(hit(r, {"same"}) for r in refused if r["case"]["method"] != "argue")
    methods = Counter(r["case"]["method"] for r in granted)
    guess1 = max(Counter(amend(m) for m in methods.elements()).values(), default=0)
    guess2 = max(methods.values(), default=0)

    def pct(a, b):
        return f"{a}/{b} = {100 * a / b:.0f}%" if b else "-"

    summary = {
        "label": label,
        "cases": len(rows),
        "failed": [r["case"]["application"] + ": " + r["error"] for r in rows if "error" in r],
        "granted": len(granted),
        "level1_amend_or_argue": pct(lv1, len(granted)),
        "level1_majority_guess": pct(guess1, len(granted)),
        "level2_how": pct(lv2, len(granted)),
        "level2_majority_guess": pct(guess2, len(granted)),
        "level3_granted_feature_in_top3": pct(lv3, len(amended)),
        "level3_same_or_partial": pct(lv3_partial, len(amended)),
        "refused_feature_repeated_in_top3": pct(
            repeat, sum(r["case"]["method"] != "argue" for r in refused)
        ),
        "granted_methods": dict(methods),
    }
    (RUNS / label / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=prepare)
    p = sub.add_parser("run")
    p.add_argument("--label", required=True)
    p.add_argument("--like", help="only cases this earlier label answered (same-case comparison)")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=run)
    p = sub.add_parser("grade")
    p.add_argument("label")
    p.add_argument("--like", help="grade only the cases this other label answered")
    p.set_defaults(func=grade)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
