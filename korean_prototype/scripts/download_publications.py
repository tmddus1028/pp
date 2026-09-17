"""Restore the four pinned public PDFs, without modifying an existing file."""

import hashlib
import json
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parents[1] / "data" / "kr_1020190000844"


def main():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = DATA / item["filename"]
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != item["sha256"]:
                raise RuntimeError(f"Existing file hash mismatch; not overwritten: {path.name}")
            print(f"Verified: {path.name}")
            continue
        if item["role"] == "office_action":
            raise RuntimeError("Restore the user-provided OA XML from the original KIPRIS sample.")
        response = httpx.get(item["source"], follow_redirects=True, timeout=60)
        response.raise_for_status()
        content = response.content
        if not content.startswith(b"%PDF-"):
            raise RuntimeError(f"Not a PDF: {path.name}")
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            raise RuntimeError(f"Download hash mismatch: {path.name}")
        path.write_bytes(content)
        print(f"Downloaded: {path.name}")


if __name__ == "__main__":
    main()
