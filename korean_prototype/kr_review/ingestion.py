"""Local input handling for the separate Korean prototype.

Evidence always indexes Document.text, never byte offsets or reconstructed PDF pages.
"""

import hashlib
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import Document, Evidence, Page, ReviewError

MAX_BYTES = 20 * 1024 * 1024
MAX_XML_BYTES = 5 * 1024 * 1024
KR_PATENT_NS = "urn:kr:gov:doc:kipo:patent"
NAMESPACES = {
    KR_PATENT_NS: "krpat",
    "urn:kr:gov:doc:kipo:common": "krcom",
    "http://www.wipo.int/standards/XMLSchema/ST96/Common": "com",
    "http://www.wipo.int/standards/XMLSchema/ST96/Patent": "pat",
}


def normalize_text(text: str) -> str:
    """Normalize whitespace only; do not rewrite or summarize original wording."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    return "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n")).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _qualified_name(tag: str) -> str:
    if tag.startswith("{"):
        namespace, name = tag[1:].split("}", 1)
        return f"{NAMESPACES.get(namespace, namespace)}:{name}"
    return tag


def _read_xml(data: bytes, document_id: str, filename: str) -> Document:
    if len(data) > MAX_XML_BYTES:
        raise ReviewError("의견제출통지서 XML은 5 MB 이하로 입력하세요.")
    try:
        source = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ReviewError("현재 한국어 시제품은 UTF-8 XML만 지원합니다.") from exc
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", source, re.IGNORECASE):
        raise ReviewError("DTD 또는 외부 엔터티가 포함된 XML은 지원하지 않습니다.")
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise ReviewError(
            "XML 형식이 올바르지 않습니다. 원본 의견제출통지서를 확인하세요."
        ) from exc
    if root.tag != f"{{{KR_PATENT_NS}}}PatentOpinionSubmission":
        raise ReviewError("KIPRIS 의견제출통지서 PatentOpinionSubmission XML을 입력하세요.")

    # Record both leaf text and enclosing sections. This preserves table row
    # boundaries and source paths without putting XML markup into visible text.
    pieces: list[str] = []
    elements: list[dict] = []
    position = 0

    def add_text(text: str | None) -> tuple[int, int] | None:
        nonlocal position
        value = normalize_text(text or "")
        if not value:
            return None
        if pieces:
            position += 2
        start = position
        pieces.append(value)
        position += len(value)
        return start, position

    def walk(element: ET.Element, path: str, depth: int = 0) -> tuple[int, int] | None:
        if depth > 80:
            raise ReviewError("XML 중첩이 너무 깊습니다. 정상 의견제출통지서를 입력하세요.")
        spans = []
        own = add_text(element.text)
        if own:
            spans.append(own)
        counts: dict[str, int] = {}
        for child in element:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            child_path = f"{path}/{_qualified_name(child.tag)}[{counts[child.tag]}]"
            child_span = walk(child, child_path, depth + 1)
            if child_span:
                spans.append(child_span)
            tail = add_text(child.tail)
            if tail:
                spans.append(tail)
        if not spans:
            return None
        start, end = spans[0][0], spans[-1][1]
        elements.append(
            {"name": _local_name(element.tag), "path": path, "start": start, "end": end}
        )
        return start, end

    walk(root, f"/{_qualified_name(root.tag)}")
    text = "\n\n".join(pieces)

    def field(name: str) -> str:
        item = next((item for item in elements if item["name"] == name), None)
        return text[item["start"] : item["end"]] if item else ""

    application_number = re.sub(r"\D", "", field("ApplicationNumberText"))
    if not re.fullmatch(r"10\d{11}", application_number):
        raise ReviewError("XML에서 한국 특허 출원번호를 확인할 수 없습니다.")
    return Document(
        document_id=document_id,
        filename=filename,
        kind="office_action",
        text=text,
        metadata={
            "format": "xml",
            "application_number": application_number,
            "title": field("InventionTitle"),
            "document_date": field("SendDate") or field("DocumentDate"),
            "send_identifier": field("SendIdentifier"),
            "xml_elements": elements,
            "xml_namespaces": {prefix: uri for uri, prefix in NAMESPACES.items()},
            "ocr_used": False,
            "warnings": ["의견제출통지서는 XML 원문입니다. 원본 PDF 페이지·좌표 정보는 없습니다."],
        },
    )


def _pdfium_text(data: bytes) -> list[str]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    try:
        pages = []
        for index in range(len(document)):
            page = document[index]
            try:
                text_page = page.get_textpage()
                try:
                    pages.append(text_page.get_text_range())
                finally:
                    text_page.close()
            finally:
                page.close()
        return pages
    finally:
        document.close()


def _read_pdf(data: bytes) -> tuple[list[str], str, list[str]]:
    from pypdf import PdfReader

    warnings = []
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise ReviewError("암호로 보호된 PDF입니다. 암호가 해제된 사본을 입력하세요.")
        pages = [page.extract_text() or "" for page in reader.pages]
        parser = "pypdf"
        if not any(page.strip() for page in pages):
            pages = _pdfium_text(data)
            parser = "pdfium"
    except ReviewError:
        raise
    except Exception:
        try:
            pages = _pdfium_text(data)
            parser = "pdfium"
            warnings.append("pypdf에서 읽지 못한 문서를 PDFium 텍스트 추출로 처리했습니다.")
        except Exception as exc:
            raise ReviewError(
                "PDF를 열거나 텍스트를 추출할 수 없습니다. 원본 파일을 확인하세요."
            ) from exc
    if not pages or not any(page.strip() for page in pages):
        raise ReviewError(
            "PDF에 읽을 수 있는 텍스트가 없습니다. 한국어 스캔 OCR은 이 시제품에서 아직 지원하지 "
            "않습니다. 텍스트 PDF 또는 UTF-8 청구항 TXT를 입력하세요."
        )
    sparse_pages = [index for index, text in enumerate(pages, 1) if len(text.strip()) < 20]
    if sparse_pages:
        warnings.append(
            "텍스트가 적은 페이지(도면·빈 페이지·스캔 가능): "
            + ", ".join(map(str, sparse_pages))
            + ". 이 시제품은 한국어 OCR을 실행하지 않습니다."
        )
    return pages, parser, warnings


def _bibliography(text: str) -> dict:
    application = re.search(r"출원번호\s*(10\s*-\s*\d{4}\s*-\s*\d{7})", text)
    publication = re.search(r"공개번호\s*10\s*-\s*(\d{4})\s*-\s*(\d{7})", text)
    registered = re.search(r"등록번호\s*10\s*-\s*(\d{7})", text)
    title = re.search(r"발명의\s*명칭\s*([^\n]+)", text)
    metadata = {
        "application_number": re.sub(r"\D", "", application[1]) if application else "",
        "title": title[1].strip() if title else "",
    }
    if publication:
        metadata["publication_number"] = f"KR{publication[1]}{publication[2]}A"
    elif registered:
        # The bare registered number does not establish a kind code.
        metadata["publication_number"] = f"KR10{registered[1]}"
    return metadata


def read_document(data: bytes, filename: str, kind: str) -> Document:
    if not data:
        raise ReviewError("입력 파일이 비어 있습니다.")
    if len(data) > MAX_BYTES:
        raise ReviewError("각 입력 파일은 20 MB 이하로 입력하세요.")
    suffix = Path(filename).suffix.lower()
    document_id = f"{kind}_{hashlib.sha256(data).hexdigest()[:16]}"
    if suffix == ".xml":
        if kind != "office_action":
            raise ReviewError("XML은 의견제출통지서 입력에만 사용할 수 있습니다.")
        return _read_xml(data, document_id, filename)
    if kind == "office_action":
        raise ReviewError(
            "한국어 시제품의 의견제출통지서는 KIPRIS XML을 입력하세요. OA PDF는 미지원입니다."
        )
    if suffix == ".pdf":
        raw_pages, parser, warnings = _read_pdf(data)
    elif suffix == ".txt":
        try:
            raw_pages = [data.decode("utf-8-sig")]
        except UnicodeDecodeError as exc:
            raise ReviewError("TXT는 UTF-8 인코딩으로 저장해 주세요.") from exc
        parser, warnings = "text", []
    else:
        raise ReviewError("명세서·인용발명은 PDF 또는 UTF-8 TXT로 입력하세요.")
    texts = [normalize_text(text) for text in raw_pages]
    pages = []
    position = 0
    if suffix == ".pdf":
        for number, text in enumerate(texts, 1):
            pages.append(Page(number=number, text=text, start=position, end=position + len(text)))
            position += len(text) + 2
    text = "\n\n".join(texts)
    return Document(
        document_id=document_id,
        filename=filename,
        kind=kind,
        text=text,
        pages=pages,
        metadata={
            **_bibliography(text),
            "format": suffix[1:],
            "parser": parser,
            "ocr_used": False,
            "warnings": warnings,
        },
    )


def evidence_at(document: Document, start: int, end: int, xml_path: str | None = None) -> Evidence:
    if not 0 <= start < end <= len(document.text):
        raise ReviewError("원문 근거의 문자 위치가 올바르지 않습니다.")
    return Evidence(
        document_id=document.document_id,
        text=document.text[start:end],
        start=start,
        end=end,
        page_numbers=[
            page.number for page in document.pages if page.start < end and start < page.end
        ],
        xml_path=xml_path,
    )
