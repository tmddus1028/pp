"""Conservative patent margin removal, before normalization and Evidence offsets.

Never replace publication numbers throughout prose. A text fragment must be in
the physical margin, isolated from body text, and either a recognizable running
patent header or repeated in the same margin on another page. Uncertain layouts
pass through. OCR output without coordinates uses only contiguous edge headers.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader, mult
from pypdf.errors import PdfReadError

from backend.schemas import OCRMetadata, RemovedMargin

PUBLICATION = re.compile(r"US\s*\d{4}\s*/?\s*\d{7}\s*A\d", re.I)
DATE = re.compile(
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\.?\s+\d{1,2},?\s+\d{4}",
    re.I,
)
TITLE = re.compile(r"Patent Application Publication", re.I)
NUMBER = re.compile(r"(?:Page\s+)?\d{1,4}(?:\s+of\s+\d{1,4})?", re.I)


def _key(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _kind(text: str) -> str | None:
    if NUMBER.fullmatch(text):
        return "page_number"
    rest = text
    for pattern in (PUBLICATION, DATE, TITLE):
        rest = pattern.sub("", rest)
    rest = re.sub(r"Sheet\s+\d+\s+of\s+\d+", "", rest, flags=re.I)
    if not rest.strip() and PUBLICATION.search(text):
        return "publication_header"
    if TITLE.fullmatch(text):
        return "publication_title"
    if DATE.fullmatch(text):
        return "publication_date"
    return None


@dataclass
class Fragment:
    text: str
    y: float
    position: str | None
    edge_distance: float


def _fragments(page, expected: str) -> list[Fragment]:
    if page.rotation:
        return []  # No guesses for rotated pages or mismatching extraction passes.
    box = page.cropbox
    height = float(box.height)
    fragments = []

    def visit(text, cm, tm, font, size):
        matrix = mult(tm, cm)
        y = matrix[5] - float(box.bottom)
        position = None
        if not matrix[1] and not matrix[2] and 0 <= y <= height:
            if y >= height - min(96, height * 0.12):
                position = "header"
            elif y <= min(64, height * 0.08):
                position = "footer"
        fragments.append(Fragment(text, y, position, min(y, height - y)))

    try:
        page.extract_text(visitor_text=visit)
    except (PdfReadError, RuntimeError, ValueError, KeyError, OSError):
        return []
    # A tagged duplicate OCR layer may already have been removed by pdf_reader.
    # Do not map offsets from a different extraction to the cleaned page.
    return fragments if "".join(f.text for f in fragments) == expected else []


def _candidate(fragment: Fragment) -> bool:
    text = fragment.text.strip()
    if not fragment.position or not text or len(text.splitlines()) != 1 or len(text) > 100:
        return False
    if _kind(text):
        return True
    if fragment.edge_distance > 32:
        return False  # Arbitrary repeated text needs a much narrower outer margin.
    # Keep numbered claims, section headings and repeated prose sentences.
    return not (
        re.match(r"(?:\d+[.)]|claims?\b|description\b|what is claimed\b)", text, re.I)
        or text.endswith((".", ";", ":", "-", ","))
        or len(text.split()) > 10
    )


def clean_patent_margins(data: bytes, texts: list[str], metadata: OCRMetadata) -> list[str]:
    try:
        pdf = PdfReader(BytesIO(data))
        positioned = [
            _fragments(page, text) if n not in metadata.ocr_pages else []
            for n, (page, text) in enumerate(zip(pdf.pages, texts), 1)
        ]
    except (PdfReadError, RuntimeError, ValueError, KeyError, OSError, TypeError, IndexError):
        # Optional cleaning must not reject a PDF already opened by another engine.
        positioned = [[] for _ in texts]
    occurrences = defaultdict(set)
    for number, fragments in enumerate(positioned, 1):
        for fragment in fragments:
            if _candidate(fragment):
                key = (
                    "#page"
                    if _kind(fragment.text.strip()) == "page_number"
                    else _key(fragment.text)
                )
                occurrences[(fragment.position, key)].add(number)
    cleaned = list(texts)
    for number, fragments in enumerate(positioned, 1):
        removable = []
        patent_headers = {
            f.position
            for f in fragments
            if _candidate(f) and _kind(f.text.strip()) == "publication_header"
        }
        for fragment in fragments:
            if not _candidate(fragment):
                continue
            kind = _kind(fragment.text.strip())
            key = "#page" if kind == "page_number" else _key(fragment.text)
            recognized_block = kind is not None and fragment.position in patent_headers
            if not recognized_block and len(occurrences[(fragment.position, key)]) < 2:
                continue
            removable.append(fragment)
        # Candidate headers must be separated from retained body by at least 16pt.
        # This protects running prose even if it starts inside the margin band.
        body = [f for f in fragments if f.text.strip() and f not in removable]
        accepted = []
        for fragment in removable:
            inward = [
                abs(f.y - fragment.y)
                for f in body
                if (f.y < fragment.y if fragment.position == "header" else f.y > fragment.y)
            ]
            if not inward or min(inward) < 16:
                continue
            accepted.append(fragment)
            metadata.removed_margins.append(
                RemovedMargin(
                    page_number=number,
                    text=fragment.text,
                    position=fragment.position,
                    reason="position:" + (_kind(fragment.text.strip()) or "repeated_margin"),
                )
            )
        if fragments:
            cleaned[number - 1] = "".join(f.text for f in fragments if f not in accepted)
    _clean_ocr_edges(cleaned, metadata)
    return cleaned


def _clean_ocr_edges(texts: list[str], metadata: OCRMetadata) -> None:
    """No geometry: require a repeated publication header in a contiguous edge block."""
    blocks = []
    repeated = defaultdict(set)
    for number in metadata.ocr_pages:
        lines = texts[number - 1].splitlines(keepends=True)
        for position, indices in (
            ("header", range(len(lines))),
            ("footer", range(len(lines) - 1, -1, -1)),
        ):
            block = []
            for index in indices:
                value = lines[index].strip()
                if value and not _kind(value):
                    break
                block.append(index)
            headers = [
                _key(lines[i]) for i in block if _kind(lines[i].strip()) == "publication_header"
            ]
            for header in headers:
                repeated[(position, header)].add(number)
            blocks.append((number, position, lines, block, headers))
    removed = defaultdict(set)
    for number, position, lines, block, headers in blocks:
        if not any(len(repeated[(position, header)]) >= 2 for header in headers):
            continue
        for index in block:
            if index in removed[number] or not lines[index].strip():
                continue
            removed[number].add(index)
            metadata.removed_margins.append(
                RemovedMargin(
                    page_number=number,
                    text=lines[index],
                    position=position,
                    reason="ocr_edge:repeated_publication_header",
                )
            )
    for number, indices in removed.items():
        texts[number - 1] = "".join(
            line
            for i, line in enumerate(texts[number - 1].splitlines(keepends=True))
            if i not in indices
        )
