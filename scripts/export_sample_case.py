"""Save one finished case (analysis, AI advice, choice, draft, PDFs) as the no-API-key sample.

uv run python scripts/export_sample_case.py 15   # → data/samples/kr_0844/

POST /cases/sample (web: '샘플 사건 불러오기') loads it into any teammate's database, so the whole
flow can be shown without ANTHROPIC_API_KEY. Re-export after the AI output format changes.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import backend.main  # noqa: E402, F401  (backend.cases must be imported through main)
from backend import store  # noqa: E402
from backend.cases import SAMPLE_DIR  # noqa: E402


def main():
    case_id = int(sys.argv[1])
    case = store.get_case(case_id)
    selections = {s["id"]: s for s in store.list_selections(case_id)}
    drafts = store.list_drafts(case_id)
    used = [selections[d["selection_id"]] for d in drafts]
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    files = {}
    for document_id in store.get_files(case_id):
        file = store.get_file(case_id, document_id)
        (SAMPLE_DIR / file["filename"]).write_bytes(file["data"])
        files[document_id] = file["filename"]
    sample = {
        "title": "샘플 사건 · 전자쿠폰 0844",
        "analysis_id": case["analysis_id"],
        "result": case["result"],
        "review": case["review"],
        "files": files,
        "advice": [
            {k: a[k] for k in ("rejection_id", "claim_number", "provider", "response")}
            for a in store.list_advice(case_id)[:1]
        ],
        "selections": [
            {k: s[k] for k in ("rejection_id", "record", "confirmed_by")} for s in used[:1]
        ],
        "drafts": [{k: d[k] for k in ("provider", "model", "response")} for d in drafts[:1]],
    }
    path = SAMPLE_DIR / "case.json"
    path.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"case {case_id} → {path.relative_to(ROOT)} + {len(files)} PDFs")


if __name__ == "__main__":
    main()
