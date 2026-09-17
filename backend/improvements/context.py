"""Bounded context from existing links, with exact offsets and no document rewriting."""

import hashlib
import json
import re

from backend.improvements.models import ImprovementRequest, ReviewEvidence
from backend.schemas import Evidence
from frontend.review_model import explicit_support

MAX_CONTEXT_CHARS = 48000
REWRITE_PHRASE = re.compile(
    r"would\s+be\s+allowable\s+if\s+rewritten\s+in\s+independent\s+form", re.I
)


def build_context(request: ImprovementRequest):
    result = request.analysis
    claims = {c.claim_number: c for c in result.patent.claims}
    claim = claims.get(request.claim_number)
    if claim is None or claim.status == "canceled":
        raise ValueError("검토할 활성 청구항 원문이 없습니다.")
    status = next((s for s in result.claim_statuses if s.claim_number == claim.claim_number), None)
    if status and status.status in {"allowed", "withdrawn", "canceled"}:
        raise ValueError("이 청구항은 현재 거절·지적 검토 대상이 아닙니다.")
    related = {
        i.rejection_id
        for i in result.impacts
        if claim.claim_number in i.direct_claims + i.objected_claims + i.dependency_impacted_claims
    } | {r.rejection_id for r in result.rejections if claim.claim_number in r.claims}
    rejections = [
        r
        for r in result.rejections
        if r.rejection_id in related
        and (request.rejection_id is None or r.rejection_id == request.rejection_id)
    ]
    if not rejections:
        raise ValueError("선택 청구항과 연결된 거절·지적 사유가 없습니다.")
    documents = {d.document_id: d for d in result.documents}
    sources = []

    def add(eid, kind, label, evidence, item):
        doc = documents.get(evidence.document_id)
        if (
            doc is None
            or evidence.end <= evidence.start
            or doc.text[evidence.start : evidence.end] != evidence.text
        ):
            raise ValueError("개선 검토 근거가 원문 위치와 일치하지 않습니다.")
        pages = [p.number for p in doc.pages if p.start < evidence.end and p.end > evidence.start]
        if pages != evidence.page_numbers:
            raise ValueError("개선 검토 근거 페이지가 원문과 일치하지 않습니다.")
        sources.append(
            ReviewEvidence(
                evidence_id=eid, kind=kind, label=label, evidence=evidence, navigation_item=item
            )
        )
        return eid

    add(
        "CLAIM-" + str(claim.claim_number),
        "claim",
        f"청구항 {claim.claim_number}",
        claim.evidence,
        f"claim-{claim.claim_number}",
    )
    missing, parents, visited = [], [], {claim.claim_number}

    def ancestors(number, path):
        for parent in claims[number].depends_on:
            if parent in path:
                raise ValueError("종속관계에 순환이 있어 개선 검토를 진행할 수 없습니다.")
            if parent not in claims:
                missing.append(f"상위 청구항 {parent} 원문 미확보")
                continue
            if parent in visited:
                continue
            visited.add(parent)
            c = claims[parent]
            eid = add(
                f"PARENT-{parent}",
                "parent_claim",
                f"상위 청구항 {parent}",
                c.evidence,
                f"claim-{parent}",
            )
            parents.append(
                {
                    "claim_number": parent,
                    "text": c.text,
                    "depends_on": c.depends_on,
                    "evidence_id": eid,
                }
            )
            ancestors(parent, path | {parent})

    ancestors(claim.claim_number, {claim.claim_number})
    bases, citations = [], []
    for r in rejections:
        eid = add(
            f"OA-{r.rejection_id}",
            "office_action",
            f"{r.rejection_id} · {r.statute}",
            r.evidence,
            f"rejection-{r.rejection_id}",
        )
        bases.append(
            {
                "rejection_id": r.rejection_id,
                "statute": r.statute,
                "action_type": r.action_type,
                "direct": claim.claim_number in r.claims,
                "evidence_id": eid,
            }
        )
        for ref in r.cited_references:
            if ref.citation_role != "relied_upon":
                continue
            eid = add(
                f"CITE-{r.rejection_id}-{ref.citation_id}",
                "citation_mention",
                ref.name or ref.publication_number or ref.citation_id,
                ref.evidence,
                "citation-" + ref.citation_id,
            )
            citations.append(
                {
                    "citation_id": ref.citation_id,
                    "rejection_id": r.rejection_id,
                    "name": ref.name,
                    "publication_number": ref.publication_number,
                    "evidence_id": eid,
                    "original_available": False,
                }
            )
    # Reuse the exact existing UI link policy. No search-based/speculative support links.
    for link in explicit_support(result.model_dump(mode="json")):
        if link["rejection_id"] in {r.rejection_id for r in rejections} and link["figure"] is None:
            add(
                "SPEC-" + link["id"],
                "specification",
                link["label"],
                Evidence.model_validate(link["evidence"]),
                link["id"],
            )
    if status and status.evidence:
        add(
            "STATUS",
            "status",
            "심사관 청구항 상태 근거",
            status.evidence,
            f"claim-{claim.claim_number}",
        )
    # Require the actual examiner wording, not only a status flag. Restrict to its ground.
    rewrite = bool(
        status
        and status.conditional_allowance
        and status.evidence
        and parents
        and not missing
        and REWRITE_PHRASE.search(status.evidence.text)
        and any(r.action_type == "objection" and claim.claim_number in r.claims for r in rejections)
    )
    if not any(s.kind == "specification" for s in sources):
        missing.append(
            "현재 자동 연결된 명세서 근거가 없어 구체적인 기술적 한정·추가 보정안은 제시하지 않습니다."
        )
    if citations:
        missing.append(
            "선행문헌 원문 미확보: 인용 위치는 심사관 문서의 인용 문장입니다. 선행문헌 본문을 읽거나 기술적 차이를 검증한 결과가 아닙니다."
        )
    context = {
        "jurisdiction": "kr" if result.analysis_id.startswith("kr-") else "us",
        "claim_number": claim.claim_number,
        "claim_text": claim.text,
        "claim_status": status.status if status else "unknown",
        "depends_on": claim.depends_on,
        "parents": parents,
        "rejections": bases,
        "citations": citations,
        "conditional_rewrite_supported": rewrite,
        "missing_evidence": missing,
        "sources": [s.model_dump(mode="json") for s in sources],
    }
    serialized = json.dumps(context, ensure_ascii=False, sort_keys=True)
    if len(serialized) > MAX_CONTEXT_CHARS:
        raise ValueError(
            "관련 근거가 개선 검토 입력 한도(48,000자)를 초과합니다. 거절 사유를 하나만 선택해 주세요."
        )
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    return context, sources, digest
