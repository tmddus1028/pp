"""Korean publication headings and structured KIPRIS rejection fields only."""

import re
import unicodedata

from .ingestion import evidence_at
from .models import Citation, Claim, Document, Rejection, ReviewError

CLAIM_HEADING = re.compile(
    r"(?m)^[ \t]*[\[【]?청\s*구\s*항\s*(?:제\s*)?(\d+)\s*항?[\]】]?[.．]?[ \t]*$"
)
SECTION_HEADING = re.compile(r"(?m)^[ \t]*[\[【]?청\s*구\s*범\s*위[\]】]?[ \t]*$")
SECTION_END = re.compile(r"(?m)^[ \t]*[\[【]?(?:발명의\s*설명|도\s*면|요\s*약\s*서)[\]】]?[ \t]*$")
LAW = re.compile(
    r"특허법\s*제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?"
)
DEPENDENCY = re.compile(
    r"^\s*((?:청구항\s*)?제?\s*\d+\s*항?[\s\S]{0,140}?)"
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
    ocr_section = None
    ocr_end = None
    if section is None and document.metadata.get("ocr_used"):
        # Tesseract can misread italic colored section titles. Match heading
        # structure only; NEVER replace characters in Document.text/evidence.
        def distance(left, right):
            a = unicodedata.normalize("NFD", re.sub(r"\s", "", left))
            b = unicodedata.normalize("NFD", right)
            row = list(range(len(b) + 1))
            for i, x in enumerate(a, 1):
                new = [i]
                for j, y in enumerate(b, 1):
                    new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
                row = new
            return row[-1]

        lines = list(re.finditer(r"(?m)^[가-힣 ]{4,12}$", document.text))
        for line in lines:
            next_heading = CLAIM_HEADING.search(document.text, line.end(), line.end() + 30)
            if distance(line[0], "청구범위") <= 4 and next_heading and next_heading[1] == "1":
                ends = [
                    m
                    for m in lines
                    if m.start() > next_heading.end() + 100
                    and re.sub(r"\s", "", m[0]).startswith("발명의")
                    and distance(m[0], "발명의설명") <= 3
                ]
                if ends:
                    ocr_section, ocr_end = line.end(), ends[0].start()
                    document.metadata.setdefault("warnings", []).append(
                        "OCR 제목의 자모 유사도와 청구항/설명 경계로 청구범위를 탐지했습니다. 원문 대조가 필요합니다."
                    )
                    break
    if section is None and ocr_section is None:
        candidates = list(CLAIM_HEADING.finditer(document.text))
        # A missing title is accepted only with multiple consecutive claims and
        # actual dependent-claim prose, not a numbered list in the description.
        start = next(
            (
                m.start()
                for i, m in enumerate(candidates[:-1])
                if int(m[1]) == 1
                and m.start() >= len(document.text) * 0.45
                and int(candidates[i + 1][1]) == 2
                and DEPENDENCY.search(document.text[candidates[i + 1].end() :].lstrip())
            ),
            None,
        )
        if start is None:
            raise ReviewError("한국어 청구범위 제목 또는 연속된 청구항 구간을 찾지 못했습니다.")
        document.metadata["claim_detection"] = "consecutive_fallback"
    else:
        start = section.end() if section else ocr_section
        document.metadata["claim_detection"] = "heading" if section else "ocr_heading_candidate"
    end_match = SECTION_END.search(document.text, start)
    section_end = (
        ocr_end if ocr_end is not None else end_match.start() if end_match else len(document.text)
    )
    headings = list(CLAIM_HEADING.finditer(document.text, start, section_end))
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
                dependency_type=(
                    "alternative"
                    if dependency and re.search(r"또는|어느|어떤", dependency[0])
                    else "multiple"
                    if dependency and len(claim_numbers(dependency[1])) > 1
                    else "single"
                    if dependency
                    else "independent"
                ),
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


def extract_office_action(document: Document) -> tuple[list[Rejection], list[Citation]]:
    from .oa import extract_office_action as extract

    return extract(document)
