"""Keep native PDF libraries out of concurrent FastAPI/Streamlit threads."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def open_native_pdf(data: bytes, max_pages: int) -> dict:
    with TemporaryDirectory(prefix="patent-review-open-") as temporary:
        path = Path(temporary) / "input.pdf"
        path.write_bytes(data)
        try:
            process = subprocess.run(
                [sys.executable, "-m", "backend.ingestion.pdf_open_worker"],
                input=json.dumps({"path": str(path), "max_pages": max_pages}),
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=Path(__file__).resolve().parents[2],
                timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                check=False,
            )
            if process.returncode:
                raise ValueError("native worker failed")
            result = json.loads(process.stdout)
            if not isinstance(result, dict) or result.get("engine") not in {
                None,
                "pymupdf",
                "pdfium",
            }:
                raise ValueError("invalid native worker result")
            if result.get("error") != "page_limit" and (
                not isinstance(result.get("pages"), list)
                or not all(isinstance(p, str) for p in result["pages"])
            ):
                raise ValueError("invalid native pages")
            if result.get("error") != "page_limit":
                for field in ("failed", "layouts"):
                    values = result.get(field)
                    if not isinstance(values, list) or any(
                        type(n) is not int or not 1 <= n <= len(result["pages"]) for n in values
                    ):
                        raise ValueError("invalid native page indices")
            if not isinstance(result.get("failures"), list) or not all(
                isinstance(f, str) for f in result["failures"]
            ):
                raise ValueError("invalid native diagnostics")
            return result
        except (OSError, subprocess.TimeoutExpired, ValueError):
            return {
                "engine": None,
                "pages": [],
                "failed": [],
                "layouts": [],
                "failures": ["native PDF worker unavailable"],
            }
