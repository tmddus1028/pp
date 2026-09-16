import re

from backend.errors import DocumentError
from backend.ingestion.adapters import evidence_at
from backend.patent.dependency_parser import parse_dependencies
from backend.schemas import Claim, Document

HEADING = re.compile(
    r"(?:^|\n)(?:what is claimed(?: is)?\s*:|we claim\s*:|i claim\s*:|"
    r"(?:listing of )?claims\s*:?)\s*(?:\n|$)",
    re.I,
)
CLAIM_START = re.compile(r"(?m)^\s*(?:Claim\s+)?(\d{1,4})[.)]\s+(?=\S)", re.I)
END_HEADING = re.compile(
    r"(?im)^\s*(?:abstract|description|specification|drawings|sequence listing)\s*$"
)
# Only used after heading detection fails. Embedded PDF text may join the end
# of one claim and the next number on a single line ("... sapphire. 19. The ...").
# Keep the source untouched so Evidence offsets still address document.text.
FALLBACK_START = re.compile(
    r"(?m)(?:^[ \t]*|(?<=[.;])[ \t]+)(?:Claim[ \t]+)?(\d{1,4})[.)]\s+"
    r"(?=(?:a|an|the)\b)",
    re.I,
)
FALLBACK_END = re.compile(
    r"(?im)^\s*(?:abstract|description|specification|drawings|sequence listing|"
    r"references|bibliography|appendix)\s*$"
)
CLAIM_LANGUAGE = re.compile(
    r"\b(?:compris(?:e[sd]?|ing)|consist(?:s|ing)?\s+(?:of|essentially\s+of)|"
    r"wherein|configured\s+to|having|including)\b",
    re.I,
)
DEPENDENT_LANGUAGE = re.compile(
    r"\b(?:of|according\s+to|as\s+(?:claimed|recited|defined)\s+in)\s+"
    r"(?:(?:any\s+)?one\s+of\s+)?claims?\s+(\d+)\b",
    re.I,
)


def _fallback_claim_section(text: str) -> tuple[int, int] | None:
    """Confirm a terminal claim sequence using several independent signals.

    Deliberately conservative: require Claim 1, at least three consecutive
    claims, claim-like sentences, and a dependency on an earlier claim in the
    sequence. Do not infer missing numbers or accept an ambiguous pair of lists.
    """
    starts = list(FALLBACK_START.finditer(text, len(text) // 2))
    sections = []
    for first in starts:
        if first[1] != "1":
            continue
        stop = FALLBACK_END.search(text, first.end())
        end = stop.start() if stop else len(text)
        matches = list(FALLBACK_START.finditer(text, first.start(), end))
        if len(matches) < 3 or [int(m[1]) for m in matches] != list(range(1, len(matches) + 1)):
            continue
        has_dependency = False
        for index, match in enumerate(matches):
            next_start = matches[index + 1].start() if index + 1 < len(matches) else end
            sentence = text[match.end() : next_start].strip()
            dependency = DEPENDENT_LANGUAGE.search(sentence)
            # Lists of references or numbered implementation steps are not
            # sufficient. Each entry must read as a substantive claim sentence.
            if (
                len(re.findall(r"\b\w+\b", sentence)) < 6
                or not re.search(r"\.(?:\s|$)", sentence)
                or not (CLAIM_LANGUAGE.search(sentence) or dependency)
            ):
                break
            if dependency and 1 <= int(dependency[1]) < int(match[1]):
                has_dependency = True
        else:
            if has_dependency:
                sections.append((first.start(), end))
    return sections[0] if len(sections) == 1 else None


def parse_claims(document: Document) -> list[Claim]:
    headings = list(HEADING.finditer(document.text))
    base = headings[-1].end() if headings else 0
    body = document.text[base:]
    end_heading = END_HEADING.search(body)
    if end_heading:
        body = body[: end_heading.start()]
    matches = list(CLAIM_START.finditer(body))
    if not headings and (not matches or matches[0].start() > 1000):
        section = _fallback_claim_section(document.text)
        if section:
            base, end = section
            body = document.text[base:end]
            matches = list(FALLBACK_START.finditer(body))
    if not headings and matches and matches[0].start() > 1000:
        raise DocumentError(
            "Claims 구간을 식별할 수 없습니다. 청구항 페이지가 스캔인지 확인하고, Claims 제목을 포함한 청구항 텍스트를 입력하세요."
        )
    if not matches:
        raise DocumentError(
            "청구항을 찾지 못했습니다. Claims 제목과 '1. ...' 형식의 청구항 원문을 입력하세요."
        )
    claims, seen = [], set()
    for index, match in enumerate(matches):
        number = int(match[1])
        if number in seen:
            raise DocumentError(
                f"Claim {number} 번호가 중복됩니다. 동일 시점의 청구항 한 세트를 사용하세요."
            )
        seen.add(number)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        raw = body[match.end() : end]
        start = base + match.end() + len(raw) - len(raw.lstrip())
        text = raw.strip()
        if not text:
            raise DocumentError(f"Claim {number}의 내용이 비어 있습니다.")
        canceled = bool(re.fullmatch(r"\(?cancel(?:l)?ed\)?\.?", text, re.I))
        depends_on = [] if canceled else parse_dependencies(text)
        claims.append(
            Claim(
                claim_number=number,
                text=text,
                depends_on=depends_on,
                independent=not depends_on,
                status="canceled" if canceled else "active",
                evidence=evidence_at(document, start, start + len(text)),
            )
        )
    if not any(c.status == "active" for c in claims):
        raise DocumentError("검토 가능한 활성 청구항이 없습니다.")
    return sorted(claims, key=lambda c: c.claim_number)
