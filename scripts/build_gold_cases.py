"""Draft LLM gold cases (data/eval/kr/<app>.json) from KIPRIS prosecution history.

uv run python scripts/build_gold_cases.py 1020140001347 1020140001427 ...

For each application (needs cached KIPRIS ClaimsChangeHistory detail):
1. inputs: Korean A publication from Google Patents (checked: its claim 1 must equal the originally
   filed claim 1 from KIPRIS, otherwise the case is skipped to avoid leaking later amendments)
   + the FIRST office action (2015 OA XML zip if present, else the KIPRIS OA PDF).
2. prosecution: every claim-1 amendment with its inserted phrases and what the next examiner action
   was (refused / granted), plus the refusal decision's review text.
3. rubric: drafted by Claude from (2) and marked "draft: needs human review".
The model under test only sees (1). Cases used as prompt examples must not be passed here.
"""

import argparse
import html
import json
import re
import sys
import urllib.parse
import zipfile
from pathlib import Path

import anthropic
import httpx
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402
from backend.precedents import repository  # noqa: E402
from backend.precedents.kipris import Kipris, KiprisError  # noqa: E402

EVAL = ROOT / "data/eval/kr"
INPUTS = ROOT / "data/eval/kr/inputs"
OA_2015 = ROOT / "data/downloads/kr_review_package/kipris_patent_oa_2015.zip"
PROMPT_EXAMPLES = {"1020140003628", "1020140002563"}  # used in prompt v2 → never gold
UA = {"User-Agent": "Mozilla/5.0 (PinPoint research)"}


class RubricItem(BaseModel):
    id: str
    weight: int
    question: str
    why: str


class Rubric(BaseModel):
    items: list[RubricItem]


def squash(text):
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", text or "")))


def claim_versions(api, app, claim_no="1"):
    """[(serial, date, doc name, full text, inserted phrases)] for one claim."""
    docs = {i["receiptSendSerialNumber"]: i for i in api.items("CL", "amendmentHistoryInfo", app)}
    out = []
    for it in api.items("CL", "amendmentHistoryDetailInfo", app):
        if it["petitionclauseNumber"] != claim_no:
            continue
        diff = html.unescape(it.get("transferPetitionclause") or "")
        ins = [
            re.sub(r"<br\s*/?>", " ", m).strip()
            for m in re.findall(r"<Ins>(.*?)</Ins>", diff, re.S)
        ]
        doc = docs.get(it["receiptSendSerialNumber"], {})
        out.append(
            {
                "serial": it["receiptSendSerialNumber"],
                "date": doc.get("receiptSendDate", ""),
                "document": doc.get("receiptSendDocumentName", ""),
                "change": it["changeTypeName"],
                "text": re.sub(
                    r"<br\s*/?>", "\n", html.unescape(it["petitionclause"] or "")
                ).strip(),
                "inserted": [i for i in ins if len(i) > 3],
            }
        )
    return sorted(out, key=lambda v: int(v["serial"]))


def google_publication(app):
    """A-publication number and PDF url via Google Patents."""
    q = urllib.parse.quote(f'q="KR{app}"')
    data = httpx.get(
        f"https://patents.google.com/xhr/query?url={q}&exp=", headers=UA, timeout=30
    ).json()
    hits = data["results"]["cluster"][0]["result"]
    granted = hits[0]["id"].split("/")[1]
    page = httpx.get(f"https://patents.google.com/patent/{granted}/ko", headers=UA, timeout=30).text
    pubs = [p for p in dict.fromkeys(re.findall(r"KR(20\d{2}\d{7})A", page)) if p != app[2:]]
    for pub in pubs:
        a_page = httpx.get(f"https://patents.google.com/patent/KR{pub}A/ko", headers=UA, timeout=30)
        if a_page.status_code != 200 or app[2:] not in a_page.text.replace("-", ""):
            continue
        pdf = re.findall(r"https://patentimages[^\"]+\.pdf", a_page.text)
        if pdf:
            return f"KR{pub}A", pdf[0]
    raise RuntimeError("A publication not found on Google Patents")


def first_claim_from_pdf(path):
    import pymupdf

    text = "".join(p.get_text() for p in pymupdf.open(path))
    m = re.search(r"청구항\s*1\s*\n(.*?)(?:\n\s*청구항\s*2\s*\n|\n\s*발명의\s*설명)", text, re.S)
    return m.group(1) if m else ""


def first_oa(api, app, folder):
    zipped = {}
    with zipfile.ZipFile(OA_2015) as z:
        for n in z.namelist():
            if n.endswith(".xml"):
                zipped.setdefault(Path(n).name.split("_")[0], []).append(n)
        notices = sorted(api.items("OP", "advancedSearchInfo", app), key=lambda i: i["sendDate"])
        first = notices[0]
        for n in zipped.get(app, []):
            if first["sendNumber"] in n:
                path = folder / Path(n).name
                path.write_bytes(z.read(n))
                return path, first
    path = Path(api.document_pdf(first["filePath"], f"OP_{app}_{first['sendNumber']}"))
    target = folder / f"{app}_{first['sendNumber']}.pdf"
    target.write_bytes(path.read_bytes())
    return target, first


def prosecution(app, versions, first_notice):
    cards = [c for c in repository.load(repository.KR_PATH) if c["application"] == app]
    rounds = []
    for v in versions[1:]:
        nxt = next(
            (
                c
                for c in sorted(cards, key=lambda c: c["oa_date"])
                if c["oa_date"].replace("-", "")
                < v["date"]
                <= c["next_action_date"].replace("-", "")
            ),
            None,
        )
        rounds.append(
            {
                "date": v["date"],
                "document": v["document"],
                "claim_1_added": v["inserted"],
                "next_action": nxt["next_action"] if nxt else "?",
                "next_action_date": nxt["next_action_date"] if nxt else "?",
                "examiner_review": (nxt or {}).get("examiner_reply_excerpt", "")[:900],
                "applicant_argument_summary": (nxt or {}).get("argument_excerpt", "")[:900],
            }
        )
    return {
        "first_notice": {
            "date": first_notice["sendDate"],
            "send_number": first_notice["sendNumber"],
        },
        "original_claim_1": versions[0]["text"],
        "rounds": rounds,
        "granted_claim_1": versions[-1]["text"],
    }


def draft_rubric(client, facts):
    prompt = (
        "You write a grading rubric for an AI that suggests how to respond to a Korean patent "
        "office action (the AI only sees the FIRST notice and original claims). Below is what "
        "really happened: each claim-1 amendment, what it inserted and whether the next examiner "
        "action refused or granted it.\n"
        "Write 4-5 items in Korean, weights summing to 8-9: one weight-3 item for the concrete "
        "technical direction that finally got granted (name the inserted feature), one weight-2 "
        "item on the specification support / prior-art distinction that matters most, one item "
        "penalizing the direction that was refused, and a weight-1 item 'no_guarantee' (no "
        "promise of allowance, states trade-offs). Questions must be answerable yes/no from the "
        "AI's suggestion text. ids in snake_case English.\n\nFACTS:\n"
        + json.dumps(facts, ensure_ascii=False)
    )
    response = client.messages.parse(
        model="claude-opus-5-5",
        max_tokens=6000,
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": prompt}],
        output_format=Rubric,
    )
    return [i.model_dump() for i in response.parsed_output.items]


def build(app, api, client):
    if app in PROMPT_EXAMPLES:
        return "skip: used as a prompt example"
    folder = INPUTS / app
    folder.mkdir(parents=True, exist_ok=True)
    versions = claim_versions(api, app)
    if len(versions) < 2:
        return "skip: no claim-1 amendments"
    pub, pdf_url = google_publication(app)
    pdf_path = folder / f"{pub}.pdf"
    if not pdf_path.exists():
        pdf_path.write_bytes(httpx.get(pdf_url, headers=UA, timeout=60).content)
    if squash(first_claim_from_pdf(pdf_path))[:120] != squash(versions[0]["text"])[:120]:
        return f"skip: {pub} claim 1 differs from the originally filed claim 1"
    oa_path, first = first_oa(api, app, folder)
    facts = prosecution(app, versions, first)
    gold = {
        "application": app,
        "purpose": "자동 생성 채점표 초안: 첫 통지서와 공개공보만 모델에 주고, 이후 보정·결과로 채점",
        "status": "draft: needs human review",
        "input_cutoff": first["sendDate"],
        "inputs": {
            "patent": str(pdf_path.relative_to(ROOT)).replace("\\", "/"),
            "office_action": str(oa_path.relative_to(ROOT)).replace("\\", "/"),
            "claim_number": 1,
        },
        "prosecution": facts,
        "rubric": draft_rubric(client, facts),
    }
    (EVAL / f"{app}.json").write_text(
        json.dumps(gold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return f"ok: {pub}, {len(facts['rounds'])} amendments, {len(gold['rubric'])} rubric items"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("applications", nargs="+")
    args = parser.parse_args()
    api = Kipris()
    client = anthropic.Anthropic(api_key=Settings().anthropic_api_key or None)
    for app in args.applications:
        try:
            print(app, build(app, api, client))
        except (KiprisError, httpx.HTTPError, RuntimeError, KeyError, IndexError) as exc:
            print(app, "fail:", exc)


if __name__ == "__main__":
    main()
