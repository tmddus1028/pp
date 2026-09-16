import re
from copy import copy
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from pypdf.generic import ContentStream, NameObject

from backend.config import Settings
from backend.errors import DocumentError, OCRProcessingError
from backend.ingestion.ocr import ocr_pdf_pages
from backend.ingestion.pdf_open import open_native_pdf
from backend.schemas import OCRMetadata


def _without_duplicate_ocr(page) -> tuple[str, bool]:
    """Handle a tagged OCR pass over a second, substantially identical OCR pass.

    Keep the original PDF untouched. Never deduplicate arbitrary repeated prose:
    require an explicit OCRPageInfo marked-content block, invisible text in both
    passes, and a near-identical ordered word sequence. Other layouts pass through.
    """
    original = page.extract_text() or ""
    contents = page.get_contents()
    if contents is None or b"/OCRPageInfo" not in contents.get_data():
        return original, False
    stream = ContentStream(contents, page.pdf)
    tagged, remaining = [], []
    depth = 0
    for operands, operator in stream.operations:
        if operator in {b"BDC", b"BMC"}:
            if depth or (operands and operands[0] == "/OCRPageInfo"):
                depth += 1
        (tagged if depth else remaining).append((operands, operator))
        if operator == b"EMC" and depth:
            depth -= 1
    if depth or not tagged or not remaining:
        return original, False
    # A visible text layer may contain unique material. Do not remove it.
    for operations in (tagged, remaining):
        modes = [int(args[0]) for args, op in operations if op == b"Tr"]
        if not modes or any(mode != 3 for mode in modes):
            return original, False

    def extract(operations):
        candidate = copy(page)
        filtered = ContentStream(None, page.pdf)
        filtered.operations = operations
        candidate[NameObject("/Contents")] = filtered
        return candidate.extract_text() or ""

    first, second = extract(tagged), extract(remaining)
    left, right = (re.findall(r"\w+", text.casefold()) for text in (first, second))
    if min(len(left), len(right)) < 30:
        return original, False
    if SequenceMatcher(None, left, right, autojunk=False).ratio() < 0.90:
        return original, False
    return second, True


@dataclass
class PDFExtraction:
    pages: list[str]
    warnings: list[str]
    metadata: OCRMetadata = field(default_factory=OCRMetadata)


def _structurally_blank(page) -> bool:
    """Skip truly empty pages without requiring native libraries or Tesseract."""
    if page.get("/Annots"):
        return False
    content = page.get_contents()
    if content is None:
        return True
    painting = {
        b"Do",
        b"INLINE IMAGE",
        b"sh",
        b"S",
        b"s",
        b"f",
        b"F",
        b"f*",
        b"B",
        b"B*",
        b"b",
        b"b*",
        b"Tj",
        b"TJ",
        b"'",
        b'"',
    }
    return not any(op in painting for _, op in ContentStream(content, page.pdf).operations)


def _inline_claim_heading(text: str) -> bool:
    return bool(
        re.search(r"what is claimed is\s*:", text, re.I)
        and not re.search(r"(?im)^\s*what is claimed is\s*:\s*$", text)
    )


def extract_pdf(data: bytes, settings: Settings) -> PDFExtraction:
    """Prefer embedded text; OCR sparse pages only, retaining original positions."""
    try:
        native = open_native_pdf(data, settings.max_pdf_pages)
        if native.get("error") == "page_limit":
            raise DocumentError(f"PDF는 1~{settings.max_pdf_pages}페이지를 지원합니다.")
        warnings = []
        if native["failures"]:
            warnings.append("PDF parser fallback: " + "; ".join(native["failures"]))
        # Opening validity follows PyMuPDF -> PDFium -> pypdf. Keep the existing
        # embedded-text extractor when compatible, including tagged OCR dedup.
        legacy_pages = None
        try:
            pdf = PdfReader(BytesIO(data))
            if pdf.is_encrypted:
                raise DocumentError("암호화된 PDF입니다. 암호를 제거한 사본을 사용하세요.")
            legacy_pages = list(pdf.pages)
        except DocumentError:
            raise
        except (
            PdfReadError,
            RuntimeError,
            ValueError,
            KeyError,
            OSError,
            TypeError,
            IndexError,
        ) as exc:
            warnings.append(
                f"pypdf 페이지 열기 실패 ({type(exc).__name__}); 사용 가능한 PDF parser로 계속합니다."
            )
            if not native["engine"]:
                raise DocumentError(
                    "PDF를 열 수 없습니다. PyMuPDF, PDFium, pypdf에서 모두 열기에 실패했습니다. 파일 손상 여부를 확인하세요."
                ) from exc
        count = len(native["pages"]) if native["engine"] else len(legacy_pages or [])
        if not 0 < count <= settings.max_pdf_pages:
            raise DocumentError(f"PDF는 1~{settings.max_pdf_pages}페이지를 지원합니다.")
        if legacy_pages is not None and len(legacy_pages) != count:
            warnings.append(
                "pypdf 페이지 수가 열린 PDF와 달라 해당 텍스트 추출을 사용하지 않았습니다."
            )
            legacy_pages = None
        metadata = OCRMetadata(pdf_parser=native["engine"] or "pypdf")
        parser_warnings, warnings = warnings, []
        pages = []
        candidates = []
        native_claim_order = False
        for number in range(1, count + 1):
            page = legacy_pages[number - 1] if legacy_pages is not None else None
            extraction_failed = False
            deduplicated = False
            try:
                if number in native.get("layouts", []):
                    text = native["pages"][number - 1]
                    metadata.pdf_layout_pages.append(number)
                    metadata.pdf_text_extractors[number] = native["engine"] + ":claim_columns"
                elif page is not None:
                    text, deduplicated = _without_duplicate_ocr(page)
                    metadata.pdf_text_extractors[number] = "pypdf"
                    if native["engine"] and not deduplicated:
                        alternate = native["pages"][number - 1]
                        if (
                            alternate.strip()
                            and not _inline_claim_heading(alternate)
                            and (native_claim_order or _inline_claim_heading(text))
                        ):
                            # Some MuPDF versions already return correct Claim lines.
                            # Do not replace that valid order with interleaved legacy text.
                            text, native_claim_order = alternate, True
                            metadata.pdf_layout_pages.append(number)
                            metadata.pdf_text_extractors[number] = native["engine"] + ":claim_order"
                else:
                    text = native["pages"][number - 1]
                    extraction_failed = number in native["failed"]
                    metadata.pdf_text_extractors[number] = native["engine"]
                    if extraction_failed:
                        raise ValueError("Native page text extraction failed")
            except (PdfReadError, RuntimeError, ValueError, KeyError, OSError):
                text, deduplicated, extraction_failed = "", False, True
                warnings.append(
                    f"PDF {number}페이지의 텍스트 레이어 추출에 실패해 OCR을 시도했습니다."
                )
            pages.append(text)
            if deduplicated:
                warnings.append(
                    f"PDF {number}페이지의 중복 OCR 레이어를 감지해 한 텍스트 레이어를 사용했습니다. "
                    "OCR 철자와 숫자는 원본 PDF에서 확인하세요."
                )
            if sum(c.isalnum() for c in text) < settings.ocr_min_text_chars:
                blank = False
                if page is not None and not extraction_failed and not text.strip():
                    try:
                        blank = _structurally_blank(page)
                    except (PdfReadError, RuntimeError, ValueError, KeyError, OSError, TypeError):
                        pass  # Let the renderer determine whether this sparse page is empty.
                if blank:
                    warnings.append(
                        f"PDF {number}페이지가 비어 있어 OCR을 생략했습니다. 페이지 번호는 유지합니다."
                    )
                else:
                    candidates.append(number)
        if metadata.pdf_layout_pages:
            warnings.append(
                f"PDF 청구항의 섞인 줄/단 순서를 원문 글자 좌표로 정렬했습니다. 페이지: {metadata.pdf_layout_pages}"
            )
        if candidates:
            result = ocr_pdf_pages(data, candidates, settings)
            raw = {}
            for number in candidates:
                text = result["texts"][str(number)]
                if number in result["blank_pages"]:
                    # A renderer-confirmed white page is not an OCR success.
                    warnings.append(
                        f"PDF {number}페이지가 빈 이미지로 확인되어 OCR을 생략했습니다."
                    )
                    continue
                if not any(c.isalnum() for c in text):
                    raise OCRProcessingError(
                        f"PDF {number}페이지의 텍스트 추출과 OCR이 모두 실패했습니다. 분석을 중단했습니다."
                    )
                pages[number - 1] = text
                raw[number] = text
                if sum(c.isalnum() for c in text) < settings.ocr_min_text_chars:
                    warnings.append(f"PDF {number}페이지의 OCR 결과가 짧습니다. 원본과 대조하세요.")
            warnings.extend(result["warnings"])
            if raw:
                metadata = OCRMetadata.model_validate(
                    metadata.model_dump()
                    | dict(
                        ocr_used=True,
                        ocr_pages=list(raw),
                        ocr_engine="tesseract",
                        ocr_renderer=result["renderer"],
                        ocr_dpi=settings.ocr_dpi,
                        ocr_language="eng",
                        ocr_raw_text=raw,
                        ocr_words=result.get("words", {}),
                    )
                )
                warnings.append(
                    f"스캔 PDF가 감지되어 로컬 OCR을 수행했습니다. ({len(raw)}페이지, PDF 페이지: {', '.join(map(str, raw))}) OCR 문구·번호는 원본과 대조하세요."
                )
        if not any(text.strip() for text in pages):
            raise DocumentError(
                "추출 가능한 텍스트가 없습니다. 빈 PDF 또는 OCR로 읽을 내용이 없는 문서인지 확인하세요."
            )
        warnings.extend(parser_warnings)
        warnings.append(
            "PDF 텍스트 추출과 OCR의 읽기 순서를 사용합니다. 다단 편집/표/줄 번호가 있는 원문은 추출 순서를 확인하세요."
            if metadata.ocr_used
            else "PDF는 내장 텍스트의 읽기 순서를 사용합니다. 다단 편집/표/줄 번호가 있는 원문은 추출 순서를 확인하세요."
        )
        return PDFExtraction(pages, warnings, metadata)
    except DocumentError:
        raise
    except (PdfReadError, RuntimeError, ValueError, KeyError, OSError) as exc:
        raise DocumentError("PDF를 열 수 없습니다. 파일 손상 여부를 확인하세요.") from exc


def read_pdf(data: bytes, max_pages: int = 150) -> tuple[list[str], list[str]]:
    """Compatibility wrapper for callers using the original two-value return."""
    result = extract_pdf(data, Settings(max_pdf_pages=max_pages))
    return result.pages, result.warnings
