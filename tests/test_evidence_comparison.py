from copy import deepcopy
from unittest.mock import patch

import httpx
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

from backend.ingestion.adapters import LocalAdapter, from_text
from backend.service import analyze
from frontend.evidence_comparison import comparison_for_claim
from frontend.review_model import build_review_model


@pytest.fixture
def comparison_result(settings):
    adapter = LocalAdapter(settings)
    patent = adapter.read(
        (ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf").read_bytes(),
        "patent.pdf",
        "patent",
    )
    oa = adapter.read(
        (ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf").read_bytes(),
        "oa.pdf",
        "office_action",
    )
    return analyze(patent, oa, settings).model_dump(mode="json")


def test_real_claim14_comparison_preserves_evidence_and_all_five_citations(comparison_result):
    before = deepcopy(comparison_result)
    model = build_review_model(comparison_result)
    view = comparison_for_claim(model, 14)
    assert comparison_result == before
    assert view["claim"]["depends_on"] == [1]
    assert view["claim"]["children"] == [15]
    assert view["role"] == "direct_rejection"
    assert [r["rejection_id"] for r in view["rejections"]] == ["R1", "R2"]
    assert sorted(e["reference"]["type"] for e in view["citations"]) == [
        "npl",
        "npl",
        "patent",
        "patent",
        "patent",
    ]
    assert len({e["reference"]["citation_id"] for e in view["citations"]}) == 5
    assert all(e["rejection_ids"] == ["R2"] and 14 in e["claim_numbers"] for e in view["citations"])
    assert view["support"] == []
    for evidence in [
        view["claim"]["evidence"],
        *[r["evidence"] for r in view["rejections"]],
        *[e["reference"]["evidence"] for e in view["citations"]],
    ]:
        doc = next(
            d for d in comparison_result["documents"] if d["document_id"] == evidence["document_id"]
        )
        assert doc["text"][evidence["start"] : evidence["end"]] == evidence["text"]


def test_scope_changes_keep_direct_and_inherited_grounds_distinct(comparison_result):
    model = build_review_model(comparison_result)
    first = comparison_for_claim(model, 14, "R1")
    second = comparison_for_claim(model, 14, "R2")
    assert first["statutes"] == ["35 USC 112"] and first["citations"] == []
    assert second["statutes"] == ["35 USC 103(a)"] and len(second["citations"]) == 5
    claim2 = comparison_for_claim(model, 2, "R1")
    assert claim2["role"] == "dependency" and claim2["claim"]["direct"] == ["R2"]


def test_specification_requires_an_existing_explicit_link(settings):
    patent = from_text(
        "[0018] A sensor and controller.\nClaims\n1. A sensor and controller.",
        "patent.txt",
        "patent",
    )
    unlinked = from_text(
        "Claim 1 is rejected under 35 USC 112(b). A sensor and controller are unclear.",
        "oa.txt",
        "office_action",
    )
    linked = from_text(
        "Claim 1 is rejected under 35 USC 112(b). See paragraph [0018].", "oa.txt", "office_action"
    )
    view = comparison_for_claim(
        build_review_model(analyze(patent, unlinked, settings).model_dump(mode="json")), 1
    )
    assert view["support"] == []  # Matching vocabulary is not a support link.
    view = comparison_for_claim(
        build_review_model(analyze(patent, linked, settings).model_dump(mode="json")), 1
    )
    assert len(view["support"]) == 1
    assert view["support"][0]["title"] == "Paragraph [0018]"


@pytest.fixture
def app(comparison_result):
    with patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15)
        app.session_state["result"] = comparison_result
        app.session_state["section"] = "근거 비교"
        app.run()
        yield app


def test_claim_and_scope_selectors_update_all_comparison_cards(app):
    app.selectbox(key="comparison_claim").select(14).run()
    assert not app.exception
    assert any("현재 자동 연결된 명세서 근거가 없습니다." in m.value for m in app.markdown)
    assert len(app.expander) == 5
    app.selectbox(key="comparison_scope").select("R1").run()
    assert len(app.expander) == 0
    assert any('data-focus="112"' in m.value for m in app.markdown)
    assert not any(
        'data-focus="103"' in m.value
        for m in app.markdown
        if m.value.startswith('<div class="comparison-focus">')
    )
    app.selectbox(key="comparison_scope").select("R2").run()
    assert len(app.expander) == 5
    app.selectbox(key="comparison_claim").select(2).run()
    assert app.selectbox(key="comparison_scope").value == "all"
    app.selectbox(key="comparison_scope").select("R1").run()
    assert any("종속 영향 · 직접 지적 아님" in m.value for m in app.markdown)
    assert not app.exception


@pytest.mark.parametrize(
    "target,expected,scope",
    [
        ("comparison-claim-pdf", "claim-14", "R2"),
        ("comparison-oa-R2", "rejection-R2", "R2"),
    ],
)
def test_comparison_to_pdf_navigation_and_return_preserve_selection(app, target, expected, scope):
    app.selectbox(key="comparison_claim").select(14).run()
    app.selectbox(key="comparison_scope").select(scope).run()
    app.button(key=target).click().run()
    assert not app.exception
    assert app.session_state["section"] == "PDF 검토"
    assert app.session_state["review_ui"]["selected"] == "claim-14"
    assert app.session_state["review_ui"]["expanded"] == "claim-14"
    assert app.session_state["review_ui"]["viewer_evidence"] == expected
    assert app.session_state["review_ui"]["active_rejection"] == (
        "R2" if expected == "rejection-R2" else None
    )
    assert app.session_state["review_ui"]["scope"] == scope
    app.sidebar.radio[0].set_value("근거 비교").run()
    assert app.selectbox(key="comparison_claim").value == 14
    assert app.selectbox(key="comparison_scope").value == scope


def test_comparison_has_no_pdf_viewer_or_renderer(app):
    with patch("frontend.pdf_review._component") as component, patch("httpx.post") as post:
        app.run()
        app.selectbox(key="comparison_claim").select(14).run()
    component.assert_not_called()
    post.assert_not_called()
    assert not app.exception


@pytest.mark.parametrize("origin", ["pdf", "map"])
def test_other_views_send_claim_and_scope_to_comparison(app, origin):
    section = "PDF 검토" if origin == "pdf" else "관계 지도"
    app.sidebar.radio[0].set_value(section).run()
    if origin == "pdf":
        ui = {
            **app.session_state["review_ui"],
            "selected": "claim-14",
            "expanded": "claim-14",
            "scope": "R2",
        }
        event = {
            "nonce": "comparison-pdf",
            "action": "open_comparison",
            "ui": ui,
            "navigation": app.session_state["review_navigation"],
        }
        target = "frontend.pdf_review._component"
    else:
        event = {
            "nonce": "comparison-map",
            "action": "open_comparison",
            "ui": {"selected": "CL14", "scope": "R1"},
        }
        target = "frontend.relationship_map._component"
    with patch(target, return_value=event):
        app.run()
    assert not app.exception
    assert app.session_state["section"] == "근거 비교"
    assert app.selectbox(key="comparison_claim").value == 14
    assert app.selectbox(key="comparison_scope").value == ("R2" if origin == "pdf" else "R1")
    app.run()
    assert app.session_state["section"] == "근거 비교"
