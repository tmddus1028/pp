"""Read-only access to the Korean response-precedent table (KIPRIS) plus labelled demo cases.

KR: scripts/build_kr_precedents.py (KIPRIS Plus). The JSONL file is the source of truth so the
demo works without PostgreSQL; scripts/load_precedents_pg.py copies it into `response_cases`.

KIPRIS records carry no claim text; scripts/build_kr_claim_history.py adds it per case from the
claim-change history (kr_claim_history.jsonl: claims before/after the response, added wording).
scripts/build_kr_opinions.py adds the applicant's own 의견서 text (kr_opinions.jsonl, from PDFs
downloaded by hand from 특허청 OPD): applicant_argument is their conclusion, opinion_text the body.
`kr_demo_cases.jsonl` holds clearly marked DEMO cases, used for similar-case retrieval only in a
category where no real case has claim text yet. Demo cases never enter the statistics.
"""

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import httpx

from backend.precedents.taxonomy import argument_label, label

ROOT = Path(__file__).resolve().parents[2]
KR_PATH = ROOT / "data/precedents/kr_kipris_cases.jsonl"
DEMO_PATH = ROOT / "data/precedents/kr_demo_cases.jsonl"
HISTORY_PATH = ROOT / "data/precedents/kr_claim_history.jsonl"
OPINION_PATH = ROOT / "data/precedents/kr_opinions.jsonl"
IPC_PATH = ROOT / "data/precedents/kr_ipc.jsonl"  # scripts/build_kr_ipc.py
EMBEDDING_PATH = ROOT / "data/precedents/kr_claim_embeddings.npz"  # build_kr_embeddings.py
DEFAULT_PATH = KR_PATH
HISTORY_FIELDS = (
    "claims_before",
    "claims_after",
    "added_limitation",
    "response_method",
    "amendment_documents",
    "history_source",
)
OPINION_FIELDS = ("opinion_date", "opinion_file", "applicant_argument", "opinion_text")
NOTE = (
    "한국 특허청 실제 사건(KIPRIS 의견제출통지서·거절결정서·등록결정서)의 집계입니다. 표본이 작아 "
    "경향으로 해석하지 말고 사례로만 참고하세요. 변리사 검토가 필요합니다."
)
MIN_ARGUMENT_CASES = 5
# Calibration knob: tf-idf cosine below this is unrelated technology in practice (e.g. a coupon
# claim vs. a drug composition scored ~0.08). Re-tune once cases are filtered by IPC.
MIN_SIMILARITY = 0.15
# bge-m3 cosine between claims of different IPC main groups exceeds 0.63 for only ~1% of pairs
# (median 0.45): a different-field case is shown only above it.
CROSS_FIELD_COSINE = 0.63
RRF_K = 60
MORPHEME_TAGS = {"NNG", "NNP", "SL", "SH", "XR", "VV", "VA"}
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


@lru_cache
def _kiwi():
    from kiwipiepy import Kiwi

    return Kiwi()


def morphemes(text):
    """Nouns and verb/adjective stems (Kiwi): "통신부를" and "통신부가" are the same word."""
    return [
        t.form.lower()
        for t in _kiwi().tokenize(text or "")
        if t.tag in MORPHEME_TAGS and t.form not in STOPWORDS and len(t.form) > 1
    ]


def _bm25(cases, field, query, k1=1.5, b=0.75):
    docs = [Counter(morphemes(field(c))) for c in cases]
    lengths = [sum(d.values()) for d in docs]
    average = sum(lengths) / len(docs) or 1
    df = Counter(t for d in docs for t in d)
    n = len(docs)
    terms = set(morphemes(query))
    return [
        sum(
            math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            * d[t]
            * (k1 + 1)
            / (d[t] + k1 * (1 - b + b * length / average))
            for t in terms
            if t in d
        )
        for d, length in zip(docs, lengths)
    ]


@lru_cache
def case_embeddings():
    """{case_id: unit vector} from scripts/build_kr_embeddings.py, {} when not built."""
    if not EMBEDDING_PATH.exists():
        return {}
    import numpy as np

    data = np.load(EMBEDDING_PATH)
    return dict(zip(data["ids"].tolist(), data["vectors"].astype("float32")))


def query_embedding(text):
    """Unit bge-m3 vector of `text` from local Ollama, or None: search then uses words only."""
    from backend.config import Settings

    settings = Settings()
    if not settings.precedent_embedding_model or not (text or "").strip():
        return None
    try:
        response = httpx.post(
            f"{settings.local_llm_base_url}/api/embed",
            json={"model": settings.precedent_embedding_model, "input": [text[:4000]]},
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None
    import numpy as np

    vector = np.asarray(response.json()["embeddings"][0], dtype="float32")
    return vector / (np.linalg.norm(vector) or 1)


def _ranks(scores):
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    return {i: rank for rank, i in enumerate(order)}


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
    """KIPRIS cases with their claim history and 의견서 merged in (when those files exist)."""
    extras = [
        ({h["case_id"]: h for h in load(HISTORY_PATH)}, HISTORY_FIELDS),
        ({o["case_id"]: o for o in load(OPINION_PATH)}, OPINION_FIELDS),
    ]
    ipc = {r["application"]: r["ipc"] for r in load(IPC_PATH)}
    return tuple(
        c
        | {
            k: rows[c["case_id"]][k]
            for rows, fields in extras
            if c["case_id"] in rows
            for k in fields
            if k in rows[c["case_id"]]
        }
        | {"ipc": ipc.get(c["application"], [])}
        for c in load(KR_PATH)
    )


def subclasses(codes):
    """IPC subclasses ("H01L 31/042" → "H01L"): same subclass ≈ same field of technology."""
    return {code[:4] for code in codes or ()}


def main_groups(codes):
    return {code.split("/")[0] for code in codes or ()}


def similar(category, claim_text, limit=5, exclude_applications=frozenset(), ipc=()):
    """Past cases whose rejected claim resembles `claim_text`.

    Hybrid ranking (DAPFAM 2025: hybrid beats either alone): Kiwi-morpheme BM25 and bge-m3
    claim embeddings fused by reciprocal rank, plus a bonus for the same IPC main group /
    subclass as the patent. On the DB itself (219 claims, relevance = shared IPC) this raised
    nDCG@5 from 0.31 (tf-idf) to 0.35 before the IPC bonus.
    Shown: same-subclass cases with shared words, or any case that is very close
    (CROSS_FIELD_COSINE; tf-idf MIN_SIMILARITY when embeddings are unavailable).
    Real cases need claim history; DEMO cases stand in only when no real case qualifies.
    """
    fields, groups = subclasses(ipc), main_groups(ipc)

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
        if not cases or not (claim_text or "").strip():
            return []

        def text(c):
            return c["claims_before"] + " " + c.get("title", "")

        words = _bm25(cases, text, claim_text)
        tfidf = _cosine(cases, text, claim_text)
        query, vectors = query_embedding(claim_text), case_embeddings()
        cosine = [
            float(vectors[c["case_id"]] @ query)
            if query is not None and c["case_id"] in vectors
            else None
            for c in cases
        ]
        orders = [_ranks(words)] + (
            [_ranks([-1.0 if x is None else x for x in cosine])]
            if any(x is not None for x in cosine)
            else []
        )
        hits = []
        for i, case in enumerate(cases):
            same_field = bool(fields & subclasses(case.get("ipc")))
            similarity = cosine[i] if cosine[i] is not None else tfidf[i]
            floor = CROSS_FIELD_COSINE if cosine[i] is not None else MIN_SIMILARITY
            if not ((same_field and words[i] > 0) or similarity >= floor):
                continue
            score = sum(1 / (RRF_K + 1 + order[i]) for order in orders)
            score += (bool(groups & main_groups(case.get("ipc"))) + same_field) / (2 * (RRF_K + 1))
            hits.append((score, case["case_id"], case, similarity))
        hits.sort(key=lambda h: (-h[0], h[1]))
        return [summary(c) | {"similarity": round(s, 3)} for _, _, c, s in hits[:limit]]

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
            "opinion_date",
            "applicant_argument",
            "ipc",
        )
        if case.get(key)
    }


def get(case_id):
    """One case by case_id (real KIPRIS or demo)."""
    return next((c for c in (*real_cases(), *load(DEMO_PATH)) if c["case_id"] == case_id), None)
