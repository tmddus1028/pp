"""Page-only Korean OCR. No language-model repair and no rewritten source PDF."""

import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import ReviewError


def tesseract_path():
    candidates = [
        os.getenv("KR_TESSERACT_CMD"),
        shutil.which("tesseract"),
        str(Path(os.getenv("LOCALAPPDATA", "")) / "Programs/Tesseract-OCR/tesseract.exe"),
    ]
    return next((p for p in candidates if p and Path(p).is_file()), None)


def recognize_image(image, command, directory):
    """One hidden process, explicit argv (including paths with spaces), TXT+TSV."""
    with tempfile.TemporaryDirectory(prefix="kr-ocr-") as folder:
        source = Path(folder) / "page.png"
        output = Path(folder) / "result"
        image.save(source)
        args = [command, str(source), str(output), "-l", "kor", "--oem", "1", "--psm", "6"]
        if directory:
            args += ["--tessdata-dir", directory]
        args += ["-c", "tessedit_create_txt=1", "-c", "tessedit_create_tsv=1"]
        try:
            process = subprocess.run(
                args,
                capture_output=True,
                timeout=90,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReviewError("한국어 OCR 실행 실패 또는 제한시간 초과입니다.") from exc
        if process.returncode:
            raise ReviewError(
                "한국어 스캔 OCR 실행에 실패했습니다. Tesseract 및 kor 언어 설치를 확인하세요."
            )
        rows = list(
            csv.DictReader(
                output.with_suffix(".tsv").read_text(encoding="utf8").splitlines(), delimiter="\t"
            )
        )
        values = {
            key: [
                row[key] if key == "text" else float(row[key]) if key == "conf" else int(row[key])
                for row in rows
            ]
            for key in ("text", "left", "top", "width", "height", "block_num", "line_num", "conf")
        }
        return output.with_suffix(".txt").read_text(encoding="utf8"), values


def recognize_pages(data, texts):
    import pypdfium2 as pdfium
    from PIL import ImageStat

    sparse = [i for i, text in enumerate(texts) if len(text.strip()) < 30]
    metadata = {"ocr_used": False, "ocr_pages": [], "ocr_raw_text": {}, "ocr_words": {}}
    warnings = []
    if not sparse:
        return texts, metadata, warnings
    command = tesseract_path()
    if not command:
        raise ReviewError(
            "한국어 스캔 OCR에 필요한 Tesseract가 없습니다. KR_TESSERACT_CMD를 확인하세요."
        )
    default_data = (
        Path(os.getenv("LOCALAPPDATA", str(Path.home() / ".local/share"))) / "PatentReview/tessdata"
    )
    directory = os.getenv("KR_TESSDATA_DIR") or (
        str(default_data) if default_data.is_dir() else None
    )
    document = pdfium.PdfDocument(data)
    try:
        for index in sparse:
            page = document[index]
            bitmap = None
            try:
                scale = min(300 / 72, (40_000_000 / (page.get_width() * page.get_height())) ** 0.5)
                bitmap = page.render(scale=scale)
                image = bitmap.to_pil().convert("RGB")
                if ImageStat.Stat(image.convert("L")).mean[0] > 254.95:
                    warnings.append(f"{index + 1}쪽: 빈 페이지로 OCR 텍스트가 없습니다.")
                    continue
                raw, values = recognize_image(image, command, directory)
                words = []
                for n, value in enumerate(values["text"]):
                    if not value.strip():
                        continue
                    x, y, w, h = (values[k][n] for k in ("left", "top", "width", "height"))
                    if w <= 0 or h <= 0:
                        continue
                    words.append(
                        {
                            "text": value,
                            "bbox": [
                                x / image.width,
                                y / image.height,
                                min(1, (x + w) / image.width),
                                min(1, (y + h) / image.height),
                            ],
                            "block": values["block_num"][n],
                            "line": values["line_num"][n],
                            "confidence": float(values["conf"][n]),
                        }
                    )
                metadata["ocr_pages"].append(index + 1)
                metadata["ocr_raw_text"][index + 1] = raw
                metadata["ocr_words"][index + 1] = words
                texts[index] = raw
                average = sum(w["confidence"] for w in words) / max(1, len(words))
                warnings.append(
                    f"{index + 1}쪽: 한국어 OCR 사용, 평균 단어 신뢰도 {average:.1f}/100. 원문 대조가 필요합니다."
                )
            finally:
                if bitmap is not None:
                    bitmap.close()
                page.close()
    except RuntimeError as exc:
        raise ReviewError(
            "한국어 OCR 실행에 실패했습니다. 원본과 Tesseract 설정을 확인하세요."
        ) from exc
    finally:
        document.close()
    if metadata["ocr_pages"]:
        metadata.update(
            ocr_used=True,
            ocr_engine="tesseract",
            ocr_renderer="pdfium",
            ocr_dpi=300,
            ocr_language="kor",
        )
    return texts, metadata, warnings
