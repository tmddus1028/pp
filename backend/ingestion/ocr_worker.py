"""One-document local OCR worker, launched only for sparse PDF pages."""

import json
import math
import sys

from backend.errors import OCRDependencyError, OCRProcessingError


def open_renderer(path: str, preference: str):
    warnings = []
    if preference != "pdfium":
        try:
            import pymupdf
        except (ImportError, OSError) as exc:
            if preference == "pymupdf":
                raise OCRDependencyError(
                    "PyMuPDF를 불러올 수 없습니다. uv sync 및 Windows Visual C++ x64 런타임/DLL 실행 정책을 확인하세요."
                ) from exc
            warnings.append(
                "PyMuPDF를 불러올 수 없어 로컬 PDFium으로 페이지를 렌더링했습니다. OCR 엔진은 Tesseract입니다."
            )
        else:
            try:
                return pymupdf.open(path), "pymupdf", warnings
            except Exception as exc:
                if preference == "pymupdf":
                    raise OCRProcessingError("PyMuPDF에서 OCR 대상 PDF를 열지 못했습니다.") from exc
                warnings.append(
                    "PyMuPDF에서 PDF 열기에 실패하여 로컬 PDFium으로 OCR 렌더링을 시도합니다."
                )
    try:
        import pypdfium2
    except (ImportError, OSError) as exc:
        raise OCRDependencyError(
            "PDF OCR 렌더러를 불러올 수 없습니다. uv sync로 PyMuPDF/PDFium을 설치하고 Windows 런타임을 확인하세요."
        ) from exc
    return pypdfium2.PdfDocument(path), "pdfium", warnings


def render_page(document, renderer: str, number: int, dpi: int, max_pixels: int):
    from PIL import Image

    page = document[number - 1]
    try:
        width, height = (
            (page.rect.width, page.rect.height) if renderer == "pymupdf" else page.get_size()
        )
        pixels = math.ceil(width * dpi / 72) * math.ceil(height * dpi / 72)
        if pixels <= 0 or pixels > max_pixels:
            raise OCRProcessingError(
                f"PDF {number}페이지가 OCR 이미지 크기 제한을 초과합니다. OCR_DPI를 낮추거나 페이지 크기를 확인하세요."
            )
        if renderer == "pymupdf":
            import pymupdf

            pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        bitmap = page.render(scale=dpi / 72)
        try:
            return bitmap.to_pil().convert("RGB")
        finally:
            bitmap.close()
    finally:
        if renderer == "pdfium":
            page.close()


def recognize(request: dict) -> dict:
    try:
        import pytesseract
    except ImportError as exc:
        raise OCRDependencyError(
            "pytesseract/Pillow가 설치되어 있지 않습니다. uv sync를 실행하세요."
        ) from exc
    pytesseract.pytesseract.tesseract_cmd = request["command"]
    try:
        languages = pytesseract.get_languages(config="")
        if "eng" not in languages:
            raise OCRDependencyError(
                "Tesseract 영어 언어 데이터 eng.traineddata가 없습니다. 영어(eng) 데이터를 설치하세요."
            )
    except (pytesseract.TesseractNotFoundError, OSError) as exc:
        raise OCRDependencyError(
            "Tesseract OCR을 실행할 수 없습니다. 설치 상태와 TESSERACT_CMD 경로를 확인하세요."
        ) from exc
    except pytesseract.TesseractError as exc:
        raise OCRDependencyError(
            "Tesseract 언어 데이터를 읽을 수 없습니다. eng.traineddata 설치와 TESSDATA_PREFIX를 확인하세요."
        ) from exc
    document, renderer, warnings = open_renderer(request["path"], request["renderer"])
    texts, blank_pages, words = {}, [], {}
    try:
        for number in request["pages"]:
            try:
                with render_page(
                    document, renderer, number, request["dpi"], request["max_pixels"]
                ) as image:
                    # Only a uniformly white rendered page is treated as blank.
                    if image.convert("L").getextrema()[0] == 255:
                        texts[str(number)] = ""
                        blank_pages.append(number)
                        continue
                    text = pytesseract.image_to_string(
                        image,
                        lang="eng",
                        config=f"--dpi {request['dpi']} --psm 3",
                        timeout=request["timeout"],
                    )
                    # Separate display metadata: keep image_to_string and its raw
                    # output unchanged. Geometry failure must not invent highlights.
                    try:
                        data = pytesseract.image_to_data(
                            image,
                            lang="eng",
                            config=f"--dpi {request['dpi']} --psm 3",
                            output_type=pytesseract.Output.DICT,
                            timeout=request["timeout"],
                        )
                        words[str(number)] = word_boxes(data, image.width, image.height)
                    except (pytesseract.TesseractError, OSError, RuntimeError):
                        warnings.append(
                            f"PDF {number}페이지의 OCR 텍스트는 추출했지만 표시용 좌표 추출에 실패했습니다. 해당 구간은 페이지·원문 근거로 확인하세요."
                        )
                if not any(c.isalnum() for c in text):
                    raise OCRProcessingError(
                        f"PDF {number}페이지에 내용이 있지만 OCR 텍스트를 인식하지 못했습니다. 스캔 품질과 회전을 확인하세요. 부분 결과로 분석하지 않았습니다."
                    )
                texts[str(number)] = text
            except pytesseract.TesseractNotFoundError as exc:
                raise OCRDependencyError(
                    "Tesseract OCR 실행 파일을 찾을 수 없습니다. TESSERACT_CMD를 확인하세요."
                ) from exc
            except pytesseract.TesseractError as exc:
                raise OCRProcessingError(
                    f"PDF {number}페이지에서 Tesseract OCR이 실패했습니다. 영어 데이터와 스캔 파일을 확인하세요."
                ) from exc
            except RuntimeError as exc:
                raise OCRProcessingError(
                    f"PDF {number}페이지의 OCR 시간이 초과되었거나 렌더링에 실패했습니다. 스캔 품질과 OCR_TIMEOUT_SECONDS를 확인하세요."
                ) from exc
    finally:
        document.close()
    return {
        "texts": texts,
        "blank_pages": blank_pages,
        "renderer": renderer,
        "warnings": warnings,
        "words": words,
    }


def word_boxes(data, width, height):
    words = []
    for i, text in enumerate(data["text"]):
        if not text.strip() or data["width"][i] <= 0 or data["height"][i] <= 0:
            continue
        x, y = data["left"][i], data["top"][i]
        words.append(
            {
                "text": text,
                "bbox": [
                    max(0, x / width),
                    max(0, y / height),
                    min(1, (x + data["width"][i]) / width),
                    min(1, (y + data["height"][i]) / height),
                ],
                "block": data["block_num"][i],
                "line": data["line_num"][i],
                "confidence": float(data["conf"][i]),
            }
        )
    return words


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = recognize(json.load(sys.stdin))
    except (OCRDependencyError, OCRProcessingError) as exc:
        print(
            json.dumps(
                {
                    "code": "dependency" if isinstance(exc, OCRDependencyError) else "processing",
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        return 1
    except Exception:
        # Native/PDF exceptions differ across renderers. Do not leak document data.
        print(
            json.dumps(
                {
                    "code": "processing",
                    "error": "텍스트 추출 후 PDF OCR 렌더링에 실패했습니다. PDF 페이지 손상과 로컬 렌더러 실행 상태를 확인하세요. 부분 결과로 분석하지 않았습니다.",
                },
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
