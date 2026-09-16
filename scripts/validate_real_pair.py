"""Reproduce one public, version-matched PDF case without an LLM or network calls.

Run from the repository root: uv run python -m scripts.validate_real_pair
Source labels are maintained separately from the predictions.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.evaluation.evaluator import GroundTruth, evaluate
from backend.evaluation.metrics import set_metrics
from backend.ingestion.adapters import LocalAdapter
from backend.main import app, get_settings
from backend.schemas import AnalysisResult
from backend.service import analyze

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "data/raw/uspto_14455526_20160617"
OUTPUT = ROOT / "data/validation/uspto_14455526_20160617"


def verify_source_files() -> dict[str, str]:
    manifest = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
    hashes = {}
    for item in manifest["files"]:
        path = CASE / item["filename"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Source/label hash mismatch: {path.name}")
        hashes[path.name] = digest
    return hashes


def check_result(result: AnalysisResult) -> tuple[dict, dict]:
    truth = GroundTruth.model_validate_json(
        (CASE / "ground_truth.json").read_text(encoding="utf-8")
    )
    labels = json.loads((CASE / "source_labels.json").read_text(encoding="utf-8"))
    metrics = evaluate(result, truth)
    metrics["claim_statuses"] = set_metrics(
        {(str(c.claim_number), c.status) for c in result.patent.claims},
        labels["claims"].items(),
    )
    # The general evaluator scores sets of links. Also check whole rejection groups
    # here so swapped citation assignments or duplicated actions cannot pass.
    predicted_groups = [
        (
            r.statute,
            tuple(sorted(r.claims)),
            tuple(sorted(c.publication_number or c.name or "" for c in r.cited_references)),
        )
        for r in result.rejections
    ]
    expected_groups = [
        (r.statute, tuple(sorted(r.claims)), tuple(sorted(r.citations))) for r in truth.rejections
    ]
    metrics["rejection_groups"] = set_metrics(predicted_groups, expected_groups)
    checks = {
        "local_provider": result.provider == "local",
        "input_page_counts": [len(d.pages) for d in result.documents] == [3, 16],
        "exactly_two_rejections": len(result.rejections) == 2,
        "all_actions_are_rejections": all(r.action_type == "rejection" for r in result.rejections),
        "no_duplicate_groups": len(predicted_groups) == len(set(predicted_groups)),
        "four_unique_patent_references": sum(len(r.cited_references) for r in result.rejections)
        == 4,
        "active_independent_claim_8": [
            c.claim_number for c in result.patent.claims if c.independent and c.status == "active"
        ]
        == labels["independent_active_claims"],
        "primary_claim_8_for_each_ground": all(
            r.primary_claims == labels["primary_claims_per_rejection"] for r in result.rejections
        ),
        "no_missing_claims": all(not i.missing_claims for i in result.impacts),
        "no_additional_dependency_impacts": all(
            not i.dependency_impacted_claims for i in result.impacts
        ),
        "all_four_claims_directly_addressed_per_ground": all(
            i.direct_claims == [3, 4, 5, 8] for i in result.impacts
        ),
        "checklists_present": len(result.impacts) == 2
        and all(i.review_items for i in result.impacts),
        "graph_node_counts": Counter(n.kind for n in result.graph.nodes)
        == {"office_action": 1, "rejection": 2, "claim": 8, "citation": 4},
        "graph_edge_counts": Counter(e.relation for e in result.graph.edges)
        == {"contains": 2, "directly_addresses": 8, "depends_on": 3, "cites": 4},
        "graph_dependencies": {
            (e.source, e.target) for e in result.graph.edges if e.relation == "depends_on"
        }
        == {("CL8", "CL3"), ("CL8", "CL4"), ("CL8", "CL5")},
        "claim_8_spans_all_three_pages": next(
            (c.evidence.page_numbers for c in result.patent.claims if c.claim_number == 8), []
        )
        == [1, 2, 3],
        "oa_cover_date_present": "06/17/2016" in result.documents[1].pages[0].text,
        "oa_summary_response_date_present": "5/6/2016" in result.documents[1].pages[1].text,
        "response_to_arguments_preserved": "Response to Arguments" in result.documents[1].text,
        "oa_last_page_preserved": "/OLABODE AKINTOLA/" in result.documents[1].pages[-1].text,
    }
    documents = {d.document_id: d for d in result.documents}
    evidence_count = 0
    evidence_valid = True

    def walk(value):
        nonlocal evidence_count, evidence_valid
        if isinstance(value, dict):
            if {"document_id", "start", "end", "page_numbers", "text"} <= value.keys():
                evidence_count += 1
                doc = documents.get(value["document_id"])
                evidence_valid &= bool(doc) and 0 <= value["start"] < value["end"] <= len(doc.text)
                if doc:
                    evidence_valid &= doc.text[value["start"] : value["end"]] == value["text"]
                    evidence_valid &= value["page_numbers"] == [
                        p.number
                        for p in doc.pages
                        if p.start < value["end"] and p.end > value["start"]
                    ]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(result.model_dump())
    checks["all_evidence_offsets_and_pages_valid"] = evidence_valid and evidence_count > 0
    checks["all_scored_sets_match"] = all(
        m["exact_match"] == 1.0 for m in metrics.values() if isinstance(m, dict)
    )
    metrics["scope"] = (
        "One source-reviewed development/regression pair; no held-out accuracy claim. Empty additional-impact sets are not positive recall evidence. Narrative quality, case-law references and OCR character accuracy are not scored."
    )
    return metrics, {
        "passed": all(checks.values()),
        "checks": checks,
        "evidence_occurrences_checked": evidence_count,
    }


def run_validation(output: Path = OUTPUT) -> dict:
    hashes = verify_source_files()
    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    patent_bytes, oa_bytes = (
        (CASE / "claims.pdf").read_bytes(),
        (CASE / "office_action.pdf").read_bytes(),
    )
    result = analyze(
        adapter.read(patent_bytes, "claims.pdf", "patent"),
        adapter.read(oa_bytes, "office_action.pdf", "office_action"),
        settings,
    )
    metrics, report = check_result(result)
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (output / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Exercise the actual multipart endpoint with both unedited source-page PDFs.
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze/files",
                files={
                    "patent": ("claims.pdf", patent_bytes, "application/pdf"),
                    "office_action": ("office_action.pdf", oa_bytes, "application/pdf"),
                },
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
    api_ok = (
        response.status_code == 200 and AnalysisResult.model_validate(response.json()) == result
    )
    # Use the public CLI as a separate process, explicitly disabling LLM calls.
    cli = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.cli",
            "--patent",
            str(CASE / "claims.pdf"),
            "--office-action",
            str(CASE / "office_action.pdf"),
            "--provider",
            "local",
            "--output",
            str(output / "cli_analysis.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    (output / "cli.log").write_text(cli.stdout + cli.stderr, encoding="utf-8")
    cli_ok = (
        cli.returncode == 0
        and AnalysisResult.model_validate_json(
            (output / "cli_analysis.json").read_text(encoding="utf-8")
        )
        == result
    )
    report.update(
        {
            "source_sha256": hashes,
            "api_status": response.status_code,
            "api_matches_service": api_ok,
            "cli_exit_code": cli.returncode,
            "cli_matches_service": cli_ok,
        }
    )
    report["passed"] &= api_ok and cli_ok
    (output / "checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = run_validation(args.output.resolve())
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"}, indent=2))
    print(f"Saved real-pair validation to {args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
