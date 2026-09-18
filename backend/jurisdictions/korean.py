"""Map Korean extraction into the existing US-independent review contract.

No English parser is run over Korean material. The existing graph, dependency,
summary and checklist builders operate on the mapped objects unchanged.
"""

import hashlib

from backend.analysis.checklist_generator import generate_checklist
from backend.analysis.impact_analyzer import analyze_impacts
from backend.errors import DocumentError
from backend.graph.graph_builder import build_graph
from backend.office_action.claim_status import summarize_claim_statuses
from backend.schemas import (
    AnalysisResult,
    CitationDocument,
    CitedReference,
    Claim,
    ClaimDisposition,
    Document,
    Evidence,
    Page,
    Patent,
    Rejection,
    RejectionCitation,
)
from korean_prototype.kr_review.models import ReviewError
from korean_prototype.kr_review.service import analyze as extract_korean


def analyze_korean(
    patent_data,
    patent_filename,
    oa_data,
    oa_filename,
    max_chars=500000,
    references=None,
    amendments=None,
    version_history=None,
):
    try:
        extracted = extract_korean(
            patent_data,
            patent_filename,
            oa_data,
            oa_filename,
            references,
            amendments,
            version_history,
        )
    except ReviewError as exc:
        raise DocumentError(str(exc)) from exc
    if any(len(document.text) > max_chars for document in extracted.documents):
        raise DocumentError(f"추출된 문서는 {max_chars:,}자까지 지원합니다.")

    documents = []
    logical_documents = set()
    for document in extracted.documents:
        pages = [Page(**page.model_dump()) for page in document.pages]
        warnings = list(document.metadata.get("warnings", []))
        if not pages:
            # Same single logical page convention as existing TXT input. Never
            # render/reconstruct a PDF or claim this is the original OA's p.1.
            logical_documents.add(document.document_id)
            pages = [Page(number=1, text=document.text, start=0, end=len(document.text))]
            warnings.append(
                f"{document.filename}: XML 원문은 텍스트 뷰어로 표시합니다. "
                "화면의 p.1은 텍스트 표시용 논리 페이지이며 실제 OA PDF 페이지가 아닙니다."
            )
        documents.append(
            Document(
                document_id=document.document_id,
                filename=document.filename,
                kind=document.kind,
                text=document.text,
                pages=pages,
                warnings=warnings,
                source_metadata=document.metadata,
                metadata={
                    k: v
                    for k, v in document.metadata.items()
                    if k.startswith("ocr_") or k == "removed_margins"
                },
            )
        )

    def evidence(source):
        return Evidence(
            document_id=source.document_id,
            text=source.text,
            start=source.start,
            end=source.end,
            page_numbers=[1] if source.document_id in logical_documents else source.page_numbers,
            xml_path=source.xml_path,
        )

    patent = Patent(
        document_id=documents[0].document_id,
        claims=[
            Claim(
                claim_number=claim.number,
                text=claim.text,
                independent=not claim.depends_on,
                depends_on=claim.depends_on,
                status=claim.status,
                evidence=evidence(claim.evidence),
            )
            for claim in extracted.claims
        ],
    )
    references = {
        citation.citation_id: CitedReference(
            citation_id=citation.citation_id,
            name=citation.title or None,
            publication_number=citation.publication_number,
            evidence=evidence(citation.evidence),
            type=citation.type,
            raw_text=citation.evidence.text,
            title=citation.title or None,
            canonical_key=citation.canonical_key,
            citation_role=citation.role,
            source_document_id=citation.document_id,
        )
        for citation in extracted.citations
    }
    rejections = [
        Rejection(
            rejection_id=rejection.rejection_id,
            action_type="rejection",
            statute=rejection.statute,
            claims=rejection.claims,
            reason_summary=rejection.explanation,
            examiner_explanation=rejection.explanation,
            cited_references=[references[cid] for cid in rejection.citation_ids],
            evidence=evidence(rejection.evidence),
            extraction_method="local",
            statute_code=rejection.statute_code,
            raw_statute_text=rejection.raw_statute_text,
            subject=rejection.subject,
        )
        for rejection in extracted.rejections
    ]
    statuses = [
        ClaimDisposition(
            claim_number=s.claim_number,
            status={"allowable": "allowed", "amended": "pending"}.get(s.status, s.status),
            source_status=s.status,
            raw_status=s.raw_status,
            evidence=evidence(s.evidence) if s.evidence else None,
        )
        for s in extracted.claim_statuses
    ]
    impacts = analyze_impacts(patent, rejections, statuses)
    for rejection, impact in zip(rejections, impacts):
        impact.review_items = generate_checklist(rejection, impact)
    citations = [
        CitationDocument(
            citation_id=ref.citation_id,
            canonical_key=ref.canonical_key,
            display_name=ref.name or ref.publication_number,
            authors=[],
            title=ref.title,
            publication_number=ref.publication_number,
            type=ref.type,
            citation_role=ref.citation_role,
            citation_roles=[ref.citation_role],
            evidence=ref.evidence,
            source_document_id=ref.source_document_id,
        )
        for ref in references.values()
    ]
    edges = [
        RejectionCitation(
            rejection_id=rejection.rejection_id,
            citation_id=ref.citation_id,
            role=ref.citation_role,
            evidence=ref.evidence,
            claim_numbers=rejection.claims,
        )
        for rejection in rejections
        for ref in rejection.cited_references
    ]
    # Namespace prevents cached selection/coordinates leaking across jurisdictions.
    digest = hashlib.sha256(extracted.model_dump_json().encode()).hexdigest()[:16]
    return AnalysisResult(
        analysis_id="kr-" + digest,
        provider="local",
        documents=documents,
        patent=patent,
        rejections=rejections,
        impacts=impacts,
        graph=build_graph(patent, rejections, impacts, statuses),
        warnings=list(
            dict.fromkeys(
                [
                    *extracted.warnings,
                    *(warning for document in documents for warning in document.warnings),
                ]
            )
        ),
        claim_statuses=statuses,
        claim_summary=summarize_claim_statuses(statuses, impacts),
        citations=citations,
        rejection_citations=edges,
        evidence_links=[
            {**link.model_dump(), "evidence": evidence(link.evidence).model_dump()}
            for link in extracted.evidence_links
        ],
        claim_version=extracted.version,
    )
