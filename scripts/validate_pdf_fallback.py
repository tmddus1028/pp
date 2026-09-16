"""Validate the user's unchanged pp_ex2/pp_vd2 PDFs against source-based expectations."""

import hashlib
import json
from pathlib import Path

from backend.config import Settings
from backend.ingestion.adapters import LocalAdapter
from backend.service import analyze

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "tests/fixtures/pdf_fallback"


def main():
    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    documents = []
    for entry, kind in zip(manifest["files"], ["patent", "office_action"]):
        data = (CASE / entry["filename"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        doc = adapter.read(data, entry["filename"], kind)
        assert len(doc.pages) == entry["pages"]
        documents.append(doc)
    result = analyze(*documents, settings)
    truth = manifest["expected"]
    checks = {
        "claims_1_to_20": [c.claim_number for c in result.patent.claims] == truth["claims"],
        "three_103_rejections": len(result.rejections) == 3
        and all(
            r.statute == e["statute"]
            and r.claims == e["claims"]
            and r.evidence.page_numbers[0] == e["start_page"]
            and {c.name for c in r.cited_references} == set(e["citations"])
            for r, e in zip(result.rejections, truth["rejections"])
        ),
        "five_citation_nodes": len([n for n in result.graph.nodes if n.kind == "citation"]) == 5,
        "original_bytes_unchanged": all(
            hashlib.sha256((CASE / e["filename"]).read_bytes()).hexdigest() == e["sha256"]
            for e in manifest["files"]
        ),
    }
    output = ROOT / "data/validation/pdf_fallback"
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (output / "checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
