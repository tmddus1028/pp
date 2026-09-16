import hashlib
from types import SimpleNamespace

import pytest
from conftest import ROOT
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.errors import ExtractionError
from backend.ingestion.adapters import LocalAdapter, from_text
from backend.llm.client import ExtractionBatch, RejectionDraft
from backend.main import app, get_settings
from backend.office_action.rejection_extractor import extract_local
from backend.service import analyze
from frontend.claim_analysis import claim_rows

FIXTURES = ROOT / "tests/fixtures/oa_status"
SYNTHETIC = (FIXTURES / "18731426_reconstructed.txt").read_text(encoding="utf-8")
CLAIMS = "Claims\n1. A device comprising a sensor.\n" + "\n".join(
    f"{n}. The device of claim 1, wherein the sensor comprises a processor." for n in range(2, 21)
)


def run(text, settings):
    return analyze(
        from_text(CLAIMS, "claims.txt", "patent"),
        from_text(text, "oa.txt", "office_action"),
        settings,
    )


@pytest.fixture(scope="module")
def actual_pair():
    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    data = (FIXTURES / "pp_vd3.pdf").read_bytes()
    assert (
        hashlib.sha256(data).hexdigest()
        == "358fb0006ab595e02988cbbe4a83affe285ae609d2518b942a1c9712cf19fe3b"
    )
    return analyze(
        adapter.read(
            (ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf").read_bytes(), "pp_ex3.pdf", "patent"
        ),
        adapter.read(data, "pp_vd3.pdf", "office_action"),
        settings,
    )


def test_actual_pdf_is_different_case_and_five_grounds_remain(actual_pair):
    text = actual_pair.documents[1].text
    assert "17/708,932" in text and "18/731,426" not in text
    summary = actual_pair.claim_summary
    assert summary.direct_rejected_claims == list(range(1, 15)) + [17, 18, 19]
    assert summary.objected_claims == [15, 16]
    assert summary.canceled_claims == [20]
    assert summary.allowed_claims == []
    assert 20 not in summary.dependency_impacted_claims
    rejections = [r for r in actual_pair.rejections if r.action_type == "rejection"]
    assert len(rejections) == 5
    assert [r.statute for r in rejections] == ["35 USC 103"] * 5
    assert [r.claims for r in rejections] == [
        [1, 2, 3, 4, 6, 8, 17, 18, 19],
        [5, 6],
        [7, 9],
        [10, 11],
        [12, 13, 14],
    ]
    objection = next(r for r in actual_pair.rejections if r.action_type == "objection")
    assert objection.claims == [15, 16] and objection.cited_references == []
    assert "Conclusion" not in objection.evidence.text


def assert_source_spans(result):
    documents = {d.document_id: d for d in result.documents}
    for record in result.claim_statuses:
        if record.evidence:
            ev = record.evidence
            doc = documents[ev.document_id]
            assert doc.text[ev.start : ev.end] == ev.text
            assert ev.page_numbers == [
                p.number for p in doc.pages if p.start < ev.end and p.end > ev.start
            ]


def test_actual_objections_are_amber_and_cancelled_not_impacted(actual_pair):
    rows, model = claim_rows(actual_pair.model_dump())
    for number in [15, 16]:
        row = rows[number - 1]
        assert row["direct"] == [] and row["role"] == "dependency"
        assert row["status"] == "objected" and row["conditional_allowance"]
    assert rows[19]["status"] == "canceled" and rows[19]["indirect"] == []
    assert "R6 · Objection" in {i["title"] for i in model["items"]}
    assert not any(
        a["type"] == "direct_rejection" and a["claim_number"] in [15, 16, 20]
        for a in model["annotations"]
    )
    assert_source_spans(actual_pair)


def test_user_supplied_18731426_statuses_reconstructed_not_original(settings):
    result = run(SYNTHETIC, settings)
    summary = result.claim_summary
    assert summary.direct_rejected_claims == [1, 2, 3, 8]
    assert summary.objected_claims == [4, 5, 6, 7, 9, 10]
    assert summary.allowed_claims == list(range(11, 21))
    assert summary.dependency_impacted_claims == [4, 5, 6, 7, 9, 10]
    grounds = [r for r in result.rejections if r.action_type == "rejection"]
    assert len(grounds) == 1 and grounds[0].claims == [1, 2, 3, 8]
    assert {(r.name, r.publication_number) for r in grounds[0].cited_references} == {
        ("Wu", "US20230402512"),
        ("Ando", "US20210328013"),
    }
    assert len([n for n in result.graph.nodes if n.kind == "citation"]) == 2
    nodes = {n.claim_number: n for n in result.graph.nodes if n.kind == "claim"}
    assert all(nodes[n].status == "allowed" for n in range(11, 21))
    rows, _ = claim_rows(result.model_dump())
    assert sum(r["role"] == "direct_rejection" for r in rows) == 4
    assert sum(r["role"] == "dependency" for r in rows) == 6
    assert sum(r["status"] == "allowed" for r in rows) == 10
    assert_source_spans(result)


@pytest.mark.parametrize(
    "text",
    [
        "Regarding claim 15, Smith describes a sensor.",
        "Claims 11-20 are allowed.",
        "Claims 4-7 and 9-10 depend directly or indirectly on claim 1.",
        "Claims 4-7 would be allowable if rewritten in independent form.",
        "Reasons for Allowance\nRegarding claim 16, the combination is novel.",
        "Claims 1-3 are not rejected under 35 USC 103.",
        "Allowable\nSubject\nMatter\nClaims 11-20 are rejected under 35 USC 103.",
    ],
)
def test_mentions_and_allowance_sections_do_not_create_rejection(text):
    assert extract_local(from_text(text, "oa.txt", "office_action"))[0] == []


@pytest.mark.parametrize(
    "status,expected",
    [
        ("allowed", "allowed"),
        ("withdrawn", "withdrawn"),
        ("now cancelled", "canceled"),
        ("pending", "pending"),
        ("objected to because of a typo", "objected"),
    ],
)
def test_dispositions_are_explicit_and_do_not_become_direct_rejections(settings, status, expected):
    result = run(f"Claims 2-3 are {status}.", settings)
    assert result.claim_summary.direct_rejected_claims == []
    assert {s.status for s in result.claim_statuses if s.claim_number in [2, 3]} == {expected}
    assert next(s for s in result.claim_statuses if s.claim_number == 1).status == "unknown"


def test_pending_does_not_undo_allowance_and_word_per_line_headings_stop_grounds(settings):
    result = run(
        "Claim 1 is rejected under 35 USC 112.\nAllowable\nSubject\nMatter\n"
        "Claims 2-20 are allowed.\nClaims 1-20 are pending.",
        settings,
    )
    assert result.claim_summary.direct_rejected_claims == [1]
    assert result.claim_summary.allowed_claims == list(range(2, 21))
    assert result.claim_summary.dependency_impacted_claims == []
    assert "Allowable" not in result.rejections[0].evidence.text


def test_objection_only_has_no_direct_impact_or_red_graph(settings):
    result = run("Claim 1 is objected to because of a typo.", settings)
    assert result.impacts[0].direct_claims == []
    assert result.impacts[0].objected_claims == [1]
    assert result.impacts[0].dependency_impacted_claims == []
    assert next(n for n in result.graph.nodes if n.id == "CL1").status == "objected"


def test_incidental_patents_in_same_block_do_not_become_relied_upon(settings):
    result = run(
        "Claim 1 is rejected under 35 USC 103 over Wu (US 2023/0402512) "
        "in view of Ando (US 2021/0328013). The examiner mentions Smith (US 2010/0123456) "
        "and Jones (US 2012/0987654) in background discussion.",
        settings,
    )
    assert {r.name for r in result.rejections[0].cited_references} == {"Wu", "Ando"}


@pytest.mark.parametrize("provider", ["openai", "azure"])
def test_llm_cannot_turn_objection_or_regarding_mentions_into_rejected_claims(settings, provider):
    oa = "Regarding claim 15, the rejected base claim is discussed. Claim 16 is objected to because of a rejected base claim."
    draft = RejectionDraft(
        action_type="rejection",
        statute="unknown",
        claims=[15, 16],
        reason_summary="Bad inference",
        examiner_explanation=oa,
        cited_references=[],
        evidence=oa,
    )
    client = SimpleNamespace(extract=lambda text: ExtractionBatch(rejections=[draft]))
    with pytest.raises(ExtractionError):
        analyze(
            from_text(CLAIMS, "p.txt", "patent"),
            from_text(oa, "oa.txt", "office_action"),
            settings.model_copy(update={"llm_provider": provider}),
            client,
        )


def test_multipart_reconstructed_status_summary(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze/files",
                files={
                    "patent": ("claims.txt", CLAIMS.encode(), "text/plain"),
                    "office_action": ("reconstructed_oa.txt", SYNTHETIC.encode(), "text/plain"),
                },
            )
        assert response.status_code == 200, response.text
        summary = response.json()["claim_summary"]
        assert summary["direct_rejected_claims"] == [1, 2, 3, 8]
        assert len(summary["objected_claims"]) == 6 and len(summary["allowed_claims"]) == 10
    finally:
        app.dependency_overrides.clear()
