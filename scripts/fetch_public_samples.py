"""Download small public source PDFs explicitly; the app never needs network datasets."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import httpx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1] / "data/raw/uspto"
SOURCES = [
    {
        "filename": "official_112f_sample.pdf",
        "type": "official_hypothetical_training_example",
        "url": "https://www.uspto.gov/sites/default/files/documents/112f_sample_action.pdf",
    },
    {
        "filename": "US20140201856A1.pdf",
        "type": "public_uspto_application_publication_mirror",
        "url": "https://patentimages.storage.googleapis.com/df/00/7c/b59446f4f14dcc/US20140201856A1.pdf",
    },
]


def fetch(source):
    response = httpx.get(source["url"], follow_redirects=True, timeout=45)
    response.raise_for_status()
    data = response.content
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("Sample exceeds 20 MB")
    pdf = PdfReader(BytesIO(data))
    target = ROOT / source["filename"]
    target.write_bytes(data)
    print(f"Saved {target.name}: {len(pdf.pages)} pages")
    return {**source, "sha256": hashlib.sha256(data).hexdigest(), "pages": len(pdf.pages)}


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        manifest = list(pool.map(fetch, SOURCES))
    existing = ROOT / "sources.json"
    if existing.exists():
        downloaded = {item["filename"] for item in manifest}
        manifest.extend(
            item
            for item in json.loads(existing.read_text(encoding="utf-8"))
            if item["filename"] not in downloaded
        )
    (ROOT / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
