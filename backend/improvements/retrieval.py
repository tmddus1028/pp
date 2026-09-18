"""Bounded, deterministic retrieval of original specification candidates, not support labels."""

import hashlib
import json
import re
from collections import Counter
from math import sqrt

from backend.improvements.context import MAX_CONTEXT_CHARS, build_context
from backend.improvements.models import ReviewEvidence
from backend.schemas import Evidence

STOP = set(
    "a an the of and or is are with to in for as by said wherein comprising claim claims 청구항 상기 및 또는 하는 있는".split()
)


def terms(text):
    return Counter(t for t in re.findall(r"[\w]+", text.lower()) if t not in STOP and len(t) > 1)


def cosine(left, right):
    a, b = terms(left), terms(right)
    norm = sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return sum(v * b[k] for k, v in a.items()) / norm if norm else 0.0


def specification_chunks(analysis):
    doc = next(d for d in analysis.documents if d.document_id == analysis.patent.document_id)
    # Subtract every Claim source interval before chunking: a Claim cannot support itself.
    excluded = sorted((c.evidence.start, c.evidence.end) for c in analysis.patent.claims)
    ranges, cursor = [], 0
    for start, end in excluded:
        if start > cursor:
            ranges.append((cursor, start))
        cursor = max(cursor, end)
    ranges.append((cursor, len(doc.text)))
    chunks = []
    for lo, hi in ranges:
        boundaries = [lo] + [
            m.start() for m in re.finditer(r"\[\s*\d{4,5}\s*\]|\n\s*\n", doc.text[lo:hi])
        ]
        # regex positions above are relative; keep original offsets throughout.
        boundaries = [lo] + [lo + p for p in boundaries[1:]] + [hi]
        for start, end in zip(boundaries, boundaries[1:]):
            while start < end:
                stop = min(start + 1200, end)
                if stop < end:
                    split = doc.text.rfind(" ", start + 600, stop)
                    if split > start:
                        stop = split
                left = start
                while left < stop and doc.text[left].isspace():
                    left += 1
                right = stop
                while right > left and doc.text[right - 1].isspace():
                    right -= 1
                if right - left >= 40:
                    text = doc.text[left:right]
                    chunks.append(
                        ReviewEvidence(
                            evidence_id=f"SPEC-RETRIEVED-{left}-{right}",
                            kind="specification",
                            label="명세서 검색 후보 · 지지 여부 미판정",
                            navigation_item=f"spec-{left}",
                            evidence=Evidence(
                                document_id=doc.document_id,
                                text=text,
                                start=left,
                                end=right,
                                page_numbers=[
                                    p.number for p in doc.pages if p.start < right and p.end > left
                                ],
                            ),
                        )
                    )
                start = stop
    return chunks


def retrieved_context(request, queries):
    context, sources, _ = build_context(request)
    candidates = specification_chunks(request.analysis)
    selections, selected, scores = {}, {}, {}
    for key, text in queries:
        ranked = sorted(
            ((cosine(text, s.evidence.text), s) for s in candidates),
            key=lambda p: (-p[0], p[1].evidence.start),
        )
        selections[key] = []
        scores[key] = None
        for score, source in ranked[:3]:
            if score <= 0:
                continue
            if len(selected) >= 12 and source.evidence_id not in selected:
                continue
            selected[source.evidence_id] = source
            selections[key].append(source.evidence_id)
            scores[key] = max(scores[key] or 0, score)
    sources += [
        s for s in selected.values() if s.evidence_id not in {x.evidence_id for x in sources}
    ]
    # KR reference candidates use the revised elements too, not only the old claim.
    reference_candidates = {}
    if context["jurisdiction"] == "kr":
        registry = {c.citation_id: c for c in request.analysis.citations}
        documents = {d.document_id: d for d in request.analysis.documents}
        budget = 6
        for citation in context["citations"]:
            ref = registry.get(citation["citation_id"])
            doc = documents.get(ref.source_document_id) if ref else None
            if not doc or doc.kind != "reference":
                continue
            ranked = []
            for page in doc.pages:
                # Exclude cover-page bibliographic identity/address fields from
                # technical retrieval. The unchanged PDF stays in the viewer.
                beginning = page.start
                if page.number == 1:
                    abstract = re.search(r"\(57\)\s*요\s*약", page.text)
                    if abstract:
                        beginning = page.start + abstract.end()
                    elif re.search(r"\(7[12]\)|출원인|발명자", page.text):
                        continue
                for start in range(beginning, page.end, 1200):
                    end = min(start + 1200, page.end)
                    score = max(
                        (cosine(text, doc.text[start:end]) for _, text in queries), default=0
                    )
                    if score > 0:
                        ranked.append((score, start, end))
            for _, start, end in sorted(ranked, reverse=True)[:2]:
                eid = f"REF-REVISED-{doc.document_id}-{start}"
                if budget <= 0 or any(s.evidence_id == eid for s in sources):
                    continue
                budget -= 1
                sources.append(
                    ReviewEvidence(
                        evidence_id=eid,
                        kind="citation_original",
                        label=f"인용발명 {citation['citation_id']} · 수정 요소 검색 후보",
                        provenance="system_retrieved_evidence",
                        navigation_item="citation-" + citation["citation_id"],
                        evidence=Evidence(
                            document_id=doc.document_id,
                            text=doc.text[start:end],
                            start=start,
                            end=end,
                            page_numbers=[
                                p.number for p in doc.pages if p.start < end and start < p.end
                            ],
                        ),
                    )
                )
                citation.setdefault("original_evidence_ids", []).append(eid)
                citation["original_available"] = True
                reference_candidates.setdefault(citation["citation_id"], []).append(eid)
    context["sources"] = [s.model_dump(mode="json") for s in sources]
    context["retrieval"] = {
        "method": "lexical cosine top-3 per element, max 12",
        "candidates": selections,
        "support_is_unverified": True,
    }
    if reference_candidates:
        context["retrieval"]["reference_candidates"] = reference_candidates
    if selected:
        context["missing_evidence"] = [
            m for m in context["missing_evidence"] if "자동 연결된 명세서 근거가 없어" not in m
        ]
    context["retrieval_limitations"] = [
        "명세서 검색 후보의 유사도는 support 판정이 아닙니다. 검색에서 누락된 근거가 있을 수 있습니다."
    ]
    digest = context_hash(context)
    return context, sources, digest, selections, scores


def context_hash(context):
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True)
    if len(serialized) > MAX_CONTEXT_CHARS:
        raise ValueError(
            "관련 검토 근거가 48,000자 한도를 넘습니다. 거절 범위 또는 수정 청구항을 줄이세요."
        )
    return hashlib.sha256(serialized.encode()).hexdigest()
