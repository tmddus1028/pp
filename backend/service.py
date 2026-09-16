import hashlib

from backend.analysis.checklist_generator import generate_checklist
from backend.analysis.citation_registry import build_citation_registry
from backend.analysis.impact_analyzer import analyze_impacts
from backend.config import Settings
from backend.graph.graph_builder import build_graph
from backend.llm.client import ExtractionClient, OpenAIExtractionClient
from backend.llm.structured_extraction import extract_structured, merge_rejections
from backend.office_action.claim_status import extract_claim_statuses, summarize_claim_statuses
from backend.office_action.rejection_extractor import extract_local
from backend.patent.patent_parser import parse_patent
from backend.schemas import AnalysisResult, Document


def analyze(
    patent_document: Document,
    oa_document: Document,
    settings: Settings | None = None,
    client: ExtractionClient | None = None,
) -> AnalysisResult:
    settings = settings or Settings()
    patent = parse_patent(patent_document)
    if settings.llm_provider == "local":
        rejections, warnings = extract_local(oa_document, settings.oa_chunk_chars)
    else:
        owned_client = OpenAIExtractionClient(settings) if client is None else None
        try:
            rejections, warnings = extract_structured(
                oa_document, client or owned_client, settings.llm_provider, settings.oa_chunk_chars
            )
        finally:
            if owned_client:
                owned_client.close()
    rejections = merge_rejections(rejections)
    citations, citation_edges = build_citation_registry(oa_document, rejections)
    statuses = extract_claim_statuses(oa_document, patent, rejections)
    impacts = analyze_impacts(patent, rejections, statuses)
    for rejection, impact in zip(rejections, impacts):
        impact.review_items = generate_checklist(rejection, impact)
        if impact.missing_claims:
            warnings.append(
                f"{rejection.rejection_id}: Claim {impact.missing_claims}의 원문이 없거나 취소 상태입니다. 청구항 버전을 확인하세요."
            )
    warnings = list(
        dict.fromkeys(patent_document.warnings + oa_document.warnings + patent.warnings + warnings)
    )
    # Content-addressed result includes extraction output, so different LLM runs cannot collide.
    digest_input = "|".join(
        [patent_document.document_id, oa_document.document_id, settings.llm_provider]
        + [r.model_dump_json() for r in rejections]
        + [s.model_dump_json() for s in statuses]
        + [i.model_dump_json() for i in impacts]
        + [c.model_dump_json() for c in citations]
        + [e.model_dump_json() for e in citation_edges]
    )
    analysis_id = hashlib.sha256(digest_input.encode()).hexdigest()[:20]
    return AnalysisResult(
        analysis_id=analysis_id,
        provider=settings.llm_provider,
        documents=[patent_document, oa_document],
        patent=patent,
        rejections=rejections,
        impacts=impacts,
        graph=build_graph(patent, rejections, impacts, statuses),
        claim_statuses=statuses,
        claim_summary=summarize_claim_statuses(statuses, impacts),
        warnings=warnings,
        citations=citations,
        rejection_citations=citation_edges,
    )
