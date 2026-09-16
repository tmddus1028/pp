import re
from dataclasses import dataclass

from backend.office_action.claim_status import STATUS_STATEMENT
from backend.patent.dependency_parser import NUMBER_LIST
from backend.schemas import Document

# Restrict the predicate to avoid treating citations to prior-art claims as direct rejections.
ACTION_START = re.compile(
    r"\bclaims?(?:\(s\))?\s+(?P<numbers>" + NUMBER_LIST + r")"
    r"\s*(?:,\s*)?(?:(?:is\s*/\s*are(?=\s+rejected\s+under\b)|is|are|remain|remains|stand|stands)\s+)?"
    r"(?:(?:hereby|provisionally|also|further)\s+)*(?P<action>rejected|objected\s+to)\b",
    re.I,
)
SECTION_HEADING = re.compile(
    r"(?im)^\s*(?:claim\s+rejections?[^\r\n]*|claim\s+objections?[^\r\n]*|response\s+to\s+arguments|"
    r"conclusion|allowable\s+subject\s+matter|reasons\s+for\s+allowance|"
    r"notice\s+of\s+allowability|notice\s+of\s+references\s+cited|double\s+patenting)\s*$"
)


@dataclass(frozen=True)
class Chunk:
    text: str
    start: int
    end: int


def in_allowance_section(document: Document, offset: int) -> bool:
    headings = list(SECTION_HEADING.finditer(document.text, 0, offset))
    return bool(
        headings
        and re.match(
            r"\s*(?:allowable\s+subject\s+matter|reasons\s+for\s+allowance|notice\s+of\s+allowability)",
            headings[-1][0],
            re.I,
        )
    )


def chunk_office_action(document: Document, max_chars: int = 14000) -> list[Chunk]:
    """Keep rejection boundaries, including cross-page text; split long sections with overlap."""
    boundaries = {0, len(document.text)}
    boundaries.update(m.start() for m in ACTION_START.finditer(document.text))
    boundaries.update(m.start() for m in SECTION_HEADING.finditer(document.text))
    # Allowed/canceled/pending statements end the preceding rejection's evidence;
    # they are not new rejections. Handle word-per-line PDF extraction as well.
    boundaries.update(m.start() for m in STATUS_STATEMENT.finditer(document.text))
    bounds = sorted(boundaries)
    chunks = []
    overlap = min(1000, max_chars // 4)
    for begin, end in zip(bounds, bounds[1:]):
        while begin < end:
            stop = min(end, begin + max_chars)
            if document.text[begin:stop].strip():
                chunks.append(Chunk(document.text[begin:stop], begin, stop))
            if stop == end:
                break
            begin = stop - overlap
    return chunks
