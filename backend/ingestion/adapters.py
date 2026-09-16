import hashlib
import json
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.config import Settings
from backend.errors import DocumentError
from backend.ingestion.margin_cleaner import clean_patent_margins
from backend.ingestion.pdf_reader import extract_pdf
from backend.ingestion.text_cleaner import clean_text
from backend.schemas import Document, Evidence, OCRMetadata, Page

Kind = Literal["patent", "office_action"]


class DocumentAdapter(Protocol):
    def read(self, data: bytes, filename: str, kind: Kind) -> Document: ...


class PageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


class DocumentInput(BaseModel):
    """Portable local/dataset adapter format; never trust client-supplied offsets."""

    model_config = ConfigDict(extra="forbid")
    pages: list[PageInput] = Field(min_length=1)


def from_pages(
    texts: list[str],
    filename: str,
    kind: Kind,
    warnings: list[str] | None = None,
    max_chars: int = 500000,
    metadata: OCRMetadata | None = None,
) -> Document:
    pages, offset = [], 0
    for number, raw in enumerate(texts, 1):
        text = clean_text(raw)
        pages.append(Page(number=number, text=text, start=offset, end=offset + len(text)))
        offset += len(text) + 2
    joined = "\n\n".join(page.text for page in pages)
    if not joined.strip():
        raise DocumentError("문서가 비어 있습니다.")
    if len(joined) > max_chars:
        raise DocumentError(f"문서 텍스트는 {max_chars:,}자를 초과할 수 없습니다.")
    digest = hashlib.sha256(f"{kind}:{joined}".encode()).hexdigest()[:20]
    return Document(
        document_id=digest,
        filename=Path(filename).name,
        kind=kind,
        text=joined,
        pages=pages,
        warnings=warnings or [],
        metadata=metadata or OCRMetadata(),
    )


def from_text(text: str, filename: str, kind: Kind, max_chars: int = 500000) -> Document:
    return from_pages(text.split("\f"), filename, kind, max_chars=max_chars)


def evidence_at(document: Document, start: int, end: int) -> Evidence:
    if not 0 <= start < end <= len(document.text):
        raise ValueError("Evidence must be a nonempty span inside the source document")
    return Evidence(
        document_id=document.document_id,
        text=document.text[start:end],
        start=start,
        end=end,
        page_numbers=[p.number for p in document.pages if p.start < end and p.end > start],
    )


class LocalAdapter:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()

    def read(self, data: bytes, filename: str, kind: Kind) -> Document:
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise DocumentError(f"파일 크기는 {self.settings.max_upload_mb} MB까지 지원합니다.")
        suffix = Path(filename).suffix.lower()
        warnings: list[str] = []
        metadata = OCRMetadata()
        if suffix == ".pdf":
            extracted = extract_pdf(data, self.settings)
            texts, warnings, metadata = extracted.pages, extracted.warnings, extracted.metadata
            if kind == "patent":
                texts = clean_patent_margins(data, texts, metadata)
        elif suffix in {".txt", ".json"}:
            try:
                decoded = data.decode("utf-8-sig")
                texts = (
                    [page.text for page in DocumentInput.model_validate_json(decoded).pages]
                    if suffix == ".json"
                    else decoded.split("\f")
                )
            except (UnicodeDecodeError, ValidationError, json.JSONDecodeError) as exc:
                raise DocumentError(
                    'UTF-8 텍스트 또는 {"pages":[{"text":"..."}]} JSON이 필요합니다.'
                ) from exc
        else:
            raise DocumentError("PDF, TXT, JSON 파일만 지원합니다.")
        return from_pages(
            texts, filename, kind, warnings, self.settings.max_document_chars, metadata
        )
