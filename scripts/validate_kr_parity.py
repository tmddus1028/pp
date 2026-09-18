"""Evaluate frozen, source-transcribed Korean labels and common model invariants."""

import hashlib
import json
from pathlib import Path

from backend.improvements.context import build_context
from backend.improvements.models import ImprovementRequest
from backend.jurisdictions.korean import analyze_korean

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/kr_parity"


def scores(expected, actual):
    tp = len(expected & actual)
    fp = len(actual - expected)
    fn = len(expected - actual)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted((ROOT / "data/fixtures/korean").glob("*.json")):
        truth = json.loads(path.read_text(encoding="utf8"))
        files = truth["files"]
        for f in files:
            assert hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() == f["sha256"]
        pat = next(ROOT / f["path"] for f in files if f["role"] == "patent")
        refs = [ROOT / f["path"] for f in files if f["role"] == "reference"]
        for oa in [ROOT / f["path"] for f in files if f["role"] == "office_action"]:
            result = analyze_korean(
                pat.read_bytes(),
                pat.name,
                oa.read_bytes(),
                oa.name,
                references=[(p.name, p.read_bytes()) for p in refs],
            )
            record = {
                "application": path.stem,
                "oa_format": oa.suffix,
                "expected": truth["rejections"],
                "actual": [
                    {
                        "statute_code": r.statute_code,
                        "claims": r.claims,
                        "citations": [
                            c.publication_number or c.canonical_key for c in r.cited_references
                        ],
                    }
                    for r in result.rejections
                ],
            }
            record["claim_number_accuracy"] = len(
                set(truth["claims"]) & {c.claim_number for c in result.patent.claims}
            ) / len(set(truth["claims"]) | {c.claim_number for c in result.patent.claims})
            record["dependency_accuracy"] = sum(
                c.depends_on == truth["dependencies"][str(c.claim_number)]
                for c in result.patent.claims
            ) / len(truth["claims"])
            expected = {(i, n) for i, r in enumerate(truth["rejections"]) for n in r["claims"]}
            actual = {(i, n) for i, r in enumerate(result.rejections) for n in r.claims}
            record["rejection_claims"] = scores(expected, actual)
            record["statute_accuracy"] = sum(
                r.statute_code == e["statute_code"]
                for r, e in zip(result.rejections, truth["rejections"])
            ) / len(truth["rejections"])
            expected = {c for r in truth["rejections"] for c in r["citations"]}
            actual = {c.publication_number or c.canonical_key for c in result.citations}
            record["citations"] = scores(expected, actual)
            record["reference_match"] = {
                "provided": len(refs),
                "linked": sum(bool(c.source_document_id) for c in result.citations),
                "exact_publication_match": all(
                    next(
                        d for d in result.documents if d.document_id == c.source_document_id
                    ).source_metadata["publication_number"]
                    == c.publication_number
                    for c in result.citations
                    if c.source_document_id
                ),
            }
            docs = {d.document_id: d for d in result.documents}
            checks = []

            def visit(value):
                if isinstance(value, dict):
                    if {"document_id", "text", "start", "end", "page_numbers"} <= value.keys():
                        d = docs[value["document_id"]]
                        checks.append(
                            d.text[value["start"] : value["end"]] == value["text"]
                            and value["page_numbers"]
                            == [
                                p.number
                                for p in d.pages
                                if p.start < value["end"] and value["start"] < p.end
                            ]
                        )
                    for child in value.values():
                        visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)

            visit(result.model_dump())
            record["evidence_internal_consistency"] = {
                "checked": len(checks),
                "passed": sum(checks),
            }
            record["statuses"] = {
                str(s.claim_number): s.source_status for s in result.claim_statuses
            }
            expected_statuses = {
                str(n): status for status, numbers in truth["statuses"].items() for n in numbers
            }
            record["status_accuracy"] = sum(
                record["statuses"].get(n) == status for n, status in expected_statuses.items()
            ) / len(expected_statuses)
            # Manually transcribed physical PDF pages, independent of parser
            # offsets. This checks starting pages, not glyph/bbox precision.
            page_checks = [
                c.evidence.page_numbers[0]
                == truth["evidence"]["claim_body_start_page"][str(c.claim_number)]
                for c in result.patent.claims
            ]
            if oa.suffix == ".pdf":
                page_checks += [
                    r.evidence.page_numbers[0] == page
                    for r, page in zip(
                        result.rejections, truth["evidence"]["rejection_start_pages"]
                    )
                ]
            record["manual_evidence_start_page_accuracy"] = {
                "checked": len(page_checks),
                "passed": sum(page_checks),
                "accuracy": sum(page_checks) / len(page_checks),
            }
            record["version"] = result.claim_version
            context, sources, _ = build_context(ImprovementRequest(analysis=result, claim_number=1))
            record["improvement_context"] = {
                "reference_excerpts": sum(s.kind == "citation_original" for s in sources),
                "specification_excerpts": sum(s.kind == "specification" for s in sources),
                "real_llm_called": False,
            }
            record["pass"] = (
                record["expected"] == record["actual"]
                and all(checks)
                and record["dependency_accuracy"] == 1
                and record["claim_number_accuracy"] == 1
                and record["status_accuracy"] == 1
                and all(page_checks)
                and record["reference_match"]["linked"] == len(refs)
                and record["reference_match"]["exact_publication_match"]
            )
            (OUT / (path.stem + oa.suffix + ".analysis.json")).write_text(
                result.model_dump_json(indent=2), encoding="utf8"
            )
            records.append(record)
            print(path.stem, oa.suffix, "PASS" if record["pass"] else "FAIL", flush=True)
    (OUT / "parser_metrics.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return 0 if all(r["pass"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
