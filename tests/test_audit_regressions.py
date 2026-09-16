"""Bugs reproduced during the complete feature audit; no external LLM calls."""

from copy import deepcopy
from unittest.mock import patch

import httpx
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

from backend.analysis.citation_analyzer import normalize_publication
from backend.evaluation.evaluator import GroundTruth, evaluate
from backend.ingestion.adapters import from_text
from backend.service import analyze
from frontend.evidence_comparison import comparison_for_claim
from frontend.review_model import build_review_model


def test_real_ocr_wo_typo_does_not_drop_following_npl(settings):
    text = (ROOT / "tests/fixtures/citations/office_action_14623904_ocr_excerpt.txt").read_text(
        encoding="utf-8"
    )
    result = analyze(
        from_text("Claims\n1. A method of treatment.", "p.txt", "patent"),
        from_text(text, "oa.txt", "office_action"),
        settings,
    )
    refs = result.rejections[0].cited_references
    assert len(refs) == 5
    assert [r.type for r in refs] == ["patent"] * 3 + ["npl"] * 2
    hout = refs[2]
    assert hout.publication_number == "WO2013119950A2"
    assert "W02013/119950 A2" in hout.evidence.text
    assert result.documents[1].text == text
    for ref in refs:
        assert text[ref.evidence.start : ref.evidence.end] == ref.evidence.text
    assert normalize_publication("W0 is an arbitrary variable") is None


@pytest.fixture
def with_supporting(settings):
    return analyze(
        from_text(
            "Claims\n1. A device comprising a sensor.\n2. The device of claim 1.", "p.txt", "patent"
        ),
        from_text(
            "Claims 1-2 are rejected under 35 USC 103 over Smith (US 2020/0123456 A1) as evidenced by Wei (US 2021/0123456 A1).",
            "oa.txt",
            "office_action",
        ),
        settings,
    ).model_dump(mode="json")


def test_comparison_hides_supporting_but_keeps_backend(with_supporting):
    before = deepcopy(with_supporting)
    model = build_review_model(with_supporting)
    view = comparison_for_claim(model, 1)
    assert [c["reference"]["name"] for c in view["citations"]] == ["Smith"]
    assert any(c["display_name"] == "Wei" for c in with_supporting["citations"])
    assert with_supporting == before


def test_claim_details_hide_supporting_citation_cards(with_supporting):
    with patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15)
        app.session_state["result"] = with_supporting
        app.session_state["section"] = "청구항 분석"
        app.run()
    assert not app.exception
    assert not any("Wei" in e.label for e in app.expander)
    assert any("Smith" in e.label for e in app.expander)


def test_evaluation_does_not_score_objections_as_rejections(settings):
    result = analyze(
        from_text("Claims\n1. A device.\n2. A sensor.", "p.txt", "patent"),
        from_text(
            "Claim 1 is rejected under 35 USC 112.\nClaim 2 is objected to because of its form.",
            "oa.txt",
            "office_action",
        ),
        settings,
    )
    truth = GroundTruth(
        provenance="audit synthetic",
        rejections=[{"statute": "35 USC 112", "claims": [1]}],
        dependency_edges=[],
        impacted_claims=[],
    )
    metrics = evaluate(result, truth)
    assert metrics["rejected_claims"]["predicted"] == 1
    assert metrics["statute_claim_links"]["exact_match"] == 1


def test_repeat_analysis_resets_claim_and_comparison_filters(result):
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", return_value=httpx.Response(200, json=result.model_dump(mode="json"))),
    ):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
        app.button(key="demo").click().run()
        app.sidebar.radio[0].set_value("청구항 분석").run()
        app.text_input(key="claim_number_search").set_value("999").run()
        app.sidebar.radio[0].set_value("근거 비교").run()
        app.selectbox(key="comparison_claim").set_value(7).run()
        app.sidebar.radio[0].set_value("문서 업로드").run()
        app.button(key="demo").click().run()
        assert app.session_state["review_ui"]["selected"] is None
        app.sidebar.radio[0].set_value("청구항 분석").run()
        assert app.text_input(key="claim_number_search").value == ""
        app.sidebar.radio[0].set_value("근거 비교").run()
        assert app.selectbox(key="comparison_claim").value == 1


def test_stale_map_event_does_not_override_explicit_navigation(result):
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", return_value=httpx.Response(200, json=result.model_dump(mode="json"))),
        patch("frontend.relationship_map._component", return_value=None) as component,
    ):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
        app.button(key="demo").click().run()
        app.sidebar.radio[0].set_value("관계 지도").run()
        old_navigation = app.session_state["relationship_navigation"]
        app.session_state["relationship_jump"] = "claim-2"
        component.return_value = {
            "nonce": "late-event",
            "navigation": old_navigation,
            "ui": {"selected": "CL1", "scope": "all"},
        }
        app.run()
        assert not app.exception
        assert app.session_state["relationship_ui"]["selected"] == "CL2"


@pytest.mark.parametrize(
    "section,prefix,selected",
    [("관계 지도", "relationships", "CL7"), ("PDF 검토", "pdf", "claim-7")],
)
def test_sidebar_navigation_consumes_pending_component_selection(result, section, prefix, selected):
    payload = result.model_dump(mode="json")
    with patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15)
        app.session_state["result"] = payload
        app.session_state["section"] = section
        app.run()
        key = "relationship" if prefix == "relationships" else "review"
        ui = dict(app.session_state[key + "_ui"])
        ui.update(selected=selected, scope="all")
        app.session_state[prefix + "-" + payload["analysis_id"]] = {
            "nonce": "pending-choice",
            "navigation": app.session_state[key + "_navigation"],
            "ui": ui,
        }
        app.sidebar.radio[0].set_value("근거 비교").run()
        assert app.selectbox(key="comparison_claim").value == 7
