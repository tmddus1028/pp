from copy import deepcopy
from unittest.mock import patch

import httpx
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app(result):
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", return_value=httpx.Response(200, json=result.model_dump(mode="json"))),
        patch("frontend.pdf_review._component", return_value=None),
    ):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
        app.button(key="demo").click().run()
        yield app


def test_initial_review_has_no_selection_or_expansion(app):
    assert not app.exception
    assert app.session_state["review_ui"]["selected"] is None
    assert app.session_state["review_ui"]["expanded"] is None
    assert app.session_state["review_ui"]["viewer_evidence"] is None
    assert app.session_state["review_ui"]["active_rejection"] is None
    assert app.session_state["selected_claim"] is None
    assert app.session_state["review_ui"]["page"] == 1
    assert app.session_state["review_ui"]["filter"] == "all"


def test_plain_reentry_clears_details_and_discards_late_events(app):
    before = deepcopy(app.session_state["result"])
    ui = {**app.session_state["review_ui"], "selected": "claim-4", "expanded": "claim-4"}
    ui["checked"] = {"R1-T1": True}
    ui["filter"] = "supporting_evidence"
    event = {"nonce": "select-four", "navigation": app.session_state["review_navigation"], "ui": ui}
    with patch("frontend.pdf_review._component", return_value=event):
        app.run()
    assert app.session_state["review_ui"]["expanded"] == "claim-4"
    app.sidebar.radio[0].set_value("청구항 분석").run()
    app.sidebar.radio[0].set_value("PDF 검토").run()
    assert app.session_state["review_ui"]["selected"] is None
    assert app.session_state["review_ui"]["expanded"] is None
    assert app.session_state["selected_claim"] is None
    assert app.session_state["review_ui"]["checked"] == {"R1-T1": True}
    assert app.session_state["review_ui"]["filter"] == "all"
    event["nonce"] = "late-select-four"
    with patch("frontend.pdf_review._component", return_value=event):
        app.run()
    assert app.session_state["review_ui"]["selected"] is None
    assert app.session_state["review_ui"]["expanded"] is None
    assert app.session_state["result"] == before
    assert not app.exception


def test_explicit_pdf_link_opens_only_the_requested_claim(app):
    app.sidebar.radio[0].set_value("청구항 분석").run()
    app.button(key="claim-pdf-4").click().run()
    assert app.session_state["review_ui"]["selected"] == "claim-4"
    assert app.session_state["review_ui"]["expanded"] == "claim-4"
    assert not app.exception


def test_map_opens_even_when_no_claim_is_selected(app):
    with patch(
        "frontend.pdf_review._component",
        return_value={
            "nonce": "map-without-selection",
            "navigation": app.session_state["review_navigation"],
            "action": "open_map",
            "ui": dict(app.session_state["review_ui"]),
        },
    ):
        app.run()
    assert app.session_state["section"] == "관계 지도"
    assert not app.exception


def test_oa_navigation_persists_claim_and_independent_viewer_state(app):
    before = deepcopy(app.session_state["result"])
    rejection = app.session_state["review_model"]["rejections"][0]
    ui = {
        **app.session_state["review_ui"],
        "selected": "claim-1",
        "expanded": "claim-1",
        "viewer_evidence": "rejection-R1",
        "active_rejection": "R1",
        "document": rejection["evidence"]["document_id"],
        "page": rejection["evidence"]["page_numbers"][0],
        "filter": "direct_rejection",
    }
    event = {"nonce": "view-R1", "navigation": app.session_state["review_navigation"], "ui": ui}
    with patch("frontend.pdf_review._component", return_value=event):
        app.run()
    assert app.session_state["review_ui"] == ui
    assert app.session_state["selected_claim"] == 1
    app.run()
    assert app.session_state["review_ui"] == ui
    # Plain reentry clears Claim and evidence focus together, retaining normal accordion behavior.
    app.sidebar.radio[0].set_value("청구항 분석").run()
    app.sidebar.radio[0].set_value("PDF 검토").run()
    for field in ("selected", "expanded", "viewer_evidence", "active_rejection"):
        assert app.session_state["review_ui"][field] is None
    assert app.session_state["result"] == before
    assert not app.exception


def test_standalone_rejection_jump_does_not_select_an_arbitrary_claim(app):
    app.session_state["review_jump"] = "rejection-R1"
    app.run()
    ui = app.session_state["review_ui"]
    assert ui["selected"] is None and ui["expanded"] is None
    assert ui["viewer_evidence"] == "rejection-R1" and ui["active_rejection"] == "R1"
    assert app.session_state["selected_claim"] is None
    assert not app.exception
