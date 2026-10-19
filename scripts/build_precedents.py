"""Build the US response-precedent table from PatRe (OA → applicant response → next action).

Source: https://huggingface.co/datasets/PatRe-Bench/PatRe (MIT, 480 applications).
Download once:  uv run python scripts/build_precedents.py --download
Rebuild:        uv run python scripts/build_precedents.py

Labels follow the redesign doc (2026-10-19, "해소 여부 라벨링"):
- next action Notice of Allowance / Ex parte Quayle → every rejection type resolved
- next rejection → a type still present = unresolved, a type that disappeared = resolved
- response to a Final Rejection followed by a Non-Final (RCE) → excluded from outcome stats
- argument-only vs amendment responses are recorded separately (resolution ≠ argument won)
Category-level only: PatRe does not give per-claim dispositions, so claim-level labels are a
later step (김경훈 홀드아웃 라벨링).
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.precedents.taxonomy import argument_types, categorize, categorize_patre  # noqa: E402

URL = "https://huggingface.co/datasets/PatRe-Bench/PatRe/resolve/main/PatRe-test.parquet"
RAW = ROOT / "data/datasets/patre/PatRe-test.parquet"
OUT = ROOT / "data/precedents/us_patre_cases.jsonl"
MANIFEST = ROOT / "data/precedents/manifest.json"
EXCERPT = 900

AMENDED = re.compile(
    r"Amendments?\s+to\s+the\s+Claims|Currently\s+Amended|"
    r"\b(?:is|are|have\s+been|has\s+been|were|was)\s+(?:\w+\s+)?amended\b|"
    r"\bamend(?:s|ed|ing)?\s+(?:independent\s+)?claims?\s+\d|claims?\s+[\d,\sand-]+\s+(?:is|are)\s+amended",
    re.I,
)
NOT_AMENDED = re.compile(
    r"no\s+claims?\s+(?:is|are|have\s+been|has\s+been)\s+amended|without\s+amendment|"
    r"claims?\s+(?:is|are)\s+not\s+(?:being\s+)?amended",
    re.I,
)
AMENDED_CLAIMS = re.compile(
    r"claims?\s+([\d][\d,\s\-–and]*?)\s+(?:is|are|have\s+been|has\s+been)\s+(?:\w+\s+)?amended|"
    r"amend(?:s|ed|ing)\s+(?:independent\s+)?claims?\s+(\d[\d,\s\-–]*(?:and\s+\d+)?)",
    re.I,
)
HEADING = re.compile(
    r"^\s*(?:[IVX]+\.|[A-Z]\.|\d+\.)?\s*(?:Claim\s+)?Rejections?\b.{0,120}$|"
    r"^\s*(?:[IVX]+\.|[A-Z]\.|\d+\.)?\s*.{0,60}(?:35\s*U\.?\s*S\.?\s*C\.?|§)\s*§?\s*\d{3}.{0,80}$|"
    r"^\s*(?:[IVX]+\.|[A-Z]\.|\d+\.)?\s*(?:Double\s+Patenting|Claim\s+Objections?|Drawings|"
    r"Specification|Conclusion|Allowable\s+Subject\s+Matter|Summary\s+of\s+Remarks|"
    r"Status\s+of\s+(?:the\s+)?Claims|Response\s+to\s+Arguments|Interview\s+Summary)\b.{0,80}$",
    re.I | re.M,
)


def clean(text):
    text = text or ""
    text = re.sub(r"(U\.?\s*S\.?\s*C\.?)\s*�+", r"\1 §", text)
    text = re.sub(r"�+\s*(?=\d{3})", "§ ", text)
    return re.sub(r"�+", "'", text)


def sections(text):
    """Split a REMARKS / Office Action into (heading, body) pairs on short heading lines."""
    marks = [m for m in HEADING.finditer(text) if len(m.group(0).strip()) <= 160]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(0).strip(), text[m.end() : end].strip()))
    return out


def category_sections(text):
    found = {}
    for heading, body in sections(text):
        if not re.search(r"\d{3}|Double\s+Patenting", heading, re.I):
            continue
        category = categorize(heading, "us")
        if category != "other" and body:
            found.setdefault(category, []).append(body)
    return {k: "\n".join(v) for k, v in found.items()}


def response_to_arguments(next_oa):
    m = re.search(r"Response\s+to\s+Arguments?", next_oa, re.I)
    if not m:
        return ""
    tail = next_oa[m.end() :]
    stop = re.search(r"\n\s*(?:Claim\s+Rejections?\s*-|Conclusion|Allowable\s+Subject)", tail, re.I)
    return tail[: stop.start() if stop else 4000]


def examiner_reply(rta, category):
    """persuasive / not_persuasive / moot for this category's part of Response to Arguments."""
    if not rta:
        return "unknown", ""
    parts = category_sections(rta)
    body = parts.get(category)
    if body is None:
        statute = {
            "novelty": "102",
            "inventive_step": "103",
            "description": "112",
            "eligibility": "101",
        }.get(category)
        hits = [s for s in re.split(r"(?<=\.)\s+", rta) if statute and statute in s]
        body = " ".join(hits[:6])
    if not body:
        return "unknown", ""
    window = body[:1500]
    if re.search(r"\bmoot\b", window, re.I):
        verdict = "moot"
    elif re.search(r"not\s+(?:been\s+found\s+)?persuasive|unpersuasive", window, re.I):
        verdict = "not_persuasive"
    elif re.search(r"persuasive|withdrawn", window, re.I):
        verdict = "persuasive"
    else:
        verdict = "unknown"
    return verdict, re.sub(r"\s+", " ", body)[: EXCERPT // 2]


def amended_claims(text):
    numbers = []
    for m in AMENDED_CLAIMS.finditer(text):
        numbers.append(re.sub(r"\s+", " ", m.group(1) or m.group(2)).strip(" ,"))
    return "; ".join(dict.fromkeys(numbers))[:120]


def load_rows():
    import pandas as pd

    df = pd.read_parquet(RAW)
    rows = {}
    for r in df.to_dict("records"):
        rows.setdefault(r["id"], []).append(r)
    return rows


def build():
    apps = load_rows()
    records, skipped = [], Counter()
    for app, rows in sorted(apps.items()):
        oas = {r["meta.oa_number"]: r for r in rows if r["meta.round_type"] == "oa"}
        for r in sorted(
            (r for r in rows if r["meta.round_type"] == "rebuttal"),
            key=lambda r: r["meta.oa_number"],
        ):
            k = r["meta.oa_number"]
            current, nxt = oas.get(k), oas.get(k + 1)
            if current is None or nxt is None:
                skipped["no_next_action"] += 1
                continue
            types = [t for t in json.loads(r["meta.rejection_types"] or "[]") if isinstance(t, str)]
            categories = list(dict.fromkeys(categorize_patre(t) for t in types))
            categories = [c for c in categories if c != "other"]
            if not categories:
                skipped["no_rejection"] += 1
                continue
            next_types = {
                categorize_patre(t)
                for t in json.loads(nxt["meta.rejection_types"] or "[]")
                if isinstance(t, str)
            }
            response = clean(r["input.rebuttal"])
            next_oa = clean(r["input.next_office_action"])
            next_action = nxt["meta.oa_type"]
            allowed = next_action in {"Notice of Allowance", "Ex Parte Quayle Action"}
            rce = (
                current["meta.oa_type"] == "Final Rejection"
                and next_action == "Non-Final Rejection"
            )
            amendment = bool(AMENDED.search(response)) and not NOT_AMENDED.search(response)
            interview = bool(
                re.search(
                    r"interview\s+(?:was\s+)?(?:conducted|held)|Interview\s+Summary|"
                    r"(?:telephone|telephonic)\s+interview\s+(?:on|with)",
                    response + next_oa,
                    re.I,
                )
            )
            examiner_amendment = bool(re.search(r"EXAMINER.S\s+AMENDMENT", next_oa))
            parts = category_sections(response)
            rta = response_to_arguments(next_oa)
            app_no = app.split("_")[0]
            for category in categories:
                body = parts.get(category)
                section_found = body is not None
                if body is None:
                    m = re.search(r"REMARKS|Remarks", response)
                    body = response[m.end() if m else 0 :]
                if rce:
                    outcome, reason = "excluded", "rce"
                elif allowed:
                    outcome, reason = "resolved", None
                else:
                    outcome, reason = (
                        ("unresolved", None) if category in next_types else ("resolved", None)
                    )
                verdict, reply = examiner_reply(rta, category)
                if allowed and verdict == "unknown":
                    verdict = "allowed"
                records.append(
                    {
                        "case_id": f"PATRE-{app_no}-R{k}-{category}",
                        "source": "PatRe",
                        "application": app_no,
                        "round": k,
                        "ipc_section": r["meta.ipc"],
                        "claim_count": int(r["meta.claim_count"]),
                        "category": category,
                        "oa_type": current["meta.oa_type"],
                        "oa_date": current["meta.oa_date"],
                        "other_categories": [c for c in categories if c != category],
                        "response_type": "amendment" if amendment else "argument_only",
                        "claims_amended": amended_claims(response) if amendment else "",
                        "argument_types": argument_types(body),
                        "section_found": section_found,
                        "interview": interview,
                        "examiner_amendment": examiner_amendment,
                        "next_action": next_action,
                        "next_action_date": nxt["meta.oa_date"],
                        "outcome": outcome,
                        "exclusion_reason": reason,
                        "examiner_reply": verdict,
                        "argument_excerpt": re.sub(r"\s+", " ", body)[:EXCERPT],
                        "examiner_reply_excerpt": reply,
                        "source_sha256": hashlib.sha256(
                            (r["input.rebuttal"] or "").encode("utf-8")
                        ).hexdigest()[:16],
                    }
                )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    stats = Counter((r["category"], r["response_type"], r["outcome"]) for r in records)
    MANIFEST.write_text(
        json.dumps(
            {
                "source": URL,
                "license": "MIT (PatRe-Bench/PatRe)",
                "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
                "records": len(records),
                "applications": len({r["application"] for r in records}),
                "skipped_responses": dict(skipped),
                "by_category_response_outcome": {"|".join(k): v for k, v in sorted(stats.items())},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(records)} records → {OUT.relative_to(ROOT)}; skipped {dict(skipped)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--download", action="store_true", help="fetch PatRe parquet first")
    args = parser.parse_args()
    if args.download or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(URL, RAW)
    build()
