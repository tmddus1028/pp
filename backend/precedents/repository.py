"""Read-only access to the Korean response-precedent table (KIPRIS) plus labelled demo cases.

KR: scripts/build_kr_precedents.py (KIPRIS Plus). The JSONL file is the source of truth so the
demo works without PostgreSQL; scripts/load_precedents_pg.py copies it into `response_cases`.

KIPRIS records carry no claim text; scripts/build_kr_claim_history.py adds it per case from the
claim-change history (kr_claim_history.jsonl: claims before/after the response, added wording).
`kr_demo_cases.jsonl` holds clearly marked DEMO cases, used for similar-case retrieval only in a
category where no real case has claim text yet. Demo cases never enter the statistics.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

from backend.precedents.taxonomy import argument_label, label

ROOT = Path(__file__).resolve().parents[2]
KR_PATH = ROOT / "data/precedents/kr_kipris_cases.jsonl"
DEMO_PATH = ROOT / "data/precedents/kr_demo_cases.jsonl"
HISTORY_PATH = ROOT / "data/precedents/kr_claim_history.jsonl"
DEFAULT_PATH = KR_PATH
HISTORY_FIELDS = (
    "claims_before",
    "claims_after",
    "added_limitation",
    "response_method",
    "amendment_documents",
    "history_source",
)
NOTE = (
    "한국 특허청 실제 사건(KIPRIS 의견제출통지서·거절결정서·등록결정서)의 집계입니다. 표본이 작아 "
    "경향으로 해석하지 말고 사례로만 참고하세요. 변리사 검토가 필요합니다."
)
MIN_ARGUMENT_CASES = 5
# Calibration knob: tf-idf cosine below this is unrelated technology in practice (e.g. a coupon
# claim vs. a drug composition scored ~0.08). Re-tune once cases are filtered by IPC.
MIN_SIMILARITY = 0.15
STOPWORDS = {
    "상기",
    "있어서",
    "포함하는",
    "특징으로",
    "하는",
    "청구항",
    "인용발명",
    "발명",
    "시스템",
    "방법",
    "장치",
    "있는",
    "것을",
    "구성",
    "the",
    "and",
    "for",
    "with",
    "claim",
}


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
    """Outcome counts for one common rejection category (real cases only)."""
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
        "total": len(cases),
        "labeled": len(labeled),
        "excluded": len(cases) - len(labeled),
        "resolved": len(resolved),
        "unresolved": len(labeled) - len(resolved),
        "resolved_rate": _rate(len(resolved), len(labeled)),
        "by_response": by_response,
        "by_argument": by_argument,
        "source": "KIPRIS (KIPO)",
        "note": NOTE,
    }


def _tokens(text):
    """Korean (2+ syllables) and Latin (3+ letters) words; particles stay attached (rough)."""
    words = re.findall(r"[가-힣]{2,}|[a-z][a-z0-9-]{2,}", (text or "").lower())
    return [w for w in words if w not in STOPWORDS]


def _ranker(cases, field):
    """idf-weighted word overlap between a query and one text field of each case."""
    df = Counter(t for c in cases for t in set(_tokens(field(c))))
    n = len(cases)

    def score(query_terms, case):
        words = Counter(_tokens(field(case)))
        return sum(
            min(words[t], 3) * math.log(1 + n / (1 + df[t])) for t in query_terms if t in words
        )

    return score


def _cosine(cases, field, query):
    """tf-idf cosine between `query` and each case's field: long claims don't win by length."""
    docs = [Counter(_tokens(field(c))) for c in cases]
    df = Counter(t for d in docs for t in d)
    idf = {t: math.log(1 + len(docs) / df[t]) for t in df}

    def vector(counts):
        v = {t: (1 + math.log(n)) * idf.get(t, 0) for t, n in counts.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {t: x / norm for t, x in v.items()}

    q = vector(Counter(_tokens(query)))
    return [sum(q.get(t, 0) * x for t, x in vector(d).items()) for d in docs]


def find(category, query="", limit=3, path=DEFAULT_PATH, exclude_applications=frozenset()):
    """Representative real cases: word overlap with the query, then a mix of outcomes.

    Picks amendment-resolved, argument-only-resolved and unresolved so the checklist shows what
    worked and what did not, not only successes.
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
    lexical = _ranker(cases, lambda c: c["argument_excerpt"])

    def score(case):
        clarity = 0.5 * bool(case["argument_types"]) + 0.3 * (case["examiner_reply"] != "unknown")
        return (lexical(terms, case) + clarity, case["case_id"])

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


@lru_cache
def real_cases():
    """KIPRIS cases with their claim history merged in (when the history file exists)."""
    history = {h["case_id"]: h for h in load(HISTORY_PATH)}
    return tuple(
        c | {k: history[c["case_id"]][k] for k in HISTORY_FIELDS if k in history[c["case_id"]]}
        if c["case_id"] in history
        else c
        for c in load(KR_PATH)
    )


def similar(category, claim_text, limit=5, exclude_applications=frozenset()):
    """Cases whose claim at rejection time shares the most words with `claim_text`.

    Real cases need claim history; DEMO cases stand in only when no real case of the category
    has claim text. ponytail: idf word overlap; swap in local embeddings if ranking is weak.
    """

    def usable(pool):
        return [
            c
            for c in pool
            if c["category"] == category
            and c.get("claims_before")
            and c["outcome"] != "excluded"
            and c["application"] not in exclude_applications
        ]

    def ranked(cases):
        if not cases:
            return []
        scores = _cosine(cases, lambda c: c["claims_before"] + " " + c.get("title", ""), claim_text)
        hits = sorted(zip(scores, (c["case_id"] for c in cases), cases), reverse=True)
        return [
            summary(c) | {"similarity": round(s, 3)}
            for s, _, c in hits[:limit]
            if s >= MIN_SIMILARITY
        ]

    return ranked(usable(real_cases())) or ranked(usable(load(DEMO_PATH)))


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
        for key in (
            "jurisdiction",
            "statute",
            "claims",
            "amendment_summary",
            "demo",
            "title",
            "response_method",
            "claims_before",
            "claims_after",
            "added_limitation",
            "amendment_documents",
            "history_source",
        )
        if case.get(key)
    }


def get(case_id):
    """One case by case_id (real KIPRIS or demo)."""
    return next((c for c in (*real_cases(), *load(DEMO_PATH)) if c["case_id"] == case_id), None)
