"""Korean adapter contract, jurisdiction isolation and reuse of existing UI."""

import hashlib
import json
from copy import deepcopy
from unittest.mock import patch

import httpx
import pytest
from conftest import ROOT
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.jurisdictions.korean import analyze_korean
from backend.main import app, get_settings
from backend.schemas import AnalysisResult
from frontend.claim_analysis import claim_rows
from frontend.pdf_adapter import attach_coordinates
from frontend.review_model import build_review_model
from korean_prototype.kr_review.service import analyze as extract_korean

DATA = ROOT / "korean_prototype/data/kr_1020190000844"


@pytest.fixture(scope="module")
def korean_inputs():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        assert (
            hashlib.sha256((DATA / entry["filename"]).read_bytes()).hexdigest() == entry["sha256"]
        )
    return (
        (DATA / "KR20190025857A.pdf").read_bytes(),
        "KR20190025857A.pdf",
        (DATA / "office_action_20190409.xml").read_bytes(),
        "office_action_20190409.xml",
    )


@pytest.fixture(scope="module")
def korean_result(korean_inputs):
    return analyze_korean(*korean_inputs)


@pytest.fixture
def api(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_real_pair_maps_without_rewriting_text(korean_inputs, korean_result):
    original = extract_korean(*korean_inputs)
    result = korean_result
    assert AnalysisResult.model_validate_json(result.model_dump_json()) == result
    assert result.analysis_id.startswith("kr-")
    assert result.provider == "local"
    assert [claim.claim_number for claim in result.patent.claims] == [1]
    assert result.claim_summary.direct_rejected_claims == [1]
    assert result.claim_summary.dependency_impacted_claims == []
    assert [r.statute for r in result.rejections] == ["특허법 제29조제2항"]
    assert {c.publication_number for c in result.citations} == {
        "KR20150096573A",
        "KR20150090348A",
        "KR20150093093A",
    }
    assert [d.text for d in result.documents] == [d.text for d in original.documents]
    assert result.patent.claims[0].text == original.claims[0].text
    assert result.rejections[0].examiner_explanation == original.rejections[0].explanation
    assert len(result.rejection_citations) == 3
    assert len([node for node in result.graph.nodes if node.kind == "citation"]) == 3
    assert len([edge for edge in result.graph.edges if edge.relation == "cites"]) == 3


def test_evidence_offsets_and_logical_xml_page(korean_result):
    result = korean_result
    documents = {d.document_id: d for d in result.documents}
    sources = [c.evidence for c in result.patent.claims]
    sources += [r.evidence for r in result.rejections]
    sources += [c.evidence for c in result.citations]
    for evidence in sources:
        document = documents[evidence.document_id]
        assert document.text[evidence.start : evidence.end] == evidence.text
        assert evidence.page_numbers == [
            page.number
            for page in document.pages
            if page.start < evidence.end and page.end > evidence.start
        ]
    assert result.patent.claims[0].evidence.page_numbers == [3]
    assert result.rejections[0].evidence.page_numbers == [1]
    assert any("실제 OA PDF 페이지가 아닙니다" in warning for warning in result.warnings)
    assert not any(d.metadata.ocr_used for d in result.documents)


def test_existing_review_view_model_and_coordinates(korean_inputs, korean_result):
    result = korean_result.model_dump(mode="json")
    before = deepcopy(result)
    model = attach_coordinates(
        build_review_model(result),
        result,
        {result["documents"][0]["document_id"]: korean_inputs[0]},
    )
    assert {item["kind"] for item in model["items"]} == {
        "claim",
        "rejection",
        "citation",
        "specification",
    }
    assert all(
        "시스템 검색 후보" in item["title"]
        for item in model["items"]
        if item["kind"] == "specification"
    )
    assert len([item for item in model["items"] if item["kind"] == "citation"]) == 3
    annotations = model["annotations"]
    assert any(a["boxes"] and a["page"] == 3 for a in annotations if a["claim_number"] == 1)
    assert all(
        a["location_method"] == "text"
        for a in annotations
        if a["document_id"] == result["documents"][1]["document_id"]
    )
    rows, _ = claim_rows(result)
    assert len(rows) == 1
    assert result == before


def test_korean_multipart_api_uses_shared_contract(api, korean_inputs, korean_result):
    response = api.post(
        "/analyze/files?jurisdiction=KR",
        files={
            "patent": (korean_inputs[1], korean_inputs[0], "application/pdf"),
            "office_action": (korean_inputs[3], korean_inputs[2], "application/xml"),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json() == korean_result.model_dump(mode="json")


def test_us_default_and_explicit_routing_are_identical(api, patent_text, oa_text):
    payload = {"patent_text": patent_text, "office_action_text": oa_text}
    default = api.post("/analyze/text", json=payload)
    explicit = api.post("/analyze/text?jurisdiction=US", json=payload)
    assert default.status_code == explicit.status_code == 200
    assert default.json() == explicit.json()
    files = {"patent": ("patent.txt", patent_text), "office_action": ("oa.txt", oa_text)}
    default = api.post("/analyze/files", files=files)
    explicit = api.post("/analyze/files?jurisdiction=US", files=files)
    assert default.status_code == explicit.status_code == 200
    assert default.json() == explicit.json()


def test_korean_demo_and_dependency_without_cloud(api):
    payload = {
        "patent_text": (ROOT / "data/raw/kr_demo_patent.txt").read_text(encoding="utf-8"),
        "office_action_text": (ROOT / "data/raw/kr_demo_office_action.xml").read_text(
            encoding="utf-8"
        ),
    }
    with patch("backend.service.analyze", side_effect=AssertionError("US parser called")):
        response = api.post("/analyze/text?jurisdiction=KR", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["claim_summary"]["direct_rejected_claims"] == [1]
    assert result["claim_summary"]["dependency_impacted_claims"] == [2]
    assert result["patent"]["claims"][1]["depends_on"] == [1]


def test_invalid_korean_xml_is_clear_422_and_us_still_works(api, patent_text, oa_text):
    payload = {"patent_text": patent_text, "office_action_text": "<!DOCTYPE foo><bad/>"}
    response = api.post("/analyze/text?jurisdiction=KR", json=payload)
    assert response.status_code == 422
    assert "DTD" in response.json()["detail"]
    payload["office_action_text"] = oa_text
    assert api.post("/analyze/text", json=payload).status_code == 200
    assert api.post("/analyze/text?jurisdiction=JP", json=payload).status_code == 422


def test_korean_char_limit(api, settings):
    settings.max_document_chars = 20
    response = api.post(
        "/analyze/text?jurisdiction=KR",
        json={
            "patent_text": (ROOT / "data/raw/kr_demo_patent.txt").read_text(encoding="utf-8"),
            "office_action_text": (ROOT / "data/raw/kr_demo_office_action.xml").read_text(
                encoding="utf-8"
            ),
        },
    )
    assert response.status_code == 422
    assert "20자" in response.json()["detail"]


def test_same_four_screens_and_mode_state_isolation(korean_result, result):
    us = result.model_dump(mode="json")
    kr = korean_result.model_dump(mode="json")

    def response(url, **kwargs):
        return httpx.Response(200, json=kr if "jurisdiction=KR" in url else us)

    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post", side_effect=response) as post,
    ):
        ui = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=30).run()
        assert ui.radio(key="jurisdiction_selector").value == "미국 특허"
        ui.radio(key="jurisdiction_selector").set_value("한국 특허").run()
        assert [s.value for s in ui.subheader] == ["01 · 명세서·청구범위", "02 · 의견제출통지서"]
        ui.button(key="demo").click().run()
        assert post.call_args.args[0].endswith("?jurisdiction=KR")
        assert ui.session_state["result"] == kr
        assert ui.session_state["review_ui"]["selected"] is None
        assert ui.session_state["review_ui"]["expanded"] is None
        for screen in ["청구항 분석", "관계 지도", "근거 비교", "PDF 검토"]:
            ui.sidebar.radio[0].set_value(screen).run()
            assert not ui.exception
            assert ui.session_state["result"] == kr
            if screen == "청구항 분석":
                assert ui.text_input(key="claim_number_search").label == "청구항 번호 검색"
                assert "청구항 1 상세 보기" in [e.label for e in ui.expander]
                assert ui.radio(key="claim_status_filter").options == [
                    "전체",
                    "직접 지적",
                    "추가 검토",
                    "특허 가능",
                ]
                assert any(
                    'class="claim-detail-label citation">관련 인용문헌' in m.value
                    for m in ui.markdown
                )
                assert any(
                    "청구항 1:" in c.label and "의견제출통지서 근거" in c.label for c in ui.checkbox
                )
                for choice in ["직접 지적", "추가 검토", "허용", "전체"]:
                    ui.radio(key="claim_status_filter").set_value(choice).run()
                    assert not ui.exception
                    assert ui.session_state["result"] == kr
                assert [m.value for m in ui.metric] == ["1", "1", "1", "0", "0"]
            elif screen == "근거 비교":
                assert ui.selectbox(key="comparison_claim").options == ["청구항 1"]
                assert ui.button(key="comparison-oa-R1").label == "의견제출통지서에서 보기"
                assert any("특허문헌" in e.label for e in ui.expander)
                assert any("의견제출통지서 요약" in m.value for m in ui.markdown)
        ui.sidebar.radio[0].set_value("문서 업로드").run()
        assert ui.radio(key="jurisdiction_selector").value == "한국 특허"
        ui.radio(key="jurisdiction_selector").set_value("미국 특허").run()
        assert [s.value for s in ui.subheader] == ["01 · Patent / Claims", "02 · Office Action"]
        assert "result" not in ui.session_state
        assert "pdf_assets" not in ui.session_state
        ui.button(key="demo").click().run()
        assert ui.session_state["result"] == us
        assert not ui.session_state["review_model_id"].startswith("kr-")
        assert ui.session_state["review_ui"]["scope"] == "all"
        assert ui.session_state["review_ui"]["selected"] is None
        assert not ui.exception
