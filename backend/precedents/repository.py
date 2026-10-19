"""Read-only access to the response-precedent tables.

US: scripts/build_precedents.py (PatRe). KR: scripts/build_kr_precedents.py (KIPRIS Plus).

The JSONL file is the source of truth so the demo works without PostgreSQL;
scripts/load_precedents_pg.py copies it into the `response_cases` table for the web API.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from backend.precedents.taxonomy import CATEGORIES, argument_label, label

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "data/precedents/us_patre_cases.jsonl"
KR_PATH = ROOT / "data/precedents/kr_kipris_cases.jsonl"
SOURCE_NOTE = (
    "미국 USPTO 실제 대응 사례(PatRe 데이터셋)의 통계입니다. 한국 심사 결과를 예측하지 않으며 "
    "참고용입니다. 변리사 검토가 필요합니다."
)
KR_NOTE = (
    "한국 특허청 실제 사건(KIPRIS 의견제출통지서·거절결정서·등록결정서)의 집계입니다. 표본이 작아 "
    "경향으로 해석하지 말고 사례로만 참고하세요. 변리사 검토가 필요합니다."
)
MIN_ARGUMENT_CASES = 5
STOPWORDS = set(
    "the a an of to and or in on for with by is are be as at that this from claim claims "
    "wherein said which first second one more least".split()
)


@lru_cache
def load(path=DEFAULT_PATH):
    """All cases of one JSONL table (cached per process; restart the API after rebuilding)."""
    path = Path(path)
    if not path.exists():
        return ()
    with path.open(encoding="utf-8") as f:
        return tuple(json.loads(line) for line in f if line.strip())


def _rate(part, whole):
    return round(part / whole, 3) if whole else None


def stats(category, path=DEFAULT_PATH, exclude_applications=frozenset()):
    """Outcome counts for one common rejection category. RCE/abandoned responses excluded."""
    cases = [
        c
        for c in load(path)
        if c["category"] == category and c["application"] not in exclude_applications
    ]
    labeled = [c for c in cases if c["outcome"] != "excluded"]
    resolved = [c for c in labeled if c["outcome"] == "resolved"]
    by_response = {}
    for kind in ("amendment", "argument_only"):
        group = [c for c in labeled if c["response_type"] == kind]
        ok = sum(c["outcome"] == "resolved" for c in group)
        by_response[kind] = {"cases": len(group), "resolved": ok, "rate": _rate(ok, len(group))}
    counts = Counter(a for c in labeled for a in c["argument_types"])
    wins = Counter(a for c in resolved for a in c["argument_types"])
    by_argument = [
        {
            "type": key,
            "label": argument_label(key),
            "cases": n,
            "resolved": wins[key],
            "rate": _rate(wins[key], n),
        }
        for key, n in counts.most_common()
        if n >= MIN_ARGUMENT_CASES
    ]
    return {
        "category": category,
        "label": label(category),
        "reuse": CATEGORIES.get(category, CATEGORIES["other"])["reuse"],
        "kr_statute": CATEGORIES.get(category, CATEGORIES["other"])["kr"],
        "us_statute": CATEGORIES.get(category, CATEGORIES["other"])["us"],
        "total": len(cases),
        "labeled": len(labeled),
        "excluded": len(cases) - len(labeled),
        "resolved": len(resolved),
        "unresolved": len(labeled) - len(resolved),
        "resolved_rate": _rate(len(resolved), len(labeled)),
        "by_response": by_response,
        "by_argument": by_argument,
        "source": "KIPRIS (KIPO)" if Path(path) == KR_PATH else "PatRe (USPTO, MIT)",
        "note": KR_NOTE if Path(path) == KR_PATH else SOURCE_NOTE,
    }


def _tokens(text):
    return [
        t for t in re.findall(r"[a-z][a-z0-9-]{2,}", (text or "").lower()) if t not in STOPWORDS
    ]


def find(category, query="", limit=3, path=DEFAULT_PATH, exclude_applications=frozenset()):
    """Representative cases: lexical match for English queries, otherwise clear-label cases.

    Picks a mix of outcomes (amendment-resolved, argument-only-resolved, unresolved) so the
    checklist shows what worked and what did not, not only successes.
    """
    cases = [
        c
        for c in load(path)
        if c["category"] == category
        and c["outcome"] != "excluded"
        and c["section_found"]
        and c["application"] not in exclude_applications
    ]
    if not cases:
        return []
    terms = Counter(_tokens(query))
    df = Counter(t for c in cases for t in set(_tokens(c["argument_excerpt"])))
    n = len(cases)

    def score(case):
        words = Counter(_tokens(case["argument_excerpt"]))
        lexical = sum(min(words[t], 3) * math.log(1 + n / (1 + df[t])) for t in terms if t in words)
        clarity = 0.5 * bool(case["argument_types"]) + 0.3 * (case["examiner_reply"] != "unknown")
        return (lexical + clarity, case["case_id"])

    ranked = sorted(cases, key=score, reverse=True)
    buckets = [
        lambda c: c["outcome"] == "resolved" and c["response_type"] == "amendment",
        lambda c: c["outcome"] == "resolved" and c["response_type"] == "argument_only",
        lambda c: c["outcome"] == "unresolved",
    ]
    picked = []
    for test in buckets:
        hit = next((c for c in ranked if test(c) and c not in picked), None)
        if hit:
            picked.append(hit)
    picked += [c for c in ranked if c not in picked]
    return [summary(c) for c in picked[:limit]]


def summary(case):
    """Compact card used by the checklist, API and AI prompt."""
    return {
        "case_id": case["case_id"],
        "application": case["application"],
        "category": case["category"],
        "oa_type": case["oa_type"],
        "oa_date": case["oa_date"],
        "response_type": case["response_type"],
        "argument_types": [argument_label(a) for a in case["argument_types"]],
        "next_action": case["next_action"],
        "outcome": case["outcome"],
        "examiner_reply": case["examiner_reply"],
        "argument_excerpt": case["argument_excerpt"][:600],
        "examiner_reply_excerpt": case["examiner_reply_excerpt"][:300],
    } | {
        key: case[key]
        for key in ("jurisdiction", "statute", "claims", "amendment_summary")
        if case.get(key)
    }


def get(case_id):
    """One case by case_id from the US or KR table."""
    return next(
        (c for path in (DEFAULT_PATH, KR_PATH) for c in load(path) if c["case_id"] == case_id),
        None,
    )
