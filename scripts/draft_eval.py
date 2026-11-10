"""Draft (의견서) quality against the applicant's real 의견서 (OPD PDFs, kr_opinions.jsonl).

uv run python scripts/draft_eval.py prepare --limit 30   # inputs → data/eval/drafts/cases.jsonl
uv run python scripts/draft_eval.py run --label sonnet    # AI draft for the real direction
uv run python scripts/draft_eval.py grade sonnet          # judge vs. the real 의견서

The selection given to the AI is only the real direction (반박 / 반박과 보정), never the real
argument. Scores follow PatRe (2026): soundness, completeness, constructiveness, clarity,
style (1-10), plus whether the draft makes the applicant's core argument. A draft the
validators refuse counts as a failure (pass rate is reported).
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import anthropic
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from outcome_eval import (  # noqa: E402
    claim,
    first_claim_from_pdf,
    notice_pdf,
    publication_pdf,
    squash,
)

from backend.config import Settings  # noqa: E402
from backend.errors import DocumentError, ProviderError  # noqa: E402
from backend.improvements.opinion import Selection, generate_from_selection  # noqa: E402
from backend.jurisdictions.korean import analyze_korean  # noqa: E402
from backend.precedents import repository  # noqa: E402
from backend.precedents.kipris import Kipris, KiprisError  # noqa: E402
from backend.precedents.taxonomy import categorize  # noqa: E402

OUT = ROOT / "data/eval/drafts"
RUNS = ROOT / "data/outputs/draft_runs"
SKIP = {p.stem for p in (ROOT / "data/eval/kr").glob("*.json")} | {"1020140003628", "1020140002563"}


def prepare(args):
    api = Kipris()
    path = OUT / "cases.jsonl"
    done = {}
    if path.exists():
        done = {r["case_id"]: r for r in map(json.loads, path.open(encoding="utf-8"))}
    pool = [
        c
        for c in repository.real_cases()
        if c.get("opinion_text")
        and c.get("claims_before")
        and c["category"] in {"inventive_step", "novelty"}
        and c["application"] not in SKIP
    ]
    seen_apps = {r["application"] for r in done.values()}
    ok = sum(r["ok"] for r in done.values())
    OUT.mkdir(parents=True, exist_ok=True)
    for case in pool:
        if ok >= args.limit:
            break
        if case["case_id"] in done or case["application"] in seen_apps:
            continue
        app = case["application"]
        seen_apps.add(app)
        record = {"case_id": case["case_id"], "application": app, "ok": False}
        try:
            pub = publication_pdf(api, app)
            if str(case["round"]) == "1" and (
                squash(first_claim_from_pdf(pub))[:120]
                != squash(claim(case["claims_before"]))[:120]
            ):
                record["skip"] = "공개공보 청구항 1이 통지 당시와 다름"
            else:
                oa = notice_pdf(api, case)
                record |= {
                    "ok": True,
                    "patent": str(pub.relative_to(ROOT)).replace("\\", "/"),
                    "office_action": str(oa.relative_to(ROOT)).replace("\\", "/"),
                    "category": case["category"],
                    "direction": "반박" if case.get("response_method") == "none" else "반박과 보정",
                    "outcome": case["outcome"],
                }
                ok += 1
        except (KiprisError, KeyError, IndexError) as exc:
            record["skip"] = str(exc)[:200]
        done[case["case_id"]] = record
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
            patent.read_bytes(),
            patent.name,
            oa.read_bytes(),
            oa.name,
            settings.max_document_chars,
            fetch_citations=settings.kipris_fetch_citations,  # as the app does
        )
    except DocumentError as exc:
        return {"ok": False, "error": "analysis: " + str(exc)}
    for document in result.documents:
        document.source_metadata["application_number"] = case["application"]
    rejection = next(
        (
            r
            for r in result.rejections
            if r.action_type == "rejection"
            and 1 in r.claims
            and categorize(r.statute, None, r.examiner_explanation) == case["category"]
        ),
        None,
    )
    if rejection is None:
        return {"ok": False, "error": "analysis: 해당 유형의 청구항 1 거절이유를 찾지 못함"}
    selection = Selection(
        claim_number=1,
        rejection_id=rejection.rejection_id,
        direction=case["direction"],
        confirmed_by="draft_eval",
    )
    try:
        response, model = generate_from_selection(result, selection, settings)
    except (ProviderError, ValueError) as exc:
        return {"ok": False, "error": "draft: " + str(exc)}
    return {"ok": True, "model": model, "draft": response.draft.model_dump(mode="json")}


def run(args):
    settings = Settings()
    out = RUNS / args.label
    out.mkdir(parents=True, exist_ok=True)
    for case in cases()[: args.limit or None]:
        path = out / f"{case['application']}.json"
        if path.exists():
            continue
        started = time.time()
        record = {"case_id": case["case_id"]} | run_one(case, settings)
        record["seconds"] = round(time.time() - started)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(case["application"], record.get("error", "ok")[:100], flush=True)


class Scores(BaseModel):
    soundness: int
    completeness: int
    constructiveness: int
    clarity: int
    style: int


class Verdict(BaseModel):
    ai: Scores
    actual: Scores
    core_argument: str  # same | partial | none
    preferred: str  # ai | actual | tie
    reason: str


JUDGE = """한국 특허 의견제출통지서에 대한 의견서 두 개를 평가합니다. A는 AI 초안, B는 실제 출원인의 의견서입니다.
같은 거절이유(청구항 1, {category})에 대한 대응이며 A는 통지 당시 자료만 보고 작성했습니다.

[A: AI 초안]
{draft}

[B: 실제 의견서 (발췌)]
{actual}

각 의견서를 1~10점으로 채점하세요 (PatRe 기준).
- soundness: 기술·법리 논증이 타당하고 사실과 맞는가
- completeness: 거절이유의 논점을 빠짐없이 다루는가
- constructiveness: 보정/주장이 거절 극복에 실질적으로 도움이 되는가
- clarity: 구조와 논리가 명확한가
- style: 한국 의견서의 문체·형식에 맞는가
core_argument: A가 B의 핵심 주장(인용발명과의 핵심 차이, 보정 방향)과 같은 논리를 펴는가 — "same" | "partial" | "none".
preferred: 변리사라면 어느 쪽을 출발점으로 삼겠는가 — "ai" | "actual" | "tie".
reason: 두세 문장."""


def render(draft):
    lines = [f"[보정 청구항] {draft['amended_claim']}"] if draft.get("amended_claim") else []
    for section in draft["sections"]:
        lines.append(f"## {section['heading']}")
        lines += [p["text"] for p in section["paragraphs"]]
    return "\n".join(lines)


def grade(args):
    client = anthropic.Anthropic(api_key=Settings().anthropic_api_key or None)
    actual = {c["case_id"]: c for c in repository.real_cases() if c.get("opinion_text")}
    rows = []
    for case in cases():
        path = RUNS / args.label / f"{case['application']}.json"
        if not path.exists():
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        prompt = JUDGE.format(
            category=case["category"],
            draft=render(record["draft"]) if record["ok"] else "",
            actual=actual[case["case_id"]]["opinion_text"][:12000],
        )
        # One retry: the judge occasionally returns broken JSON; then the case stays ungraded.
        for _ in range(2 if record["ok"] and "verdict" not in record else 0):
            try:
                response = client.messages.parse(
                    model="claude-sonnet-5-5",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=Verdict,
                )
            except (ValidationError, anthropic.APIError) as exc:
                print(case["application"], "judge failed:", str(exc)[:80], flush=True)
                continue
            record["verdict"] = response.parsed_output.model_dump()
            path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            break
        rows.append(record)
    report(rows, args.label)


def report(rows, label):
    graded = [r for r in rows if r.get("verdict")]
    axes = list(Scores.model_fields)

    def mean(who, axis):
        return round(statistics.mean(r["verdict"][who][axis] for r in graded), 1)

    summary = {
        "label": label,
        "cases": len(rows),
        "draft_passed_validation": f"{len(graded)}/{len(rows)}",
        "failures": [r["case_id"] + ": " + r["error"][:80] for r in rows if not r["ok"]],
        "ai": {a: mean("ai", a) for a in axes} if graded else {},
        "actual": {a: mean("actual", a) for a in axes} if graded else {},
        "core_argument": dict(
            (k, sum(r["verdict"]["core_argument"] == k for r in graded))
            for k in ("same", "partial", "none")
        ),
        "preferred": dict(
            (k, sum(r["verdict"]["preferred"] == k for r in graded))
            for k in ("ai", "actual", "tie")
        ),
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
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=run)
    p = sub.add_parser("grade")
    p.add_argument("label")
    p.set_defaults(func=grade)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
