"""Deterministic Korean prototype orchestration, isolated from the US application."""

from .ingestion import read_document
from .links import retrieve_links
from .models import AnalysisResult, ReviewError
from .parsers import extract_claims, extract_office_action
from .status import extract_statuses


def analyze(
    patent_data: bytes,
    patent_filename: str,
    oa_data: bytes,
    oa_filename: str,
    references: list[tuple[str, bytes]] | None = None,
    amendments: list[tuple[str, bytes]] | None = None,
    version_history: dict | None = None,
) -> AnalysisResult:
    if len(references or []) > 10:
        raise ReviewError("인용발명은 최대 10개까지 입력할 수 있습니다.")
    office_action = read_document(oa_data, oa_filename, "office_action")
    from .versions import select_version

    (patent_data, patent_filename), version = select_version(
        (patent_data, patent_filename),
        [(data, name) for name, data in amendments or []],
        version_history,
        office_action.metadata.get("document_date", ""),
    )
    patent = read_document(patent_data, patent_filename, "patent")
    patent_application = patent.metadata.get("application_number")
    oa_application = office_action.metadata.get("application_number")
    if patent_application and patent_application != oa_application:
        raise ReviewError(
            "명세서와 의견제출통지서의 출원번호가 다릅니다. 같은 출원의 자료를 입력하세요."
        )
    warnings = []
    if not patent_application:
        warnings.append(
            "명세서에서 출원번호를 읽지 못해 두 입력의 동일 출원 여부를 확인하지 못했습니다."
        )
    warnings.append("출원번호 일치는 심사 당시 청구항 버전의 동일성을 자동 보증하지 않습니다.")
    warnings.append("청구범위 버전 확인 필요: " + version["reason"])
    claims = extract_claims(patent)
    rejections, citations = extract_office_action(office_action)
    active = {claim.number for claim in claims if claim.status == "active"}
    direct = {number for rejection in rejections for number in rejection.claims}
    if unknown := direct - active:
        raise ReviewError(
            "거절이유의 청구항이 입력 명세서에 없거나 삭제 상태입니다: "
            + ", ".join(map(str, sorted(unknown)))
            + ". 심사 당시 버전을 확인하세요."
        )
    documents = [patent, office_action]
    reference_by_publication = {}
    seen_document_ids = {document.document_id for document in documents}
    for filename, data in references or []:
        try:
            document = read_document(data, filename, "reference")
        except ReviewError as exc:
            warnings.append(
                f"{filename}: 인용발명 원문 사용 불가 ({exc}). 청구항·거절이유 분석은 유지합니다."
            )
            continue
        if document.document_id in seen_document_ids:
            continue
        seen_document_ids.add(document.document_id)
        documents.append(document)
        publication = document.metadata.get("publication_number")
        if not publication:
            warnings.append(
                f"{filename}: 문서 본문에서 공개·등록번호를 확인하지 못해 인용발명에 자동 연결하지 않았습니다."
            )
        elif publication in reference_by_publication:
            raise ReviewError(
                f"{publication}에 서로 다른 문서가 입력되었습니다. 올바른 원문 하나를 선택하세요."
            )
        else:
            reference_by_publication[publication] = document
            if publication not in {c.publication_number for c in citations}:
                warnings.append(
                    f"{filename}: {publication}은 이 거절이유의 인용발명 번호와 일치하지 않아 연결하지 않았습니다."
                )
    for citation in citations:
        linked = reference_by_publication.get(citation.publication_number)
        if linked:
            citation.document_id = linked.document_id
            citation.title = linked.metadata.get("title") or citation.title
        else:
            warnings.append(f"{citation.publication_number}: 인용발명 원문이 입력되지 않았습니다.")

    statuses = extract_statuses(claims, rejections, office_action)
    terminal = {
        s.claim_number for s in statuses if s.status in {"allowable", "withdrawn", "canceled"}
    }
    impacted = set()
    changed = True
    while changed:
        changed = False
        for claim in claims:
            if claim.number in active - direct - impacted - terminal and set(claim.depends_on) & (
                direct | impacted
            ):
                impacted.add(claim.number)
                changed = True
    for document in documents:
        warnings.extend(document.metadata.get("warnings", []))
    return AnalysisResult(
        application_number=oa_application,
        title=office_action.metadata.get("title") or patent.metadata.get("title", ""),
        office_action_date=office_action.metadata.get("document_date", ""),
        documents=documents,
        claims=claims,
        rejections=rejections,
        citations=citations,
        direct_claims=sorted(direct),
        dependency_claims=sorted(impacted),
        warnings=list(dict.fromkeys(warnings)),
        claim_statuses=statuses,
        evidence_links=retrieve_links(patent, claims, rejections, citations, documents),
        version=version,
    )
