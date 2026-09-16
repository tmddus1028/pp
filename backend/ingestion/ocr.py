"""Local OCR boundary. Native rendering runs in an isolated, hidden process.

This avoids PyMuPDF's unsupported use from concurrent FastAPI threads, and
keeps pytesseract's executable setting private to each document request.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from backend.config import Settings
from backend.errors import OCRDependencyError, OCRProcessingError
from backend.schemas import OCRWord


class OCRResult(BaseModel):
    texts: dict[str, str]
    blank_pages: list[int]
    renderer: Literal["pymupdf", "pdfium"]
    warnings: list[str] = Field(default_factory=list)
    words: dict[int, list[OCRWord]] = Field(default_factory=dict)


def resolve_tesseract(configured: str = "") -> str:
    if configured:
        resolved = shutil.which(configured) or (configured if Path(configured).is_file() else None)
        if not resolved:
            raise OCRDependencyError(
                "TESSERACT_CMD 경로에서 Tesseract OCR을 찾을 수 없습니다. .env의 실행 파일 경로를 확인하세요."
            )
        return str(Path(resolved).resolve())
    found = shutil.which("tesseract")
    if found:
        return found
    if os.name == "nt":
        for root, suffix in [
            ("LOCALAPPDATA", "Programs/Tesseract-OCR"),
            ("LOCALAPPDATA", "Tesseract-OCR"),
            ("ProgramFiles", "Tesseract-OCR"),
        ]:
            if os.environ.get(root):
                path = Path(os.environ[root]) / suffix / "tesseract.exe"
                if path.is_file():
                    return str(path)
    raise OCRDependencyError(
        "스캔 PDF 처리에 필요한 Tesseract OCR이 설치되어 있지 않습니다. Tesseract와 영어(eng) 데이터를 설치하고 .env의 TESSERACT_CMD를 지정하세요."
    )


def ocr_pdf_pages(data: bytes, page_numbers: list[int], settings: Settings) -> dict:
    """Recognize only the requested 1-based pages. No API/LLM calls or text repair."""
    command = resolve_tesseract(settings.tesseract_cmd)
    with TemporaryDirectory(prefix="patent-review-ocr-") as temporary:
        path = Path(temporary) / "input.pdf"
        path.write_bytes(data)
        request = {
            "path": str(path),
            "pages": page_numbers,
            "command": command,
            "dpi": settings.ocr_dpi,
            "timeout": settings.ocr_timeout_seconds,
            "max_pixels": settings.ocr_max_pixels,
            "renderer": settings.ocr_renderer,
        }
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "backend.ingestion.ocr_worker"],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=Path(__file__).resolve().parents[2],
                timeout=len(page_numbers) * (settings.ocr_timeout_seconds * 2 + 30) + 30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise OCRProcessingError(
                "PDF OCR 작업 시간이 초과되었습니다. 페이지를 나누거나 OCR_TIMEOUT_SECONDS를 확인하세요."
            ) from exc
        except OSError as exc:
            raise OCRDependencyError(
                "로컬 OCR 프로세스를 시작할 수 없습니다. Python 및 실행 권한을 확인하세요."
            ) from exc
    try:
        response = json.loads(completed.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        raise OCRProcessingError(
            "OCR 프로세스가 정상 결과 없이 종료되었습니다. PDF 손상 또는 로컬 렌더러 실행 상태를 확인하세요."
        ) from exc
    if not isinstance(response, dict):
        raise OCRProcessingError(
            "OCR 프로세스의 응답 형식이 올바르지 않습니다. 분석을 중단했습니다."
        )
    if response.get("error"):
        error_class = (
            OCRDependencyError if response.get("code") == "dependency" else OCRProcessingError
        )
        raise error_class(response["error"])
    if completed.returncode != 0 or set(response.get("texts", {})) != {
        str(n) for n in page_numbers
    }:
        raise OCRProcessingError(
            "일부 PDF 페이지의 OCR 결과가 누락되었습니다. 분석을 중단했습니다."
        )
    try:
        validated = OCRResult.model_validate(response)
    except ValidationError as exc:
        raise OCRProcessingError(
            "OCR 프로세스의 페이지 결과 형식이 올바르지 않습니다. 분석을 중단했습니다."
        ) from exc
    if not set(validated.blank_pages).issubset(page_numbers):
        raise OCRProcessingError(
            "OCR 프로세스의 빈 페이지 번호가 입력과 다릅니다. 분석을 중단했습니다."
        )
    return validated.model_dump()
