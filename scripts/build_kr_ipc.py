"""IPC codes (field of technology) for every application in the KIPRIS precedent DB.

uv run python scripts/build_kr_ipc.py   # → data/precedents/kr_ipc.jsonl {application, ipc}

Read from the A publication's front page "(51) 국제특허분류": the cached PDF
(data/kipris_cache/pdf/PUB_<app>.pdf) or, when missing, the same PDF from Google Patents
(no KIPRIS quota). Similar-case search compares claims only within the same IPC subclass.
"""

import json
import sys
from pathlib import Path

import httpx
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from build_gold_cases import UA, google_publication  # noqa: E402

from backend.precedents.kipris import CACHE  # noqa: E402
from backend.precedents.repository import IPC_PATH, KR_PATH, load  # noqa: E402
from korean_prototype.kr_review.ingestion import ipc_codes  # noqa: E402


def publication(app):
    path = Path(CACHE) / "pdf" / f"PUB_{app}.pdf"
    if not path.exists():
        _, url = google_publication(app)
        content = httpx.get(url, headers=UA, timeout=60).content
        if not content.startswith(b"%PDF"):
            raise RuntimeError("Google Patents 응답이 PDF가 아님")
        path.write_bytes(content)
    return path


def main():
    known = {r["application"]: r for r in load(IPC_PATH) if r["ipc"]}
    apps = sorted({c["application"] for c in load(KR_PATH)})
    failed = []
    for i, app in enumerate(apps, 1):
        if app in known:
            continue
        try:
            text = pymupdf.open(publication(app))[0].get_text()
            known[app] = {"application": app, "ipc": ipc_codes(text)}
        except (RuntimeError, KeyError, IndexError, ValueError, httpx.HTTPError) as exc:
            failed.append(f"{app}: {exc}")
        if i % 25 == 0:
            print(f"{i}/{len(apps)}", flush=True)
    with IPC_PATH.open("w", encoding="utf-8", newline="\n") as f:
        for app in sorted(known):
            f.write(json.dumps(known[app], ensure_ascii=False) + "\n")
    print(f"IPC for {sum(bool(r['ipc']) for r in known.values())}/{len(apps)} applications")
    for line in failed:
        print("failed", line[:120])


if __name__ == "__main__":
    main()
