"""Qwen transport contracts with HTTP doubles, not live model quality tests."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.models import ClaimImprovementSuggestion, ImprovementRequest
from backend.improvements.providers import QwenImprovementProvider, get_provider
from backend.improvements.service import generate_improvement, local_review, provider_settings
from backend.jurisdictions.korean import analyze_korean
from backend.main import app, get_settings
from tests.test_revisions import mock_assessment, sample


@pytest.fixture
def config():
    return Settings(
        _env_file=None,
        llm_provider="local",
        improvement_provider="qwen",
        qwen_api_key="TEST-ONLY-KEY",
        qwen_base_url="https://example.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        qwen_model="configured-test-model",
    )


def reply(body, code=200):
    return httpx.Response(code, json=body, request=httpx.Request("POST", "https://example.test"))


def completion(draft):
    return reply(
        {"choices": [{"finish_reason": "stop", "message": {"content": draft.model_dump_json()}}]}
    )


def fake_post(_url, **kwargs):
    context = json.loads(kwargs["json"]["messages"][1]["content"])
    if "elements" in context:
        return completion(mock_assessment(context, status="UNCERTAIN"))
    return completion(local_review(context))


@pytest.mark.parametrize("jurisdiction", ["us", "kr"])
def test_explicit_qwen_is_not_overridden_by_kr_azure(config, monkeypatch, jurisdiction):
    monkeypatch.setenv("KR_AZURE_OPENAI_ENDPOINT", "https://unused.example.com")
    monkeypatch.setenv("KR_AZURE_OPENAI_API_KEY", "unused")
    monkeypatch.setenv("KR_AZURE_OPENAI_DEPLOYMENT", "unused")
    selected = provider_settings(config, jurisdiction)
    assert selected.llm_provider == "qwen"
    assert config.llm_provider == "local"
    assert isinstance(get_provider(selected), QwenImprovementProvider)
    assert "TEST-ONLY-KEY" not in repr(selected)


@pytest.mark.parametrize("jurisdiction", ["us", "kr"])
def test_improvement_and_revision_endpoints_preserve_analysis(config, jurisdiction):
    if jurisdiction == "kr":
        folder = Path(__file__).resolve().parents[1] / "korean_prototype/data/kr_1020190000844"
        result = analyze_korean(
            (folder / "KR20190025857A.pdf").read_bytes(),
            "patent.pdf",
            (folder / "office_action_20190409.xml").read_bytes(),
            "oa.xml",
        )
    else:
        result = sample()
    original = result.model_dump_json()
    payload = ImprovementRequest(
        analysis=result, claim_number=1, rejection_id="R1", require_llm=True
    ).model_dump(mode="json")
    app.dependency_overrides[get_settings] = lambda: config
    try:
        with (
            TestClient(app) as client,
            patch("backend.improvements.providers.httpx.post", side_effect=fake_post) as post,
        ):
            first = client.post("/improvements", json=payload)
            assert first.status_code == 200, first.text
            revised = deepcopy(payload)
            revised["revised_text"] = result.patent.claims[0].text
            second = client.post("/improvements/revisions", json=revised)
            assert second.status_code == 200, second.text
            assert first.json()["provider"] == second.json()["provider"] == "qwen"
            assert post.call_count == 2
            args, kwargs = post.call_args
            assert args[0].endswith("/compatible-mode/v1/chat/completions")
            assert kwargs["headers"]["Authorization"] == "Bearer TEST-ONLY-KEY"
            assert kwargs["json"]["model"] == "configured-test-model"
            assert kwargs["json"]["response_format"]["json_schema"]["strict"] is True
            assert kwargs["follow_redirects"] is False
            context = json.loads(kwargs["json"]["messages"][1]["content"])
            assert "documents" not in context
            assert context["jurisdiction"] == jurisdiction
            assert all(s["evidence"]["text"] for s in context["sources"])
    finally:
        app.dependency_overrides.clear()
    assert result.model_dump_json() == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("qwen_api_key", ""),
        ("qwen_model", ""),
        ("qwen_base_url", ""),
        ("qwen_base_url", "http://example.com/compatible-mode/v1"),
        ("qwen_base_url", "https://user:pass@example.com/compatible-mode/v1"),
        ("qwen_base_url", "https://example.com/compatible-mode/v1?key=secret"),
    ],
)
def test_missing_or_invalid_configuration_never_calls_network(config, field, value):
    setattr(config, field, value)
    with patch("backend.improvements.providers.httpx.post") as post, pytest.raises(ProviderError):
        QwenImprovementProvider(config).complete({}, ClaimImprovementSuggestion, "test")
    post.assert_not_called()


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 500, 302])
def test_http_failure_does_not_expose_response_or_key(config, code):
    with patch(
        "backend.improvements.providers.httpx.post",
        return_value=reply({"secret": "TEST-ONLY-KEY"}, code),
    ) as post:
        with pytest.raises(ProviderError) as error:
            QwenImprovementProvider(config).complete({}, ClaimImprovementSuggestion, "test")
    assert "TEST-ONLY-KEY" not in str(error.value)
    assert post.call_count == 1


@pytest.mark.parametrize(
    "body",
    [
        {},
        [],
        {"choices": []},
        {"choices": [None]},
        {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
        {
            "choices": [
                {"finish_reason": "stop", "message": {"refusal": "refused", "content": "{}"}}
            ]
        },
        {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]},
    ],
)
def test_invalid_or_incomplete_response_rejected(config, body):
    with (
        patch("backend.improvements.providers.httpx.post", return_value=reply(body)),
        pytest.raises(ProviderError),
    ):
        QwenImprovementProvider(config).complete({}, ClaimImprovementSuggestion, "test")


def test_timeout_is_reported(config):
    with (
        patch("backend.improvements.providers.httpx.post", side_effect=httpx.ReadTimeout("secret")),
        pytest.raises(ProviderError, match="응답 시간"),
    ):
        QwenImprovementProvider(config).complete({}, ClaimImprovementSuggestion, "test")


def test_qwen_cannot_bypass_evidence_validation(config):
    def invented_source(url, **kwargs):
        context = json.loads(kwargs["json"]["messages"][1]["content"])
        draft = local_review(context)
        draft.strategies[0].grounding[0].evidence_id = "FABRICATED"
        return completion(draft)

    with (
        patch("backend.improvements.providers.httpx.post", side_effect=invented_source),
        pytest.raises(ProviderError, match="근거 검증"),
    ):
        generate_improvement(
            ImprovementRequest(analysis=sample(), claim_number=1, require_llm=True), config
        )
