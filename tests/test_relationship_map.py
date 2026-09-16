from copy import deepcopy
from unittest.mock import patch

import httpx
from conftest import ROOT
from streamlit.testing.v1 import AppTest

from backend.ingestion.adapters import LocalAdapter, from_text
from backend.service import analyze
from frontend.relationship_map import build_relationship_model


def test_relationship_model_preserves_existing_graph_and_analysis(result):
    payload = result.model_dump(mode="json")
    before = deepcopy(payload)
    model = build_relationship_model(payload)
    assert payload == before
    assert {n["id"] for n in model["nodes"]} == {n["id"] for n in payload["graph"]["nodes"]}
    assert model["edges"] == [
        {k: edge[k] for k in ("source", "target", "relation", "citation_role")}
        for edge in payload["graph"]["edges"]
    ]
    assert next(n for n in model["nodes"] if n["id"] == "CL4")["item_id"] == "claim-4"
    assert model["rejections"] == payload["rejections"]


def test_real_claim_14_dependency_and_five_citations(settings):
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
    result = analyze(patent, oa, settings).model_dump(mode="json")
    model = build_relationship_model(result)
    claim14 = next(i for i in model["items"] if i["id"] == "claim-14")
    assert claim14["depends_on"] == [1] and claim14["children"] == [15]
    assert claim14["direct"] == ["R1", "R2"]
    citations = [i for i in model["items"] if i["kind"] == "citation"]
    assert len(citations) == 5
    assert sorted(c["reference"]["type"] for c in citations) == [
        "npl",
        "npl",
        "patent",
        "patent",
        "patent",
    ]
    assert all(c["rejection_ids"] == ["R2"] for c in citations)
    assert len([e for e in model["edges"] if e["source"] == "R2" and e["relation"] == "cites"]) == 5
    # Cite links retain their actual rejection-level meaning; no invented patent-to-Claim edges.
    assert not any(
        e["source"].startswith("CIT") and e["target"].startswith("CL") for e in model["edges"]
    )


def test_missing_claim_has_no_fabricated_pdf_target(settings):
    result = analyze(
        from_text("Claims\n1. A device.", "patent.txt", "patent"),
        from_text("Claim 99 is rejected under 35 USC 112.", "oa.txt", "office_action"),
        settings,
    )
    model = build_relationship_model(result.model_dump(mode="json"))
    missing = next(n for n in model["nodes"] if n["id"] == "CL99")
    assert missing["status"] == "missing" and missing["item_id"] is None


def test_map_claim_to_pdf_preserves_rejection_scope_and_consumes_event(result):
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", return_value=httpx.Response(200, json=result.model_dump(mode="json"))),
        patch("frontend.relationship_map._component", return_value=None) as component,
    ):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
        app.button(key="demo").click().run()
        assert app.session_state["section"] == "PDF 검토"
        app.sidebar.radio[0].set_value("관계 지도").run()
        assert not app.exception
        component.return_value = {
            "nonce": "claim-jump",
            "action": "open_pdf",
            "ui": {"selected": "CL4", "scope": "R1"},
        }
        app.run()
        assert not app.exception
        assert app.session_state["section"] == "PDF 검토"
        assert app.session_state["review_ui"]["selected"] == "claim-4"
        assert app.session_state["review_ui"]["scope"] == "R1"
        app.sidebar.radio[0].set_value("관계 지도").run()
        assert app.session_state["section"] == "관계 지도"  # Do not replay the old navigation.


def test_map_citation_to_pdf_and_pdf_back_to_map(result):
    ref = result.rejections[0].cited_references[0]
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", return_value=httpx.Response(200, json=result.model_dump(mode="json"))),
        patch("frontend.relationship_map._component", return_value=None) as component,
    ):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
        app.button(key="demo").click().run()
        app.sidebar.radio[0].set_value("관계 지도").run()
        component.return_value = {
            "nonce": "citation-jump",
            "action": "open_pdf",
            "ui": {"selected": ref.citation_id, "scope": "R1"},
        }
        app.run()
        assert app.session_state["section"] == "PDF 검토"
        assert app.session_state["review_ui"]["selected"] == "citation-" + ref.citation_id
        ui = dict(app.session_state["review_ui"])
        with patch(
            "frontend.pdf_review._component",
            return_value={
                "nonce": "map-jump",
                "navigation": app.session_state["review_navigation"],
                "action": "open_map",
                "ui": ui,
            },
        ):
            app.run()
        assert not app.exception
        assert app.session_state["section"] == "관계 지도"
        assert app.session_state["relationship_ui"]["selected"] == ref.citation_id
        assert app.session_state["relationship_ui"]["scope"] == "R1"
