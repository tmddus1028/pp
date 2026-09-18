"""Previously unlisted API, utility, and failure-path behaviors."""

import asyncio
import json
import subprocess
import sys
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from conftest import ROOT
from fastapi import UploadFile
from fastapi.testclient import TestClient
from openai import APIConnectionError
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from backend.config import Settings
from backend.errors import ProviderError
from backend.llm.client import OpenAIExtractionClient
from backend.main import analyze_files, app, get_settings
from scripts import make_ocr_fixtures, make_review_fixtures


def test_api_docs_json_upload_and_text_limits(settings, patent_text, oa_text):
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            for path in ["/docs", "/redoc", "/openapi.json"]:
                assert client.get(path).status_code == 200
            assert set(client.get("/openapi.json").json()["paths"]) == {
                "/health",
                "/analyze/text",
                "/analyze/files",
                "/improvements",
                "/improvements/revisions",
            }
            response = client.post(
                "/analyze/files",
                files={
                    "patent": ("p.json", json.dumps({"pages": [{"text": patent_text}]})),
                    "office_action": ("oa.txt", oa_text),
                },
            )
            assert response.status_code == 200
            assert len(response.json()["patent"]["claims"]) == 9
            settings.max_document_chars = 1000
            response = client.post(
                "/analyze/text",
                json={"patent_text": patent_text * 10, "office_action_text": oa_text},
            )
            assert response.status_code == 422
            assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("bad format"),
        APIConnectionError(request=httpx.Request("POST", "https://example.test")),
    ],
)
def test_llm_transport_and_parse_failures_are_visible(error):
    client = OpenAIExtractionClient(
        Settings(_env_file=None, llm_provider="openai", openai_api_key="test", openai_model="test")
    )
    client.close()

    def fail(**kwargs):
        raise error

    client.client = SimpleNamespace(responses=SimpleNamespace(parse=fail))
    with pytest.raises(ProviderError):
        client.extract("untrusted source")


def test_fixture_generators_only_in_temporary_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(make_review_fixtures, "FIXTURES", tmp_path / "review")
    monkeypatch.setattr(make_ocr_fixtures, "FIXTURES", tmp_path / "ocr")
    make_review_fixtures.main()
    make_ocr_fixtures.make_fixtures()
    assert len(PdfReader(tmp_path / "review/patent.pdf").pages) == 2
    assert not PdfReader(tmp_path / "review/patent_scan.pdf").pages[0].extract_text()
    mixed = PdfReader(tmp_path / "ocr/office_action_mixed.pdf")
    assert mixed.pages[0].extract_text()
    assert not mixed.pages[1].extract_text()


def test_evaluation_cli(tmp_path, result):
    source = tmp_path / "analysis.json"
    source.write_text(result.model_dump_json(), encoding="utf-8")
    output = tmp_path / "metrics.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "backend.evaluation.evaluator",
            str(source),
            str(ROOT / "data/raw/demo_ground_truth.json"),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["rejected_claims"]["exact_match"] == 1


def test_multipart_closes_both_upload_streams(settings):
    patent = UploadFile(filename="p.txt", file=BytesIO(b"Claims\n1. A sensor."))
    oa = UploadFile(filename="oa.txt", file=BytesIO(b"Claim 1 is rejected under 35 USC 112."))
    asyncio.run(analyze_files(patent, oa, settings))
    assert patent.file.closed and oa.file.closed


@pytest.mark.parametrize(
    "outcome",
    [httpx.ConnectError("offline"), httpx.Response(422, json={"detail": "invalid source"})],
)
def test_failed_ui_analysis_keeps_previous_result(result, outcome):
    with (
        patch("httpx.get", side_effect=httpx.ConnectError("offline")),
        patch(
            "httpx.post",
            side_effect=outcome if isinstance(outcome, Exception) else None,
            return_value=outcome,
        ),
    ):
        app_test = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=15)
        payload = result.model_dump(mode="json")
        app_test.session_state["result"] = payload
        app_test.run()
        app_test.button(key="demo").click().run()
        assert not app_test.exception
        assert len(app_test.error) == 1
        assert app_test.session_state["result"] == payload
        assert app_test.session_state["section"] == "문서 업로드"
