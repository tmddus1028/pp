"""Install the official Korean Tesseract model only; never overwrite a changed model."""

import hashlib
import json
import os
from pathlib import Path

import httpx


def main():
    directory = Path(
        os.getenv("KR_TESSDATA_DIR")
        or str(
            Path(os.getenv("LOCALAPPDATA", str(Path.home() / ".local/share")))
            / "PatentReview/tessdata"
        )
    )
    directory.mkdir(parents=True, exist_ok=True)
    url = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/kor.traineddata"
    target = directory / "kor.traineddata"
    manifest = Path(__file__).resolve().parents[1] / "data/ocr_model.json"
    record = json.loads(manifest.read_text(encoding="utf8"))
    if target.exists():
        data = target.read_bytes()
    else:
        response = httpx.get(url, follow_redirects=True, timeout=90)
        response.raise_for_status()
        data = response.content
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise RuntimeError("Korean OCR model hash differs; existing model was not overwritten.")
    if not target.exists():
        target.write_bytes(data)
    print("Verified:", target)


if __name__ == "__main__":
    main()
