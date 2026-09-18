"""Exact source chunks and transparent lexical candidates, never invented support."""

import re

from .ingestion import evidence_at
from .models import EvidenceLink


def chunks(document):
    from .models import ReviewError
    from .parsers import extract_claims

    if document.kind == "reference":
        try:
            for claim in extract_claims(document):
                yield f"청구항 {claim.number}", claim.evidence.start, claim.evidence.end
        except ReviewError:
            pass
        for figure in re.finditer(r"(?m)^\s*도\s*(\d+)\s*$", document.text):
            yield f"도 {figure[1]}", figure.start(), figure.end()
    # KR publications put [0001] either before or after the first text line.
    markers = list(re.finditer(r"\[\s*(\d{4})\s*\]", document.text))
    if markers:
        for i, marker in enumerate(markers):
            start = document.text.rfind("\n", 0, marker.start()) + 1
            # A marker at line end labels that same line, not the next line.
            end = (
                document.text.rfind("\n", 0, markers[i + 1].start()) + 1
                if i + 1 < len(markers)
                else len(document.text)
            )
            if end > start:
                yield marker[1], start, min(end, start + 1800)
    else:
        for page in document.pages:
            for start in range(page.start, page.end, 1200):
                yield f"p.{page.number}", start, min(page.end, start + 1200)


def terms(text):
    words = set(re.findall(r"[가-힣]{2,}|[A-Za-z]{3,}", text.lower()))
    return words - {"청구항", "있어서", "포함하는", "특징으로", "인용발명", "발명은", "상기"}


def retrieve_links(patent, claims, rejections, citations, documents):
    links = []
    docs = {d.document_id: d for d in documents}
    for rejection in rejections:
        query = " ".join(c.text for c in claims if c.number in rejection.claims)
        query_terms = terms(query)
        targets = [(None, patent)] + [
            (c, docs[c.document_id])
            for c in citations
            if c.citation_id in rejection.citation_ids and c.document_id in docs
        ]
        for citation, doc in targets:
            pins = set()
            if citation:
                # Only read pinpoint expressions in a passage explicitly naming
                # this reference; do not assign another reference's paragraphs.
                for alias in citation.aliases:
                    pattern = rf"인용\s*(?:발명|문헌)\s*{re.escape(alias)}(?!\d)[\s\S]*?(?=인용\s*(?:발명|문헌)\s*\d|\n\n|$)"
                    for mention in re.finditer(pattern, rejection.explanation):
                        for a, b in re.findall(r"\[(\d{4})\]\s*[-~∼]\s*\[(\d{4})\]", mention[0]):
                            if 0 <= int(b) - int(a) <= 100:
                                pins.update(f"{n:04d}" for n in range(int(a), int(b) + 1))
                        pins.update(re.findall(r"\[(\d{4})\]", mention[0]))
                        for claim_list in re.finditer(
                            r"청구항\s*(\d+(?:\s*[,및~∼-]\s*\d+)*)", mention[0]
                        ):
                            from .parsers import claim_numbers

                            pins.update(f"청구항 {n}" for n in claim_numbers(claim_list[1]))
                        pins.update(f"도 {n}" for n in re.findall(r"도\s*(\d+)", mention[0]))
                        pins.update(
                            f"p.{n}" for n in re.findall(r"(?:페이지|쪽|p\.)\s*(\d+)", mention[0])
                        )
            candidates = []
            available = list(chunks(doc))
            available += [
                (f"p.{p.number}", p.start, p.end) for p in doc.pages if f"p.{p.number}" in pins
            ]
            for label, start, end in available:
                if not citation and any(
                    c.evidence.start < end and start < c.evidence.end for c in claims
                ):
                    continue
                value = doc.text[start:end]
                overlap = query_terms & terms(value)
                explicit = label in pins
                if explicit or len(overlap) >= 3:
                    score = len(overlap) / max(1, len(query_terms))
                    candidates.append((explicit, score, label, start, end))
            candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            for explicit, score, label, start, end in candidates[:3]:
                links.append(
                    EvidenceLink(
                        claim_numbers=rejection.claims,
                        citation_id=citation.citation_id if citation else None,
                        rejection_id=rejection.rejection_id,
                        provenance="examiner_explicit_evidence"
                        if explicit
                        else "system_retrieved_evidence",
                        confidence="high" if explicit else "medium",
                        label=("인용발명" if citation else "명세서")
                        + f" [{label}] · "
                        + ("심사관 지정" if explicit else "시스템 검색 후보"),
                        evidence=evidence_at(doc, start, end),
                    )
                )
    return links
