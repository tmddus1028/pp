"""UI state checks; analysis and remote provider calls are deliberately stubbed."""

import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from kr_review.models import AnalysisResult, Claim, Document, Evidence, Page, Rejection, ReviewError

APP = Path(__file__).resolve().parents[1] / "app.py"
PATENT_ID = "patent_" + hashlib.sha256(b"patent").hexdigest()[:16]
OA_ID = "office_action_" + hashlib.sha256(b"oa").hexdigest()[:16]


def picker(app, name):
    return next(item for item in app.selectbox if item.key.startswith(name + "__"))


def analysis_result():
    claim_text = "전자쿠폰 관리 장치를 포함하는 전자쿠폰 시스템."
    oa_text = "청구항 제1항은 특허법 제29조제2항에 따라 특허를 받을 수 없습니다."
    claim_evidence = Evidence(document_id=PATENT_ID, text=claim_text, start=0, end=len(claim_text))
    oa_evidence = Evidence(
        document_id=OA_ID, text=oa_text, start=0, end=len(oa_text), xml_path="/RejectionLawDetail"
    )
    return AnalysisResult(
        application_number="10-2019-0000844",
        title="전자쿠폰 시스템",
        documents=[
            Document(document_id=PATENT_ID, filename="patent.txt", kind="patent", text=claim_text),
            Document(document_id=OA_ID, filename="oa.xml", kind="office_action", text=oa_text),
        ],
        claims=[
            Claim(number=1, text=claim_text, evidence=claim_evidence),
            Claim(number=2, text=claim_text, depends_on=[1], evidence=claim_evidence),
        ],
        rejections=[
            Rejection(
                rejection_id="R1",
                claims=[1],
                statute="특허법 제29조제2항",
                explanation=oa_text,
                evidence=oa_evidence,
            )
        ],
        citations=[],
        direct_claims=[1],
        dependency_claims=[2],
    )


def loaded_app():
    app = AppTest.from_file(str(APP), default_timeout=20)
    app.session_state["kr_result"] = analysis_result()
    app.session_state["kr_files"] = {PATENT_ID: b"patent", OA_ID: b"oa"}
    return app.run()


def test_first_entry_has_no_selected_claim_or_source():
    app = loaded_app()
    assert not app.exception
    assert picker(app, "kr_claim_selection").value is None
    assert picker(app, "kr_source_document").value is None
    assert [metric.value for metric in app.metric] == ["2", "1", "1", "0"]
    assert all(not item.proto.expanded for item in app.expander)
    assert not any(button.label == "Azure로 검토" for button in app.button)


def test_oa_source_navigation_preserves_claim_and_summary():
    app = loaded_app()
    picker(app, "kr_claim_selection").select(1).run()
    assert not app.exception
    app.button(key="kr_claim_rejection_1_R1").click().run()
    assert not app.exception
    assert picker(app, "kr_claim_selection").value == 1
    assert picker(app, "kr_source_document").value == OA_ID
    assert [metric.value for metric in app.metric] == ["2", "1", "1", "0"]
    assert any("/RejectionLawDetail" in caption.value for caption in app.caption)
    assert all(
        "더 보기" not in button.label and "접기" not in button.label for button in app.button
    )


def test_new_analysis_resets_selection_source_and_azure_results(monkeypatch):
    import sys

    result = analysis_result()
    analyze = Mock(return_value=result)
    monkeypatch.setitem(sys.modules, "kr_review.service", SimpleNamespace(analyze=analyze))
    monkeypatch.setitem(
        sys.modules,
        "kr_review.sample",
        SimpleNamespace(
            sample_inputs=lambda: {
                "patent_data": b"patent",
                "patent_filename": "patent.txt",
                "oa_data": b"oa",
                "oa_filename": "oa.xml",
                "references": [],
            }
        ),
    )
    app = loaded_app()
    picker(app, "kr_claim_selection").select(1).run()
    app.button(key="kr_claim_rejection_1_R1").click().run()
    app.session_state["kr_azure_results"] = {1: {"findings": []}}
    next(button for button in app.button if button.label == "한국 사례 분석").click().run()
    assert not app.exception
    analyze.assert_called_once()
    assert picker(app, "kr_claim_selection").value is None
    assert picker(app, "kr_source_document").value is None
    assert "kr_azure_results" not in app.session_state

    # Repeated analyses with identical options must create usable new selectors.
    previous_key = picker(app, "kr_claim_selection").key
    for _ in range(2):
        picker(app, "kr_claim_selection").select(1).run()
        assert not app.exception
        assert picker(app, "kr_claim_selection").value == 1
        assert any(item.value == "청구항 1 · 직접 지적" for item in app.subheader)
        assert any(item.value == result.claims[0].text for item in app.text)
        app.button(key="kr_claim_rejection_1_R1").click().run()
        assert picker(app, "kr_source_document").value == OA_ID
        next(button for button in app.button if button.label == "한국 사례 분석").click().run()
        assert not app.exception
        current_key = picker(app, "kr_claim_selection").key
        assert current_key != previous_key
        assert picker(app, "kr_claim_selection").value is None
        assert picker(app, "kr_source_document").value is None
        previous_key = current_key


def test_azure_only_runs_on_request_and_reports_configuration_failure(monkeypatch):
    import sys

    review = Mock(side_effect=ReviewError("Azure 설정이 필요합니다."))
    monkeypatch.setitem(sys.modules, "kr_review.review", SimpleNamespace(analyze_with_azure=review))
    app = loaded_app()
    picker(app, "kr_claim_selection").select(1).run()
    review.assert_not_called()
    app.button(key="kr_azure_run").click().run()
    assert not app.exception
    review.assert_called_once()
    assert any("Azure 설정이 필요합니다." in item.value for item in app.error)
    assert picker(app, "kr_claim_selection").value == 1
    assert [metric.value for metric in app.metric] == ["2", "1", "1", "0"]
    assert "kr_azure_results" not in app.session_state


def test_same_filename_sources_keep_distinct_bytes_and_render_correct_document(monkeypatch):
    import sys
    from io import BytesIO

    from PIL import Image

    import app as ui

    inputs = [
        ("patent", b"patent"),
        ("reference", b"reference one"),
        ("reference", b"reference two"),
    ]
    pdf_documents = [
        Document(
            document_id=f"{kind}_{hashlib.sha256(data).hexdigest()[:16]}",
            filename="same.pdf",
            kind=kind,
            text="source text",
            pages=[Page(number=1, text="source text", start=0, end=11)],
        )
        for kind, data in inputs
    ]
    result = analysis_result()
    result.documents = [*pdf_documents, result.documents[1]]
    monkeypatch.setitem(
        sys.modules, "kr_review.service", SimpleNamespace(analyze=Mock(return_value=result))
    )
    monkeypatch.setitem(
        sys.modules,
        "kr_review.sample",
        SimpleNamespace(
            sample_inputs=lambda: {
                "patent_data": inputs[0][1],
                "patent_filename": "same.pdf",
                "oa_data": b"oa",
                "oa_filename": "oa.xml",
                "references": [("same.pdf", data) for _, data in inputs[1:]],
            }
        ),
    )
    image_data = BytesIO()
    Image.new("RGB", (10, 10), "white").save(image_data, format="PNG")
    renderer = Mock(return_value=image_data.getvalue())
    monkeypatch.setattr(ui, "render_pdf_page", renderer)
    app = AppTest.from_string("from app import main\nmain()", default_timeout=20).run()
    next(button for button in app.button if button.label == "한국 사례 분석").click().run()
    assert not app.exception
    assert len(app.session_state["kr_files"]) == 4
    options = picker(app, "kr_source_document").options
    assert len(options) == len(set(options))
    for document, (_, expected_bytes) in zip(pdf_documents, inputs, strict=True):
        assert app.session_state["kr_files"][document.document_id] == expected_bytes
        renderer.reset_mock()
        picker(app, "kr_source_document").select(document.document_id).run()
        assert not app.exception
        renderer.assert_called_once_with(expected_bytes, 1)
