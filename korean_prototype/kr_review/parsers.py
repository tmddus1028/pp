"""Korean publication headings and structured KIPRIS rejection fields only."""

import re

from .ingestion import evidence_at
from .models import Citation, Claim, Document, Rejection, ReviewError

CLAIM_HEADING = re.compile(r"(?m)^[ \t]*\[?청구항\s*(?:제\s*)?(\d+)\s*항?\]?[ \t]*$")
SECTION_HEADING = re.compile(r"(?m)^[ \t]*\[?청\s*구\s*범\s*위\]?[ \t]*$")
SECTION_END = re.compile(r"(?m)^[ \t]*\[?발명의\s*설명\]?[ \t]*$")
LAW = re.compile(
    r"특허법\s*제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?"
)
DEPENDENCY = re.compile(
    r"^\s*((?:청구항\s*)?제?\s*\d+\s*항[\s\S]{0,140}?)"
    r"(?:에\s*있어서|에\s*따른|에\s*기재된|중\s*(?:어느|어떤)\s*한\s*항)"
)
REFERENCE = re.compile(
    r"인용\s*발명\s*(\d+)\s*[:：]\s*"
    r"(?:(공개특허공보|등록특허공보|특허공보)\s*)?제?\s*"
    r"(10\s*[-－]\s*(?:\d{4}\s*[-－]\s*)?\d{7})\s*호?[^\n]*"
)


def claim_numbers(text: str) -> list[int]:
    """Used only in an explicitly identified claim-list field, never a whole OA."""
    normalized = re.sub(r"(?:청구항|제|항)", "", text)
    numbers = set()
    for start, end in re.findall(r"(\d+)\s*(?:내지|부터|~|∼|～|[-–—])\s*(\d+)", normalized):
        low, high = int(start), int(end)
        if not 0 < low <= high <= 5000:
            raise ReviewError("청구항 번호 범위를 확인할 수 없습니다.")
        numbers.update(range(low, high + 1))
    numbers.update(map(int, re.findall(r"\d+", normalized)))
    if any(number < 1 or number > 5000 for number in numbers):
        raise ReviewError("청구항 번호는 1~5000 범위여야 합니다.")
    return sorted(numbers)


def extract_claims(document: Document) -> list[Claim]:
    section = SECTION_HEADING.search(document.text)
    if section is None:
        raise ReviewError(
            "한국어 청구범위 제목을 찾지 못했습니다. 청구범위·청구항 번호가 포함된 문서를 입력하세요."
        )
    end_match = SECTION_END.search(document.text, section.end())
    section_end = end_match.start() if end_match else len(document.text)
    headings = list(CLAIM_HEADING.finditer(document.text, section.end(), section_end))
    if not headings:
        raise ReviewError("청구범위에서 '청구항 1' 형식의 청구항을 찾지 못했습니다.")
    claims = []
    seen = set()
    for index, heading in enumerate(headings):
        number = int(heading[1])
        if number in seen:
            raise ReviewError(
                f"청구항 {number} 번호가 중복됩니다. 문서의 텍스트 레이어를 확인하세요."
            )
        seen.add(number)
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else section_end
        while start < end and document.text[start].isspace():
            start += 1
        while end > start and document.text[end - 1].isspace():
            end -= 1
        text = document.text[start:end]
        if not text:
            raise ReviewError(f"청구항 {number}의 원문이 비어 있습니다.")
        canceled = bool(re.fullmatch(r"[\[\(]?\s*삭제\s*[\]\)]?\.?", text))
        dependency = DEPENDENCY.search(text) if not canceled else None
        claims.append(
            Claim(
                number=number,
                text=text,
                depends_on=claim_numbers(dependency[1]) if dependency else [],
                status="canceled" if canceled else "active",
                evidence=evidence_at(document, start, end),
            )
        )
    _validate_dependencies(claims)
    return claims


def _validate_dependencies(claims: list[Claim]) -> None:
    mapping = {claim.number: claim for claim in claims}
    for claim in claims:
        for parent in claim.depends_on:
            if parent not in mapping:
                raise ReviewError(
                    f"청구항 {claim.number}의 상위 청구항 {parent}이 입력 문서에 없습니다."
                )
            if mapping[parent].status == "canceled":
                raise ReviewError(
                    f"청구항 {claim.number}이 삭제된 청구항 {parent}을 인용합니다. 버전을 확인하세요."
                )
    visited = set()

    def visit(number: int, path: set[int]) -> None:
        if number in path:
            raise ReviewError("청구항 종속관계에 순환이 있습니다. 청구항 원문을 확인하세요.")
        if number in visited:
            return
        for parent in mapping[number].depends_on:
            visit(parent, path | {number})
        visited.add(number)

    for number in mapping:
        visit(number, set())


def _content(document: Document, item: dict) -> str:
    return document.text[item["start"] : item["end"]]


def _statute(value: str) -> str:
    return "특허법 " + re.sub(r"\s+", "", value.removeprefix("특허법"))


def _citation_number(match: re.Match) -> str:
    parts = re.split(r"[-－]", re.sub(r"\s+", "", match[3]))
    if len(parts) == 3:
        if match[2] == "등록특허공보":
            raise ReviewError("인용발명의 공개번호와 등록공보 표시가 일치하지 않습니다.")
        return f"KR{parts[1]}{parts[2]}A"
    return "KR" + "".join(parts)


def extract_office_action(document: Document) -> tuple[list[Rejection], list[Citation]]:
    elements = document.metadata.get("xml_elements", [])
    rows = [
        item
        for item in elements
        if item["name"] == "Row" and ":ExaminationLawArticle[" in item["path"]
    ]
    details = [item for item in elements if item["name"] == "RejectionLawDetail"]
    if not rows or not details:
        raise ReviewError(
            "XML에서 거절이유 표와 구체적인 거절이유를 확인하지 못했습니다. 지원 형식을 확인하세요."
        )
    citations: list[Citation] = []
    by_number = {}
    detail_citations: dict[str, list[str]] = {}
    for detail in details:
        citation_ids = []
        for match in REFERENCE.finditer(_content(document, detail)):
            publication = _citation_number(match)
            if publication not in by_number:
                citation = Citation(
                    citation_id=f"C{len(citations) + 1}",
                    publication_number=publication,
                    title=f"인용발명 {match[1]}",
                    evidence=evidence_at(
                        document,
                        detail["start"] + match.start(),
                        detail["start"] + match.end(),
                        detail["path"],
                    ),
                )
                citations.append(citation)
                by_number[publication] = citation
            citation_ids.append(by_number[publication].citation_id)
        detail_citations[detail["path"]] = list(dict.fromkeys(citation_ids))

    rejections = []
    seen = set()
    assigned_details = set()
    for row in rows:
        entries = [
            item
            for item in elements
            if item["name"] == "Entry" and item["path"].startswith(row["path"] + "/")
        ]
        claim_cells = [
            item
            for item in entries
            if re.search(r"청구항|제\s*\d+\s*항", _content(document, item))
            and not LAW.search(_content(document, item))
        ]
        law_cells = [item for item in entries if LAW.search(_content(document, item))]
        if not claim_cells or not law_cells:
            continue
        numbers = claim_numbers(_content(document, claim_cells[0]))
        if not numbers:
            continue
        for cell in law_cells:
            for law_match in LAW.finditer(_content(document, cell)):
                statute = _statute(law_match[0])
                key = tuple(numbers), statute
                if key in seen:
                    continue
                seen.add(key)
                matching_details = [
                    detail
                    for detail in details
                    if statute
                    in {_statute(match[0]) for match in LAW.finditer(_content(document, detail))}
                ]
                if len(matching_details) != 1:
                    raise ReviewError(
                        f"{statute} 거절이유 표와 본문 구간을 하나로 연결할 수 없습니다. "
                        "이 XML 구조는 추가 검증이 필요합니다."
                    )
                detail = matching_details[0]
                if detail["path"] in assigned_details:
                    raise ReviewError(
                        "하나의 거절이유 본문에 여러 청구항 범위 또는 법조항이 연결됩니다. "
                        "인용발명 관계를 정확히 나눌 수 없어 이 XML 구조는 아직 지원하지 않습니다."
                    )
                assigned_details.add(detail["path"])
                rejections.append(
                    Rejection(
                        rejection_id=f"R{len(rejections) + 1}",
                        claims=numbers,
                        statute=statute,
                        explanation=_content(document, detail),
                        evidence=evidence_at(
                            document, detail["start"], detail["end"], detail["path"]
                        ),
                        citation_ids=detail_citations[detail["path"]],
                    )
                )
    if not rejections:
        raise ReviewError(
            "지원하는 형식의 명시적 거절이유를 찾지 못했습니다. 거절 없음으로 처리하지 않습니다."
        )
    relied = {citation_id for rejection in rejections for citation_id in rejection.citation_ids}
    return rejections, [citation for citation in citations if citation.citation_id in relied]
