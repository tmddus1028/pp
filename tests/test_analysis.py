import json

import pytest
from conftest import ROOT
from pydantic import ValidationError

from backend.evaluation.evaluator import GroundTruth, evaluate
from backend.evaluation.metrics import classification_metrics, set_metrics
from backend.schemas import AnalysisResult


def test_impact_and_primary_claims(result):
    assert result.rejections[0].primary_claims == [1]
    assert result.impacts[0].direct_claims == [1, 2, 3]
    assert result.impacts[0].dependency_impacted_claims == [4, 5]
    assert result.impacts[1].dependency_impacted_claims == [7, 8]
    assert result.impacts[2].dependency_impacted_claims == [8]


def test_checklist_evidence(result):
    for rejection, impact in zip(result.rejections, result.impacts):
        assert impact.review_items
        assert all(item.evidence == rejection.evidence for item in impact.review_items)
        assert len({item.item_id for item in impact.review_items}) == len(impact.review_items)


def test_graph_consistency(result):
    nodes = {n.id: n for n in result.graph.nodes}
    assert nodes["CL4"].status == "impacted"
    assert nodes["CL7"].status == "direct"
    assert nodes["CL9"].status == "canceled"
    assert all(e.source in nodes and e.target in nodes and e.evidence for e in result.graph.edges)
    assert any(
        e.source == "CL3" and e.target == "CL4" and e.relation == "depends_on"
        for e in result.graph.edges
    )


def test_schema_roundtrip_and_strict_fields(result):
    assert AnalysisResult.model_validate_json(result.model_dump_json()) == result
    data = json.loads(result.model_dump_json())
    data["patent"]["claims"][0]["independent"] = False
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate(data)


def test_evaluator(result):
    truth = GroundTruth.model_validate_json((ROOT / "data/raw/demo_ground_truth.json").read_text())
    scores = evaluate(result, truth)
    for name in [
        "rejected_claims",
        "statute_claim_links",
        "citations",
        "dependency_edges",
        "impacted_claims",
    ]:
        assert scores[name]["f1"] == 1.0, name


def test_metrics():
    assert set_metrics([1, 2], [2, 3])["f1"] == 0.5
    assert set_metrics([], [1])["recall"] == 0.0
    assert set_metrics([], [])["f1"] == 1.0
    assert classification_metrics(["102", "103"], ["102", "112"])["accuracy"] == 0.5
    with pytest.raises(ValueError):
        classification_metrics([], ["103"])
