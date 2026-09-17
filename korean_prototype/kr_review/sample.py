"""Verified, version-specific sample data; never substitute the later grant."""

import hashlib
import json
from pathlib import Path

from kr_review.models import ReviewError

DATA = Path(__file__).resolve().parents[1] / "data" / "kr_1020190000844"


def sample_inputs():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        content = (DATA / item["filename"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise ReviewError(f"샘플 원본 해시가 일치하지 않습니다: {item['filename']}")
    return {
        "patent_data": (DATA / "KR20190025857A.pdf").read_bytes(),
        "patent_filename": "KR20190025857A.pdf",
        "oa_data": (DATA / "office_action_20190409.xml").read_bytes(),
        "oa_filename": "office_action_20190409.xml",
        "references": [
            (item["filename"], (DATA / item["filename"]).read_bytes())
            for item in manifest["files"]
            if item["role"] == "reference"
        ],
    }
