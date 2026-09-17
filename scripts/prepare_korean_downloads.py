"""Download public Korean sources and test them without changing application code."""

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/downloads/kr_review_package"
SOURCE = ROOT / "korean_prototype/data/kr_1020190000844"
PUBLICATIONS = {
    "1020190000844": "KR20190025857A",
    "1020190000874": "KR20190003855A",
    "1020190000902": "KR20190004821A",
    "1020190000903": "KR20190019097A",
    "1020190000948": "KR20190005244A",
}
ARCHIVES = {
    "kipris_oa_sample.zip": "https://plus.kipris.or.kr/kipris/kpp/FileDown.do?atchFileId=AFI_0000000000000853&fileSn=0&fileFieldName=dowFile0",
    "kipris_patent_oa_2015.zip": "https://plus.kipris.or.kr/kipris/kpp/FileDown.do?atchFileId=AFI_0000000000000853&fileSn=2&fileFieldName=dowFile2",
}


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    published = OUT / "publications"
    published.mkdir(exist_ok=True)
    pinned = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    downloads = []
    urls = {
        entry["filename"][:-4]: entry["source"]
        for entry in pinned["files"]
        if entry["filename"].endswith(".pdf")
    }
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        official = []
        for name, url in ARCHIVES.items():
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                assert archive.testzip() is None
                destination = OUT / name
                if destination.exists() and destination.read_bytes() != content:
                    raise RuntimeError(f"Refusing to replace changed archive: {name}")
                destination.write_bytes(content)
                official.append(
                    {
                        "filename": name,
                        "source": url,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "members": [
                            {"name": i.filename, "bytes": i.file_size} for i in archive.infolist()
                        ],
                    }
                )
                if name == "kipris_oa_sample.zip":
                    base = (OUT / "official_samples").resolve()
                    for member in archive.infolist():
                        if member.is_dir():
                            continue
                        target = (base / member.filename).resolve()
                        if not target.is_relative_to(base):
                            raise RuntimeError("Archive path escapes destination")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        data = archive.read(member)
                        if target.exists() and target.read_bytes() != data:
                            raise RuntimeError(f"Refusing to replace changed original: {target}")
                        target.write_bytes(data)
        save_json(OUT / "official_downloads.json", official)
        for publication in dict.fromkeys([*urls, *PUBLICATIONS.values()]):
            source_page = f"https://patents.google.com/patent/{publication}/ko"
            url = urls.get(publication)
            if not url:
                response = client.get(source_page)
                response.raise_for_status()
                (published / (publication + ".html")).write_text(response.text, encoding="utf-8")
                match = re.search(r'<meta name="citation_pdf_url" content="([^"]+)', response.text)
                if not match:
                    match = re.search(r'href="(https://patentimages[^\"]+\.pdf)"', response.text)
                if not match:
                    raise RuntimeError(f"PDF download link not found: {publication}")
                url = match[1]
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            if not content.startswith(b"%PDF-"):
                raise RuntimeError(f"Not PDF: {publication}")
            digest = hashlib.sha256(content).hexdigest()
            original = next(
                (entry for entry in pinned["files"] if entry["filename"] == publication + ".pdf"),
                None,
            )
            if original and digest != original["sha256"]:
                raise RuntimeError(f"Published PDF changed: {publication}")
            destination = published / (publication + ".pdf")
            if destination.exists() and destination.read_bytes() != content:
                raise RuntimeError(f"Refusing to replace a different download: {destination}")
            destination.write_bytes(content)
            downloads.append(
                {
                    "publication": publication,
                    "source_page": source_page,
                    "source": url,
                    "sha256": digest,
                    "bytes": len(content),
                    "pages": len(PdfReader(io.BytesIO(content)).pages),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            print(f"Downloaded {publication}: {downloads[-1]['pages']} pages", flush=True)
    save_json(OUT / "publication_downloads.json", downloads)

    # These files came from the publicly linked KIPRIS sample archives.
    for archive in ["kipris_oa_sample.zip", "kipris_patent_oa_2015.zip"]:
        with zipfile.ZipFile(OUT / archive) as package:
            assert package.testzip() is None
    print("Official sample ZIP CRC checks passed", flush=True)


if __name__ == "__main__":
    main()
