"""Build KR response cases from KIPRIS Plus (의견제출통지 → 의견서/보정서 → 다음 조치).

uv run python scripts/build_kr_precedents.py                 # the 5 official sample cases
uv run python scripts/build_kr_precedents.py --oa-2015 --limit 50   # + 2015 OA sample apps

Labels follow the redesign doc ("해소 여부 라벨링", 한국 라벨):
- 등록결정 → every rejection reason of that notice resolved
- 거절결정 → reasons in its "거절이유가 해소되지 않은 부분" table unresolved, the rest resolved
- 다시 의견제출통지 → the same statute again = unresolved, dropped = resolved
- response to a 거절결정 via 재심사 (보정서(재심사)) is flagged and excluded from stats,
  like US RCE; abandonment/withdrawal gets no label.
Response type: a 보정서 in the window → amendment, else argument_only when the 거절결정
names only an 의견서, otherwise unknown. API responses are cached in data/kipris_cache.
"""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents.kipris import Kipris, KiprisError  # noqa: E402
from backend.precedents.taxonomy import argument_types, categorize  # noqa: E402

OUT = ROOT / "data/precedents/kr_kipris_cases.jsonl"
SAMPLES = ROOT / "data/downloads/kr_review_package/official_samples"
OA_2015 = ROOT / "data/downloads/kr_review_package/kipris_patent_oa_2015.zip"
EXCERPT = 900

# Korean argument patterns found in 거절결정서 "의견서에 대한 검토" sections.
KR_ARGUMENTS = {
    "element_missing": r"차이(?:가|점이|점)\s*있|(?:개시|기재|교시|암시)(?:되어\s*있지\s*않|하고\s*있지\s*않|되지\s*않)|"
    r"(?:구성|특징)(?:이|을)\s*(?:포함하고\s*있지\s*않|찾을\s*수\s*없)",
    "no_motivation": r"결합(?:할|하는)?\s*(?:동기|이유|용이)|사후적|결합이\s*곤란",
    "unexpected_effect": r"현저한\s*효과|예측(?:할\s*수\s*없|하지\s*못한|이\s*곤란한)\s*효과|이질적",
    "limitation_added": r"보정(?:하여|함으로써|하였)|한정(?:하는|하여|하였)|추가(?:하는|하여|하였)",
    "dependent_merge": r"(?:종속항|청구항\s*제?\d+항)의\s*(?:구성|특징)(?:을|를)\s*(?:독립항|청구항\s*제?\d+항)에",
    "clarification": r"명확(?:하게|히)|불명확|기재불비",
}


def rows(table):
    """'순번†부분†법조항§1†청구항 제1항†특허법 제29조제2항' → [(part, statute)]."""
    out = []
    for row in (table or "").split("§")[1:]:
        cells = [c.strip() for c in row.split("†")]
        if len(cells) >= 3 and cells[2]:
            out.append((cells[1], cells[2]))
    return out


def ymd(value):
    value = re.sub(r"\D", "", value or "")
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if len(value) >= 8 else ""


def pdf_text(path):
    import pymupdf

    with pymupdf.open(path) as doc:
        return "".join(page.get_text() for page in doc)


HEADING = re.compile(r"(?m)^[ \t]*((?:[가-하]|\d+(?:-\d+)?))\.[ \t]*([^\n]{2,40}?)[ \t]*$")
REASON = re.compile(r"(?m)^[ \t]*(\d+)\.[ \t]*이[ \t]*출원")
STATUTE = re.compile(r"특허법\s*제\s*\d+\s*조(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?")


def decision_sections(text):
    """Classify 거절결정서 sections across its varying layouts.

    Seen so far: '라. 의견서에 대한 검토' (one combined section), 'N-1. 의견 내용 /
    N-2. 의견 내용 검토' (per reason), '2. 의견서를 통한 출원인의 주장 / 3. 출원인의 주장에
    대한 검토', '보정서 및 의견서 내용 / … 에 관한 판단'. Returns [(role, category or None,
    body)], role ∈ argument/review/amendment.
    """
    text = re.sub(r"(?m)^\s*-\s*\d+\s*-\s*$", "", text)
    # Repeated page header: 출원번호 … 발명의 명칭 … 수신 :
    text = re.sub(r"출\s*원\s*번\s*호\s*10-\d{4}-\d{7}.*?수신\s*:", " ", text, flags=re.S)
    text = text.split("<<", 1)[0]
    reasons = {}
    for m in REASON.finditer(text):
        statute = STATUTE.search(text[m.end() : m.end() + 400])
        if statute:
            reasons[m.group(1)] = categorize(statute.group(0), "kr")
    heads = list(HEADING.finditer(text))
    out = []
    for i, m in enumerate(heads):
        title = re.sub(r"\s+", "", m.group(2))
        if re.search(r"검토|판단|해소되었는지|해소여부|심사관의의견|거절이유관련", title):
            roles = ["review"]
        else:
            roles = []
            if re.search(r"의견내용|주장|의견서(?:를통한|내용|의)", title):
                roles.append("argument")
            if re.search(r"보정(?:서의)?(?:내용|사항|요지)|보정서및|보정서내용", title):
                roles.append("amendment")
            if not roles:
                continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        reason = REASON.search(text, m.end(), end)  # next numbered reason ends this section
        end = reason.start() if reason else end
        body = re.sub(r"\s+", " ", text[m.end() : end]).strip()
        number = m.group(1).split("-")[0]
        category = reasons.get(number) if "-" in m.group(1) else None
        # '라. 의견서에 대한 검토' carries both the applicant's arguments and the reply.
        if "의견서에대한검토" in title:
            out.append(("argument", category, body))
        out += [(role, category, body) for role in roles]
    return out


INLINE_ARGUMENT = re.compile(
    r"[^\n.]*의견서[^.]{0,40}?(?:통하여|에서|를\s*통해)[\s\S]{0,1200}?주장(?:하였|합니다|하고)[^.]*\.",
)


def inline_sections(text):
    """Free-text layout: '…의견서를 통하여 … 주장하였습니다.' inside [거절결정의 이유]."""
    body = text.split("[거절결정의 이유]", 1)[-1].split("<<", 1)[0]
    body = re.sub(r"출\s*원\s*번\s*호\s*10-\d{4}-\d{7}.*?수신\s*:", " ", body, flags=re.S)
    m = INLINE_ARGUMENT.search(body)
    if not m:
        return []
    squash = lambda value: re.sub(r"\s+", " ", re.sub(r"-\s*\d+\s*-", " ", value)).strip()  # noqa: E731
    return [
        ("argument", None, squash(m.group(0))),
        ("review", None, squash(body[m.end() : m.end() + 1500])),
    ]


def pick(sections, role, category):
    return " ".join(b for r, c, b in sections if r == role and c in {None, category})


def kr_argument_types(text):
    found = [k for k, p in KR_ARGUMENTS.items() if re.search(p, text or "")]
    return found or argument_types(text)


def events(api, app):
    oas = []
    ops = {i["sendNumber"]: i for i in api.items("OP", "advancedSearchInfo", app)}
    reasons = {i["sendNumber"]: i for i in api.items("OP", "examineResultInfo", app)} if ops else {}
    for number, item in ops.items():
        oas.append(
            {
                "kind": "OA",
                "send_number": number,
                "date": ymd(item["sendDate"]),
                "rows": rows(reasons.get(number, {}).get("refusalLawTabularstatement")),
                "examined_claims": reasons.get(number, {}).get("examinationContent", ""),
            }
        )
    decisions = []
    refusals = {i["sendNumber"]: i for i in api.items("RE", "advancedSearchInfo", app)}
    if refusals:
        results = {i["sendNumber"]: i for i in api.items("RE", "examineResultInfo", app)}
        bases = {i["sendNumber"]: i for i in api.items("RE", "rejectDecisionInfo", app)}
        for number, item in refusals.items():
            sections = []
            if item.get("filePath"):
                try:
                    text = pdf_text(api.document_pdf(item["filePath"], f"{app}_{number}"))
                    sections = decision_sections(text)
                    if not any(role == "argument" for role, _, _ in sections):
                        sections += inline_sections(text)
                except (KiprisError, OSError, ValueError):
                    pass
            decisions.append(
                {
                    "kind": "RE",
                    "send_number": number,
                    "date": ymd(item["sendDate"]),
                    "unresolved": rows(results.get(number, {}).get("refusalLawTabularstatement")),
                    "basis": bases.get(number, {}).get("lawContent", ""),
                    "sections": sections,
                    # '지정기간 … 의견서 또는 보정서 제출이 없었으며' = no response at all
                    "no_response": "제출이 없" in bases.get(number, {}).get("lawContent", ""),
                }
            )
    grants = api.items("RG", "bibliographicInfo", app)
    contents = api.items("RG", "contentInfo", app) if grants else []
    for item in grants:
        text = " ".join(c["content"] for c in contents if c["sendNumber"] == item["sendNumber"])
        decisions.append(
            {
                "kind": "RG",
                "send_number": item["sendNumber"],
                "date": ymd(item["sendDate"]),
                "reexamination": "재심사" in text,
            }
        )
    amendments = [
        {"date": ymd(i["receiptSendDate"]), "name": i["receiptSendDocumentName"]}
        for i in api.items("CL", "amendmentHistoryInfo", app)
        if "보정" in i["receiptSendDocumentName"]
    ]
    return sorted(oas, key=lambda e: e["date"]), decisions, amendments


def build_app(api, app):
    oas, decisions, amendments = events(api, app)
    timeline = sorted(oas + decisions, key=lambda e: (e["date"], e["kind"] != "OA"))
    records = []
    for oa in oas:
        nxt = next((e for e in timeline if e["date"] > oa["date"]), None)
        if nxt is None:
            continue
        window = [a for a in amendments if oa["date"] < a["date"] <= nxt["date"]]
        if window:
            response = "amendment"
        elif nxt["kind"] == "RE" and "의견" in nxt["basis"] and "보정서" not in nxt["basis"]:
            response = "argument_only"
        else:
            response = "unknown"
        if nxt["kind"] == "RE":
            later = [a for a in amendments if a["date"] > nxt["date"] and "재심사" in a["name"]]
            after = next((e for e in timeline if e["date"] > nxt["date"]), None)
        for index, (part, statute) in enumerate(oa["rows"], 1):
            category = categorize(statute, "kr")
            if nxt["kind"] == "RG":
                outcome = "resolved"
            elif nxt["kind"] == "RE":
                still = {categorize(s, "kr") for _, s in nxt["unresolved"]}
                outcome = "unresolved" if category in still else "resolved"
            else:
                outcome = (
                    "unresolved"
                    if category in {categorize(s, "kr") for _, s in nxt["rows"]}
                    else "resolved"
                )
            reason = None
            if nxt["kind"] == "RE" and nxt["no_response"] and not window:
                # Not a failed response: nothing was filed (like abandonment, not a label).
                outcome, reason, response = "excluded", "no_response", "none"
            elif nxt["kind"] == "RE" and not nxt["unresolved"]:
                # Refusal without the '해소되지 않은 부분' table: per-reason outcome unknown.
                outcome, reason = "excluded", "table_missing"
            sections = nxt.get("sections", [])
            argument = pick(sections, "argument", category)
            review = pick(sections, "review", category)
            amendment = pick(sections, "amendment", category)
            records.append(
                {
                    "case_id": f"KIPRIS-{app}-{oa['send_number']}-{index}-{category}",
                    "source": "KIPRIS",
                    "jurisdiction": "KR",
                    "application": app,
                    "round": oas.index(oa) + 1,
                    "category": category,
                    "statute": statute,
                    "claims": part,
                    "oa_type": "의견제출통지서",
                    "oa_date": oa["date"],
                    "response_type": response,
                    "amendments": [a["name"] for a in window],
                    "argument_types": kr_argument_types(argument + " " + amendment),
                    "section_found": bool(argument),
                    "next_action": {"RG": "등록결정", "RE": "거절결정", "OA": "의견제출통지서"}[
                        nxt["kind"]
                    ],
                    "next_action_date": nxt["date"],
                    "outcome": outcome,
                    "exclusion_reason": reason,
                    "examiner_reply": "allowed" if nxt["kind"] == "RG" else "unknown",
                    "amendment_summary": amendment[: EXCERPT // 2],
                    "argument_excerpt": argument[:EXCERPT],
                    "examiner_reply_excerpt": review[:EXCERPT],
                    "reexamination_followed": nxt["kind"] == "RE"
                    and bool(later)
                    and after is not None,
                }
            )
    # 재심사 round: response to a 거절결정 decided by a later decision. Flagged, not counted.
    for refusal in (d for d in decisions if d["kind"] == "RE"):
        after = next((e for e in timeline if e["date"] > refusal["date"]), None)
        if after is None:
            continue
        for index, (part, statute) in enumerate(refusal["unresolved"], 1):
            category = categorize(statute, "kr")
            records.append(
                {
                    "case_id": f"KIPRIS-{app}-{refusal['send_number']}-{index}-{category}",
                    "source": "KIPRIS",
                    "jurisdiction": "KR",
                    "application": app,
                    "round": 0,
                    "category": category,
                    "statute": statute,
                    "claims": part,
                    "oa_type": "거절결정서",
                    "oa_date": refusal["date"],
                    "response_type": "amendment",
                    "amendments": [
                        a["name"]
                        for a in amendments
                        if refusal["date"] < a["date"] <= after["date"]
                    ],
                    "argument_types": [],
                    "section_found": False,
                    "next_action": {"RG": "등록결정", "RE": "거절결정", "OA": "의견제출통지서"}[
                        after["kind"]
                    ],
                    "next_action_date": after["date"],
                    "outcome": "excluded",
                    "exclusion_reason": "reexamination",
                    "examiner_reply": "allowed" if after["kind"] == "RG" else "unknown",
                    "amendment_summary": "",
                    "argument_excerpt": "",
                    "examiner_reply_excerpt": "",
                    "reexamination_followed": False,
                }
            )
    return records


def applications(args):
    apps = sorted({p.name.split("_")[0] for p in SAMPLES.iterdir() if p.is_dir()})
    if args.oa_2015:
        with zipfile.ZipFile(OA_2015) as z:
            extra = sorted({Path(n).name.split("_")[0] for n in z.namelist() if n.endswith(".xml")})
        apps += [a for a in extra if a not in apps][: args.limit]
    return apps


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--oa-2015", action="store_true", help="add apps from the 2015 OA zip")
    parser.add_argument("--limit", type=int, default=50, help="max extra 2015 applications")
    args = parser.parse_args()
    api = Kipris()
    records, failed = [], {}
    for app in applications(args):
        try:
            records += build_app(api, app)
        except KiprisError as exc:
            failed[app] = str(exc)
            if "한도" in str(exc):
                break
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"{len(records)} KR records → {OUT.relative_to(ROOT)}; failed {failed}")
    print("usage:", (api.cache / "usage.json").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    main()
