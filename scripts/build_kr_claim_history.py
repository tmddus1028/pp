"""Attach claim text before/after each response to the KIPRIS precedent cases.

For every application in data/precedents/kr_kipris_cases.jsonl this reads the KIPRIS
ClaimsChangeHistoryService (보정이력순서 + 보정이력상세내역), rebuilds the claim set after each
amendment, and writes data/precedents/kr_claim_history.jsonl keyed by case_id:

  claims_before   target claims in force on the notice date
  claims_after    the same claims after the amendments filed before the next action
  added_limitation added/changed wording (claim diff), empty when nothing changed
  response_method dependent_merge | spec_limitation | none (heuristic, see below)

Usage: uv run python scripts/build_kr_claim_history.py [--limit N]
Calls are cached in data/kipris_cache (2 per application, monthly guard in kipris.py).
The 의견서 text itself is not in KIPRIS Plus; this file only says what the claims became.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.improvements.revision import claim_diff  # noqa: E402
from backend.precedents.kipris import Kipris, KiprisError, clean  # noqa: E402
from backend.precedents.repository import KR_PATH, load  # noqa: E402

OUT = ROOT / "data/precedents/kr_claim_history.jsonl"


def target_claims(text):
    """'청구항 제1항, 제3항 내지 제8항' → [1, 3, 4, 5, 6, 7, 8]; '청구항 전부' → [] (all)."""
    numbers = []
    for start, end in re.findall(
        r"제\s*(\d+)\s*항(?:\s*(?:내지|~|-)\s*제\s*(\d+)\s*항)?", text or ""
    ):
        numbers += range(int(start), int(end or start) + 1)
    return sorted(set(numbers))


def versions(api, app):
    """[(date, document name, {claim number: text})] — the full claim set after each filing."""
    order = {
        e.findtext("receiptSendSerialNumber"): (
            e.findtext("receiptSendDate"),
            e.findtext("receiptSendDocumentName"),
        )
        for e in ET.fromstring(api.raw("CL", "amendmentHistoryInfo", app)).iter(
            "amendmentHistoryInfo"
        )
    }
    changes = {}
    for e in ET.fromstring(api.raw("CL", "amendmentHistoryDetailInfo", app)).iter(
        "amendmentHistoryDetailInfo"
    ):
        changes.setdefault(e.findtext("receiptSendSerialNumber"), []).append(
            (
                int(e.findtext("petitionclauseNumber") or 0),
                e.findtext("changeTypeCode"),
                clean(e.findtext("petitionclause")).replace("\n", " ").strip(),
            )
        )
    state, out = {}, []
    for serial in sorted(order, key=int):
        for number, kind, text in changes.get(serial, []):
            if kind == "D":
                state.pop(number, None)
            elif number:
                state[number] = text
        date, name = order[serial]
        out.append((f"{date[:4]}-{date[4:6]}-{date[6:]}", name, dict(state)))
    return out


def method(before, after, targets):
    """dependent_merge if most added words already sat in another claim; else spec_limitation.

    ponytail: word-overlap heuristic; a reviewer label replaces it once 의견서/보정서 are read.
    """
    added = " ".join(
        c.revised
        for n in targets
        if n in before and n in after
        for c in claim_diff(before[n], after[n])
        if c.change_type in {"added", "changed"}
    )
    words = set(re.findall(r"[가-힣]{2,}", added))
    if not words:
        return "none", ""
    others = " ".join(text for n, text in before.items() if n not in targets)
    shared = sum(w in others for w in words) / len(words)
    return ("dependent_merge" if shared >= 0.6 else "spec_limitation"), added.strip()


def history(case, filings):
    oa, nxt = case["oa_date"], case["next_action_date"] or "9999-12-31"
    if not oa or not filings:
        return None
    before = next((s for d, _, s in reversed(filings) if d <= oa), None)
    window = [(d, name, s) for d, name, s in filings if oa < d <= nxt]
    if before is None:
        return None
    after = window[-1][2] if window else before
    targets = target_claims(case["claims"]) or sorted(before)
    targets = [n for n in targets if n in before] or sorted(before)[:1]
    kind, added = method(before, after, targets)
    join = lambda state: "\n".join(f"[청구항 {n}] {state[n]}" for n in targets if n in state)  # noqa: E731
    return {
        "case_id": case["case_id"],
        "application": case["application"],
        "claims_before": join(before),
        "claims_after": join(after),
        "added_limitation": added[:2000],
        "response_method": kind,
        "amendment_documents": [f"{d} {name}" for d, name, _ in window],
        "history_source": "KIPRIS 청구항 변동 이력",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="applications to fetch (0 = all)")
    args = parser.parse_args()
    cases = [c for c in load(KR_PATH) if c["category"] != "other"]
    apps = list(dict.fromkeys(c["application"] for c in cases))
    if args.limit:
        apps = apps[: args.limit]
    api, rows, failed = Kipris(), [], []
    for i, app in enumerate(apps, 1):
        try:
            filings = versions(api, app)
        except (KiprisError, ET.ParseError) as exc:
            failed.append(f"{app}: {exc}")
            continue
        rows += [r for c in cases if c["application"] == app if (r := history(c, filings))]
        if i % 20 == 0:
            print(f"{i}/{len(apps)} applications")
    with OUT.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{len(rows)} cases with claim history from {len(apps) - len(failed)} applications")
    for line in failed:
        print("failed", line)


if __name__ == "__main__":
    main()
