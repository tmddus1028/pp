import argparse
import json
from pathlib import Path

from pydantic import Field

from backend.evaluation.metrics import set_metrics
from backend.office_action.rejection_extractor import normalize_statute
from backend.schemas import AnalysisResult, Model


class ActionLabel(Model):
    statute: str
    claims: list[int]
    citations: list[str] = Field(default_factory=list)


class GroundTruth(Model):
    provenance: str
    rejections: list[ActionLabel]
    dependency_edges: list[tuple[int, int]]
    impacted_claims: list[int]


def evaluate(result: AnalysisResult, truth: GroundTruth) -> dict:
    predicted = {(normalize_statute(r.statute), n) for r in result.rejections for n in r.claims}
    expected = {(normalize_statute(r.statute), n) for r in truth.rejections for n in r.claims}
    return {
        "provenance": truth.provenance,
        "rejected_claims": set_metrics({n for _, n in predicted}, {n for _, n in expected}),
        "statute_claim_links": set_metrics(predicted, expected),
        "citations": set_metrics(
            {c.publication_number or c.name for r in result.rejections for c in r.cited_references},
            {c for r in truth.rejections for c in r.citations},
        ),
        "dependency_edges": set_metrics(
            {(parent, c.claim_number) for c in result.patent.claims for parent in c.depends_on},
            truth.dependency_edges,
        ),
        "impacted_claims": set_metrics(
            {n for i in result.impacts for n in i.dependency_impacted_claims}, truth.impacted_claims
        ),
        "note": "Statute/claim link scoring does not evaluate rejection grouping or natural-language explanations.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result", type=Path)
    parser.add_argument("ground_truth", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    metrics = evaluate(
        AnalysisResult.model_validate_json(args.result.read_text(encoding="utf-8")),
        GroundTruth.model_validate_json(args.ground_truth.read_text(encoding="utf-8")),
    )
    rendered = json.dumps(metrics, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
