from backend.patent.claim_parser import HEADING, parse_claims
from backend.patent.dependency_parser import build_dependency_graph
from backend.schemas import Document, Patent


def parse_patent(document: Document) -> Patent:
    claims = parse_claims(document)
    _, warnings = build_dependency_graph(claims)
    if not HEADING.search(document.text):
        warnings.append(
            "Claims 제목이 없어 입력 전체를 청구항 목록으로 해석했습니다. 추출 범위를 확인하세요."
        )
    return Patent(document_id=document.document_id, claims=claims, warnings=warnings)
