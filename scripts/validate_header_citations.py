"""Real public patent + reconstructed OA regression, with explicit source limits.

uv run python scripts/validate_header_citations.py
uv run python scripts/validate_header_citations.py --office-action C:/path/to/actual_oa.pdf
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402
from backend.ingestion.adapters import LocalAdapter  # noqa: E402
from backend.service import analyze  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--patent", type=Path, default=ROOT / "data/raw/us20150283132a1/US20150283132A1.pdf"
    )
    parser.add_argument("--office-action", type=Path)
    args = parser.parse_args()
    oa = (
        args.office_action
        or ROOT / "tests/fixtures/citations/office_action_14623904_reconstructed.txt"
    )
    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    result = analyze(
        adapter.read(args.patent.read_bytes(), args.patent.name, "patent"),
        adapter.read(oa.read_bytes(), oa.name, "office_action"),
        settings,
    )
    claim_text = "\n".join(c.text for c in result.patent.claims)
    r2 = next(r for r in result.rejections if r.statute == "35 USC 103(a)")
    refs = r2.cited_references
    nodes = {n.id for n in result.graph.nodes if n.kind == "citation"}
    edges = [e for e in result.graph.edges if e.source == r2.rejection_id and e.relation == "cites"]
    documents = {d.document_id: d for d in result.documents}
    evidence = [c.evidence for c in result.patent.claims] + [r.evidence for r in result.rejections]
    evidence += [ref.evidence for r in result.rejections for ref in r.cited_references]
    checks = {
        "nineteen_claims": [c.claim_number for c in result.patent.claims] == list(range(1, 20)),
        "claim1_continues_across_pages": len(result.patent.claims[0].evidence.page_numbers) == 2,
        "publication_header_absent_in_claims": "US 2015/0283132 A1" not in claim_text,
        "publication_date_absent_in_claims": "Oct. 8, 2015" not in claim_text,
        "three_patent_references": {r.publication_number for r in refs if r.type == "patent"}
        == {"WO2009013126A1", "WO2008074749A1", "WO2013119950A2"},
        "two_npl_references": {(r.publication, r.year) for r in refs if r.type == "npl"}
        == {("Molecular and Cellular Endocrinology", 2010), ("BMC Cancer", 2009)},
        "five_unique_r2_citations": len(refs) == len({r.citation_id for r in refs}) == 5,
        "five_r2_graph_connections": len(edges) == 5 and {e.target for e in edges} <= nodes,
        "all_evidence_valid": all(
            ev.text == documents[ev.document_id].text[ev.start : ev.end]
            and ev.page_numbers
            == [
                p.number
                for p in documents[ev.document_id].pages
                if p.start < ev.end and p.end > ev.start
            ]
            for ev in evidence
        ),
    }
    report = {
        "patent": str(args.patent),
        "office_action": str(oa),
        "office_action_is_reconstructed": args.office_action is None,
        "same_date_claim_oa_pair_verified": False,
        "claim1_pages": result.patent.claims[0].evidence.page_numbers,
        "removed_margin_count": len(result.documents[0].metadata.removed_margins),
        "checks": checks,
        "passed": all(checks.values()),
    }
    output = ROOT / "data/outputs"
    output.mkdir(parents=True, exist_ok=True)
    (output / "header-citations-analysis.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    (output / "header-citations-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
