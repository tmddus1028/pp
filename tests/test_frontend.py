from copy import deepcopy
from html import unescape
from unittest.mock import patch

import httpx
import pytest
from conftest import ROOT
from streamlit.testing.v1 import AppTest

from frontend.claim_analysis import claim_rows, filter_claims


@pytest.fixture
def analysis_app(result):
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", return_value=httpx.Response(200, json=result.model_dump(mode="json"))),
    ):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
        app.button(key="demo").click().run()
        app.sidebar.radio[0].set_value("청구항 분석").run()
        yield app


def test_empty_state():
    with patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15).run()
    assert not app.exception
    assert app.button(key="analyze").disabled
    assert any("Patent Review" in m.value for m in app.markdown)


def test_compact_summary_and_collapsed_claim_list(analysis_app):
    app = analysis_app
    assert not app.exception
    assert [m.value for m in app.metric] == ["9", "3", "5", "3", "0"]
    assert [m.label for m in app.metric] == [
        "전체 청구항",
        "거절/지적 사유",
        "직접 지적 Claim",
        "추가 검토 Claim",
        "허용 Claim",
    ]
    assert len([b for b in app.button if b.label == "PDF에서 보기"]) == 9
    assert all(not e.proto.expanded for e in app.expander)
    assert not app.warning and not app.info
    assert not app.tabs and not app.selectbox
    assert not any(e.label == "기존 그래프 보기" for e in app.expander)


def test_exact_claim_search_filters_and_empty_state(analysis_app):
    app = analysis_app
    original = deepcopy(app.session_state["result"])
    counts = [m.value for m in app.metric]
    assert app.radio(key="claim_status_filter").options == [
        "전체",
        "직접 지적",
        "추가 검토",
        "허용",
    ]
    app.radio(key="claim_status_filter").set_value("추가 검토").run()
    rows = [b.key for b in app.button if b.label == "PDF에서 보기"]
    assert rows == ["claim-pdf-4", "claim-pdf-5", "claim-pdf-8"]
    app.radio(key="claim_status_filter").set_value("직접 지적").run()
    assert len([b for b in app.button if b.label == "PDF에서 보기"]) == 5
    assert any("35 U.S.C. 103" in m.value for m in app.markdown)
    app.radio(key="claim_status_filter").set_value("허용").run()
    assert not [b for b in app.button if b.label == "PDF에서 보기"]
    app.radio(key="claim_status_filter").set_value("전체").run()
    app.text_input(key="claim_number_search").set_value("4").run()
    assert [b.key for b in app.button if b.label == "PDF에서 보기"] == ["claim-pdf-4"]
    app.text_input(key="claim_number_search").set_value("999").run()
    assert not [b for b in app.button if b.label == "PDF에서 보기"]
    assert any("조건에 맞는 Claim이 없습니다" in m.value for m in app.markdown)
    assert [m.value for m in app.metric] == counts
    assert app.session_state["result"] == original
    app.sidebar.radio[0].set_value("PDF 검토").run()
    app.session_state["claim_status_filter"] = "§103"
    app.sidebar.radio[0].set_value("청구항 분석").run()
    assert app.radio(key="claim_status_filter").value == "전체"
    assert app.text_input(key="claim_number_search").value == "999"
    assert not app.exception


def test_claim_pdf_roundtrip_keeps_selection_and_filters(analysis_app):
    app = analysis_app
    app.text_input(key="claim_number_search").set_value("4").run()
    app.button(key="claim-pdf-4").click().run()
    assert not app.exception
    assert app.session_state["section"] == "PDF 검토"
    assert app.session_state["review_ui"]["selected"] == "claim-4"
    assert app.session_state["review_ui"]["scope"] == "all"
    assert app.session_state["review_ui"]["search"] == ""
    app.sidebar.radio[0].set_value("청구항 분석").run()
    assert app.text_input(key="claim_number_search").value == "4"
    assert any('data-claim="4"' in m.value and "selected" in m.value for m in app.markdown)


def test_checklist_state_shared_between_claims_and_pdf(analysis_app):
    app = analysis_app
    app.text_input(key="claim_number_search").set_value("1").run()
    check = next(c for c in app.checkbox if "Smith" in c.label)
    check.check().run()
    item_id = "-".join(check.key.rsplit("-", 2)[-2:])
    assert app.session_state["review_ui"]["checked"][item_id]
    app.text_input(key="claim_number_search").set_value("2").run()
    assert next(c for c in app.checkbox if "Smith" in c.label).value
    app.button(key="claim-pdf-2").click().run()
    app.session_state["review_ui"]["checked"][item_id] = False
    app.sidebar.radio[0].set_value("청구항 분석").run()
    assert not next(c for c in app.checkbox if "Smith" in c.label).value
    assert not app.exception


@pytest.mark.parametrize("provider", ["local", "openai", "azure"])
def test_processing_details_and_old_metadata_compatibility(result, provider):
    payload = result.model_dump(mode="json")
    payload["provider"] = provider
    payload["documents"][0].pop("metadata")
    payload["documents"][1]["metadata"] = {
        "ocr_used": True,
        "ocr_engine": "tesseract",
        "ocr_renderer": "pdfium",
        "ocr_pages": [2, 4],
        "ocr_raw_text": {"2": "Claims 1-19 under 35 U.S.C. § 103"},
    }
    payload["warnings"].append("PyMuPDF fallback debug")
    with patch("httpx.get", return_value=httpx.Response(200, json={"provider": provider})):
        app = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15)
        app.session_state["result"] = payload
        app.session_state["section"] = "청구항 분석"
        app.run()
    assert not app.exception
    details = next(e for e in app.expander if e.label == "문서 처리 정보 보기")
    assert not details.proto.expanded
    assert any(m.value == "PyMuPDF fallback debug" for m in details.text)
    assert any(f"분석 provider: {provider}" in m.value for m in details.caption)
    assert any("OCR 페이지: 2, 4" in m.value for m in details.caption)
    assert any("35 U.S.C. § 103" in m.value for m in details.code)
    assert not app.warning and not app.info
    assert any("✓ 문서 분석 완료 · OCR 사용됨" in m.value for m in app.markdown)


def test_claim_details_keep_citation_sources(analysis_app, result):
    app = analysis_app
    app.text_input(key="claim_number_search").set_value("1").run()
    ref = result.rejections[0].cited_references[1]
    assert any(ref.evidence.text in unescape(item.value) for item in app.markdown)
    assert any("OA 인용" in item.value for item in app.caption)
    assert any("Patent" in e.label and ref.name in e.label for e in app.expander)


def test_claim_presentation_does_not_change_analysis_or_merge_distinct_claims(result):
    payload = result.model_dump(mode="json")
    before = deepcopy(payload)
    rows, _ = claim_rows(payload)
    assert payload == before
    assert [r["claim_number"] for r in filter_claims(rows, "전체", "1")] == [1]
    assert filter_claims(rows, "전체", "1x") == []
    direct = {n for i in payload["impacts"] for n in i["direct_claims"]}
    assert {r["claim_number"] for r in rows if r["role"] == "direct_rejection"} == direct
    for row in rows:
        original = next(
            c for c in payload["patent"]["claims"] if c["claim_number"] == row["claim_number"]
        )
        assert row["evidence"] == original["evidence"]
        assert row["depends_on"] == original["depends_on"]
