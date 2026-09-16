from copy import deepcopy

import pytest

from backend.config import Settings
from backend.ingestion.adapters import LocalAdapter
from backend.schemas import AnalysisResult
from backend.service import analyze
from scripts.validate_real_pair import CASE, check_result, verify_source_files


@pytest.fixture(scope="module")
def real_result():
    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    return analyze(
        adapter.read((CASE / "claims.pdf").read_bytes(), "claims.pdf", "patent"),
        adapter.read(
            (CASE / "office_action.pdf").read_bytes(), "office_action.pdf", "office_action"
        ),
        settings,
    )


def test_real_source_hashes():
    assert len(verify_source_files()) == 6


def test_real_pair_against_source_labels(real_result):
    metrics, checks = check_result(real_result)
    assert checks["passed"], checks
    assert metrics["rejection_groups"]["expected"] == 2
    assert metrics["statute_claim_links"]["true_positives"] == 8
    assert metrics["citations"]["true_positives"] == 4
    assert metrics["dependency_edges"]["true_positives"] == 3


def test_real_pair_validation_detects_swapped_citations(real_result):
    wrong = deepcopy(real_result)
    wrong.rejections[0].cited_references, wrong.rejections[1].cited_references = (
        wrong.rejections[1].cited_references,
        wrong.rejections[0].cited_references,
    )
    metrics, checks = check_result(wrong)
    # Aggregate citation scoring alone would conceal this error.
    assert metrics["citations"]["f1"] == 1.0
    assert metrics["rejection_groups"]["f1"] == 0.0
    assert not checks["passed"]


def test_real_pair_validation_detects_bad_evidence(real_result):
    data = real_result.model_dump()
    data["patent"]["claims"][0]["evidence"]["start"] += 1
    _, checks = check_result(AnalysisResult.model_validate(data))
    assert not checks["checks"]["all_evidence_offsets_and_pages_valid"]
    assert not checks["passed"]


def test_ocr_deduplication_retains_original_source_bytes(real_result):
    assert all("중복 OCR" in d.warnings[0] for d in real_result.documents[:1])
    assert real_result.documents[0].text.count("Listing of claims") == 1
    assert len(verify_source_files()) == 6
