"""Read-only improvement context, structured generation and UI isolation."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from conftest import ROOT
from fastapi.testclient import TestClient
from openai import APIConnectionError
from streamlit.testing.v1 import AppTest

from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.context import build_context
from backend.improvements.models import ImprovementRequest
from backend.improvements.service import (
    generate_improvement,
    local_review,
    provider_settings,
    validate_suggestion,
)
from backend.ingestion.adapters import from_text
from backend.jurisdictions.korean import analyze_korean
from backend.main import app, get_settings
from backend.schemas import AnalysisResult
from backend.service import analyze
from frontend.improvements import improvement_html


@pytest.fixture
def local():
    return Settings(_env_file=None, llm_provider="local", improvement_provider="local")


@pytest.fixture(scope="module")
def pair1():
    return golden(1)


def golden(number):
    path = ROOT / f"data/outputs/audit-20260916/final-golden/pair-{number}.json"
    if not path.exists():
        pytest.skip("User-supplied golden analysis is unavailable; synthetic tests still run")
    return AnalysisResult.model_validate_json(path.read_text(encoding="utf-8"))


def request(result, claim=1, rid=None):
    return ImprovementRequest(analysis=result, claim_number=claim, rejection_id=rid)


def provider(draft=None, error=None):
    client = Mock()
    client.model = "test-deployment"
    client.client.responses.parse.return_value = SimpleNamespace(
        status="completed", output_parsed=draft
    )
    client.client.responses.parse.side_effect = error
    return client


def cloud():
    return Settings(_env_file=None, llm_provider="local", improvement_provider="openai")


def test_us_real_112_and_103_are_separate_and_no_result_mutation(pair1, local):
    before = pair1.model_dump_json()
    r1 = generate_improvement(request(pair1, rid="R1"), local)
    r2 = generate_improvement(request(pair1, rid="R2"), local)
    assert r1.evidence_hash != r2.evidence_hash
    assert "112" in r1.suggestion.issue_summary and "103" in r2.suggestion.issue_summary
    assert r1.suggestion.strategies != r2.suggestion.strategies
    assert len([s for s in r2.sources if s.kind == "citation_mention"]) == 5
    assert all(s.kind != "citation_original" for s in r2.sources)
    assert any("선행문헌 원문 미확보" in m for m in r2.suggestion.missing_evidence)
    assert pair1.model_dump_json() == before


def test_dependent_claim_all_ancestors_and_rewrite_only_when_examiner_explicit(local):
    result = golden(3)
    for number in (15, 16):
        context, _, _ = build_context(request(result, number, "R6"))
        assert context["conditional_rewrite_supported"]
        assert context["parents"]
        response = generate_improvement(request(result, number, "R6"), local)
        assert any(s.action_type == "dependency_rewrite" for s in response.suggestion.strategies)
    context, _, _ = build_context(request(result, 1, "R1"))
    assert not context["conditional_rewrite_supported"]
    draft = local_review(context)
    draft.strategies[0].action_type = "dependency_rewrite"
    with pytest.raises(ValueError, match="독립항"):
        validate_suggestion(draft, context)


def test_korean_real_context_law_and_retrieved_specification(local):
    data = ROOT / "korean_prototype/data/kr_1020190000844"
    result = analyze_korean(
        (data / "KR20190025857A.pdf").read_bytes(),
        "patent.pdf",
        (data / "office_action_20190409.xml").read_bytes(),
        "oa.xml",
    )
    response = generate_improvement(request(result, rid="R1"), local)
    assert response.suggestion.jurisdiction == "kr"
    assert response.suggestion.rejection_basis[0].statute == "특허법 제29조제2항"
    assert len([s for s in response.sources if s.kind == "citation_mention"]) == 3
    assert any(
        s.kind == "specification" and "시스템 검색 후보" in s.label for s in response.sources
    )
    assert any("선행문헌 원문 미확보" in m for m in response.suggestion.missing_evidence)
    assert all(s.action_type == "argument_only" for s in response.suggestion.strategies)


def test_api_request_is_read_only_and_local_has_no_cloud_calls(result, local):
    app.dependency_overrides[get_settings] = lambda: local
    before = result.model_dump_json()
    try:
        with patch("backend.llm.client.OpenAI") as network, TestClient(app) as api:
            response = api.post(
                "/improvements", json=request(result, rid="R1").model_dump(mode="json")
            )
            assert response.status_code == 200, response.text
            assert response.json()["provider"] == "local"
            assert response.json()["status"] == "limited"
            network.assert_not_called()
        assert result.model_dump_json() == before
    finally:
        app.dependency_overrides.clear()


def test_structured_request_sends_only_relevant_context_and_closes_client(result):
    req = request(result, rid="R1")
    context, _, _ = build_context(req)
    mock = provider(local_review(context))
    response = generate_improvement(req, cloud(), lambda _: mock)
    kwargs = mock.client.responses.parse.call_args.kwargs
    assert kwargs["text_format"].__name__ == "ClaimImprovementSuggestion"
    assert kwargs["store"] is False
    payload = json.loads(kwargs["input"][1]["content"])
    assert "documents" not in payload and "analysis" not in payload
    assert {r["rejection_id"] for r in payload["rejections"]} == {"R1"}
    assert all(s["kind"] != "claim" or s["evidence_id"] == "CLAIM-1" for s in payload["sources"])
    assert response.provider == "openai"
    mock.close.assert_called_once()


@pytest.mark.parametrize(
    "failure", ["id", "quote", "element", "statute", "scope", "claim", "new_matter", "example"]
)
def test_invalid_model_output_is_never_displayed_as_valid_evidence(result, failure):
    req = request(result, rid="R1")
    context, _, _ = build_context(req)
    draft = local_review(context)
    if failure == "id":
        draft.strategies[0].evidence_ids.append("SPEC-INVENTED")
    elif failure == "quote":
        draft.strategies[0].grounding[0].quote = "Invented source quote"
    elif failure == "element":
        draft.strategies[0].target_elements = ["new quantum limitation"]
    elif failure == "statute":
        draft.rejection_basis[0].statute = "unknown law"
    elif failure == "scope":
        draft.rejection_basis[0].rejection_id = "R999"
    elif failure == "claim":
        draft.claim_number = 999
    elif failure == "example":
        draft.optional_example.available = True
        draft.optional_example.text = "A new amended claim"
        draft.optional_example.evidence_ids = draft.strategies[0].evidence_ids
    else:
        draft.strategies[0].action_type = "add_limitation"
    with pytest.raises(ProviderError):
        generate_improvement(req, cloud(), lambda _: provider(draft))


def test_provider_failure_refusal_and_abstention(result):
    req = request(result, rid="R1")
    failed = provider(
        error=APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))
    )
    with pytest.raises(ProviderError):
        generate_improvement(req, cloud(), lambda _: failed)
    failed.close.assert_called_once()
    with pytest.raises(ProviderError):
        generate_improvement(req, cloud(), lambda _: provider())
    context, _, _ = build_context(req)
    draft = local_review(context)
    draft.strategies = []
    draft.missing_evidence = ["현재 확보된 근거만으로는 안전한 수정안을 제시하기 어렵습니다."]
    assert generate_improvement(req, cloud(), lambda _: provider(draft)).status == "abstained"


def test_tampered_evidence_oversize_context_invalid_scope(result):
    bad = result.model_copy(deep=True)
    bad.patent.claims[0].evidence.text = "modified"
    with pytest.raises(ValueError, match="원문 위치"):
        build_context(request(bad))
    with pytest.raises(ValueError, match="연결된"):
        build_context(request(result, rid="R999"))
    with (
        patch("backend.improvements.context.MAX_CONTEXT_CHARS", 10),
        pytest.raises(ValueError, match="한도"),
    ):
        build_context(request(result))


def test_grounded_amendment_requires_existing_spec_and_exact_quote(local):
    result = analyze(
        from_text(
            "[0034] The sensor records at 10 Hz.\nClaims\n1. A device comprising a sensor.",
            "p.txt",
            "patent",
        ),
        from_text(
            "Claim 1 is rejected under 35 USC 103 over Smith (US 2020/0123456 A1). See specification [0034].",
            "oa.txt",
            "office_action",
        ),
        local,
    )
    req = request(result, rid="R1")
    context, sources, _ = build_context(req)
    specification = next(s for s in sources if s.kind == "specification")
    draft = local_review(context)
    strategy = draft.strategies[0]
    strategy.action_type = "narrow"
    strategy.description = "명세서의 10 Hz 조건으로 한정하는 방향을 검토할 수 있습니다. 선행문헌과의 차이는 미확인입니다."
    strategy.evidence_ids.append(specification.evidence_id)
    from backend.improvements.models import Grounding

    strategy.grounding.append(
        Grounding(evidence_id=specification.evidence_id, quote="The sensor records at 10 Hz.")
    )
    response = generate_improvement(req, cloud(), lambda _: provider(draft))
    assert response.suggestion.strategies[0].action_type == "narrow"
    assert "현재 자동 연결된 명세서 근거가 없어" not in " ".join(
        response.suggestion.missing_evidence
    )
    strategy.grounding[-1].quote = "The sensor records at 100 Hz."
    with pytest.raises(ProviderError, match="근거 검증"):
        generate_improvement(req, cloud(), lambda _: provider(draft))


@pytest.mark.parametrize(
    "reason, expected",
    [
        ("written description", "기재 뒷받침"),
        ("indefinite for lack of antecedent basis", "명확성"),
        ("enablement", "실시가능성"),
        ("see detailed remarks", "유형 미확인"),
    ],
)
def test_112_subtypes_require_explicit_oa_wording(local, reason, expected):
    result = analyze(
        from_text("Claims\n1. A device comprising a sensor.", "p.txt", "patent"),
        from_text("Claim 1 is rejected under 35 USC 112: " + reason, "oa.txt", "office_action"),
        local,
    )
    response = generate_improvement(request(result), local)
    assert expected in response.suggestion.strategies[0].title


def test_conditional_flag_alone_does_not_authorize_rewrite(local):
    result = golden(3).model_copy(deep=True)
    source = next(s for s in result.claim_statuses if s.claim_number == 15)
    # An original, valid source span without the conditional statement.
    source.evidence.end = source.evidence.start + len("Claims")
    source.evidence.text = "Claims"
    response = generate_improvement(request(result, 15, "R6"), local)
    assert response.status == "abstained"
    assert not response.suggestion.strategies


def test_provider_failure_api_keeps_health_and_analysis_available(result, local):
    app.dependency_overrides[get_settings] = lambda: local
    try:
        with (
            TestClient(app) as api,
            patch(
                "backend.main.generate_improvement",
                side_effect=ProviderError("provider unavailable"),
            ),
        ):
            assert (
                api.post("/improvements", json=request(result).model_dump(mode="json")).status_code
                == 502
            )
            assert api.get("/health").json()["status"] == "ok"
    finally:
        app.dependency_overrides.clear()


def test_kr_configuration_isolated_from_us_and_partial_keys_fail(monkeypatch, local):
    for key, value in {
        "ENDPOINT": "https://kr.example.invalid",
        "API_KEY": "test-only",
        "DEPLOYMENT": "kr-deployment",
    }.items():
        monkeypatch.setenv("KR_AZURE_OPENAI_" + key, value)
    # Pin the inherit default: a developer .env selecting a provider must not change this check.
    base = Settings(_env_file=None, llm_provider="local", improvement_provider="inherit")
    assert provider_settings(base, "us").llm_provider == "local"
    assert provider_settings(base, "kr").azure_openai_deployment == "kr-deployment"
    assert provider_settings(local, "kr").llm_provider == "local"
    monkeypatch.setenv("KR_AZURE_OPENAI_API_KEY", "")
    with pytest.raises(ProviderError):
        provider_settings(base, "kr")


def test_shared_render_escapes_output_and_keeps_amendment_separate(result, local):
    review = generate_improvement(request(result, rid="R1"), local).model_dump(mode="json")
    review["suggestion"]["issue_summary"] = "<script>bad()</script>"
    html = improvement_html(review)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "수정 방향" in html and "검토 가능한 반박 논점" in html
    assert "선행문헌 원문 미확보" in html


def test_explicit_click_cache_and_analysis_change_reset(result, local):
    data = result.model_dump(mode="json")
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post") as post,
    ):
        post.return_value = httpx.Response(200, json=data)
        ui = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=30).run()
        ui.button(key="demo").click().run()
        ui.sidebar.radio[0].set_value("청구항 분석").run()
        assert post.call_count == 1  # Only initial analysis; opening details never calls LLM.
        response = generate_improvement(request(result), local).model_dump(mode="json")
        post.return_value = httpx.Response(200, json=response)
        button = "improve-" + result.analysis_id + "-1:all"
        ui.button(key=button).click().run()
        assert post.call_count == 1  # opening the workflow no longer generates a review
        ui.button(key="generate-1:all").click().run()
        assert post.call_count == 2
        assert ui.session_state["result"] == data
        assert any(e.label == "개선 방안" for e in ui.expander)
        ui.button(key="generate-1:all").click().run()
        assert post.call_count == 2
        changed = deepcopy(data)
        changed["analysis_id"] += "-another-case"
        ui.session_state["result"] = changed
        ui.run()
        assert ui.session_state["improvement_results"] == {}
        assert not ui.exception
