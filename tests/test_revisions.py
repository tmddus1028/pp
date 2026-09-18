"""Revision workflow contracts. Model judgments are mocked, never labeled live LLM quality."""

from copy import deepcopy
from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.models import ImprovementRequest
from backend.improvements.providers import OllamaImprovementProvider, get_provider
from backend.improvements.retrieval import retrieved_context, specification_chunks
from backend.improvements.revision import claim_diff, review_revision, revision_elements, similarity
from backend.improvements.revision_models import RevisionAssessment, RevisionRequest
from backend.improvements.service import generate_improvement, local_review, provider_settings
from backend.ingestion.adapters import from_text
from backend.main import app, get_settings
from backend.service import analyze
from frontend.improvements import revisions_html

SETTINGS = Settings(
    _env_file=None,
    llm_provider="local",
    improvement_provider="local_ollama",
    local_llm_model="test-configured-model",
)
PATENT = "[0001] The device includes a sensor. The sensor records at 10 Hz using a controller.\n[0002] The housing protects the sensor from external pressure and water.\nClaims\n1. A device comprising a sensor.\n2. The device of claim 1 comprising a housing."


@pytest.fixture
def analysis():
    return sample()


def sample(law="103"):
    return analyze(
        from_text(PATENT, "patent.txt", "patent"),
        from_text(
            "Claim 1 is rejected under 35 USC "
            + law
            + " over Smith (US 2020/0123456 A1). The sensor limitation is disclosed by Smith. See specification [0001].",
            "oa.txt",
            "office_action",
        ),
        Settings(_env_file=None, llm_provider="local"),
    )


def req(analysis, text="A device comprising a sensor; the sensor records at 10 Hz."):
    return RevisionRequest(analysis=analysis, claim_number=1, rejection_id="R1", revised_text=text)


def mock_assessment(context, status="SUPPORTED"):
    sources = {s["evidence_id"]: s for s in context["sources"]}
    support = []
    for element in context["elements"]:
        ids = element["candidate_evidence_ids"][:1]
        support.append(
            {
                "element_id": element["element_id"],
                "status": status if ids else "NOT_FOUND",
                "evidence_ids": ids,
                "grounding": [
                    {"evidence_id": eid, "quote": sources[eid]["evidence"]["text"]} for eid in ids
                ],
                "reason": "TEST MOCK: provided sensor limitation compared against source.",
            }
        )
    return RevisionAssessment.model_validate(
        {
            "revision_summary": "TEST MOCK revision review",
            "specification_support": support,
            "rejection_response": [
                {
                    "rejection_id": r["rejection_id"],
                    "status": "INSUFFICIENT_EVIDENCE",
                    "reason": "TEST MOCK: prior art originals absent; OA reasoning only.",
                    "evidence_ids": [r["evidence_id"]],
                    "grounding": [
                        {
                            "evidence_id": r["evidence_id"],
                            "quote": sources[r["evidence_id"]]["evidence"]["text"][:350],
                        }
                    ],
                    "prior_art_assessment": "OA_ONLY",
                }
                for r in context["rejections"]
            ],
            "remaining_issues": ["TEST MOCK: human review needed"],
            "cautions": [],
        }
    )


def reviewer(status="SUPPORTED"):
    mock = Mock()
    mock.review_revision.side_effect = lambda context, schema, prompt: mock_assessment(
        context, status
    )
    return mock


def test_diff_is_lossless_and_deterministic():
    original, revised = "A red device; a sensor.", "A blue device; a sensor; a housing."
    changes = claim_diff(original, revised)
    assert "".join(c.original for c in changes) == original
    assert "".join(c.revised for c in changes) == revised
    assert changes == claim_diff(original, revised)
    assert {c.change_type for c in changes} >= {"unchanged", "changed", "added"}
    assert any(c.change_type == "removed" for c in claim_diff("a red device", "a device"))
    for e in revision_elements(revised, changes):
        assert revised[e.start : e.end] == e.element


def test_retrieval_excludes_claim_and_preserves_exact_positions(analysis):
    context, sources, _, choices, _ = retrieved_context(
        req(analysis), [("E1", "sensor records at 10 Hz")]
    )
    assert choices["E1"] and "documents" not in context
    doc = analysis.documents[0]
    for source in specification_chunks(analysis):
        e = source.evidence
        assert doc.text[e.start : e.end] == e.text
        assert all(
            e.end <= c.evidence.start or e.start >= c.evidence.end for c in analysis.patent.claims
        )
    assert len([s for s in sources if s.evidence_id.startswith("SPEC-RETRIEVED")]) <= 12


@pytest.mark.parametrize("law", ["103", "112"])
def test_revision_support_and_oa_scope_without_mutation(law):
    result = sample(law)
    before = result.model_dump_json()
    provider = reviewer()
    response = review_revision(req(result), SETTINGS, provider)
    assert response.provider == "local_ollama"
    assert all(s.status == "SUPPORTED" for s in response.assessment.specification_support)
    assert not response.new_matter_risks
    assert any("원문 미확보" in s for s in response.limitations)
    assert response.assessment.rejection_response[0].prior_art_assessment == "OA_ONLY"
    assert result.model_dump_json() == before
    assert provider.review_revision.call_args.args[0]["rejections"][0]["statute"].endswith(law)


def test_unsupported_addition_flags_possible_new_matter(analysis):
    response = review_revision(
        req(analysis, "A device comprising a sensor; temperature below 100°C."),
        SETTINGS,
        reviewer("NOT_FOUND"),
    )
    assert response.new_matter_risks
    assert all("가능성" in r and "신규사항입니다" not in r for r in response.new_matter_risks)
    assert response.similarity.method == "lexical_cosine"


def test_unfounded_numeric_supported_is_rejected(analysis):
    with pytest.raises(ProviderError, match="수치"):
        review_revision(
            req(analysis, "A device comprising a sensor; the sensor records at 100 Hz."),
            SETTINGS,
            reviewer(),
        )


@pytest.mark.parametrize("failure", ["id", "quote", "element", "scope", "paragraph", "guarantee"])
def test_revision_hallucinations_rejected(analysis, failure):
    provider = reviewer()

    def invalid(context, schema, prompt):
        draft = mock_assessment(context)
        if failure == "id":
            draft.specification_support[0].evidence_ids.append("SPEC-NONEXISTENT")
        elif failure == "quote":
            draft.specification_support[0].grounding[0].quote = "invented passage"
        elif failure == "element":
            draft.specification_support.pop()
        elif failure == "scope":
            draft.rejection_response[0].rejection_id = "R999"
        elif failure == "paragraph":
            draft.revision_summary = "See paragraph [9999]."
        else:
            draft.revision_summary = "등록 가능합니다."
        return draft

    provider.review_revision.side_effect = invalid
    with pytest.raises(ProviderError):
        review_revision(req(analysis), SETTINGS, provider)


def test_ollama_structured_success_uses_configured_model(analysis):
    request = ImprovementRequest(analysis=analysis, claim_number=1, require_llm=True)
    context, _, _, _, _ = retrieved_context(
        request, [("selected_claim", analysis.patent.claims[0].text)]
    )
    draft = local_review(context)
    response = httpx.Response(
        200,
        json={"done": True, "message": {"content": draft.model_dump_json()}},
        request=httpx.Request("POST", "http://127.0.0.1:11434/api/chat"),
    )
    with patch("backend.improvements.providers.httpx.post", return_value=response) as post:
        result = generate_improvement(request, SETTINGS)
    kwargs = post.call_args.kwargs
    assert kwargs["json"]["model"] == "test-configured-model"
    assert kwargs["json"]["stream"] is False
    assert kwargs["json"]["format"]["additionalProperties"] is False
    assert kwargs["trust_env"] is False
    assert result.provider == "local_ollama"


@pytest.mark.parametrize("failure", ["connection", "missing", "malformed", "length", "not_done"])
def test_ollama_failures_are_not_success(failure):
    provider = OllamaImprovementProvider(SETTINGS)
    response = httpx.Response(
        404 if failure == "missing" else 200,
        json={
            "done": failure != "not_done",
            "done_reason": "length" if failure == "length" else "stop",
            "message": {"content": "not json"},
        },
        request=httpx.Request("POST", "http://localhost"),
    )
    with (
        patch(
            "backend.improvements.providers.httpx.post",
            return_value=response,
            side_effect=httpx.ConnectError("offline") if failure == "connection" else None,
        ),
        pytest.raises(ProviderError),
    ):
        provider.review_revision({}, RevisionAssessment, "prompt")


def test_missing_model_and_nonlocal_host_fail_before_network():
    with patch("httpx.post") as network:
        for settings in [
            SETTINGS.model_copy(update={"local_llm_model": ""}),
            SETTINGS.model_copy(update={"local_llm_base_url": "https://example.com"}),
        ]:
            with pytest.raises(ProviderError):
                OllamaImprovementProvider(settings).review_revision(
                    {}, RevisionAssessment, "prompt"
                )
        network.assert_not_called()


def test_rule_mode_ai_request_requires_llm(analysis):
    with pytest.raises(ProviderError, match="설정"):
        generate_improvement(
            ImprovementRequest(analysis=analysis, claim_number=1, require_llm=True),
            Settings(_env_file=None, improvement_provider="local"),
        )
    with pytest.raises(ProviderError):
        get_provider(Settings(_env_file=None, llm_provider="local"))


def test_kr_ollama_does_not_switch_to_azure(monkeypatch):
    monkeypatch.setenv("KR_AZURE_OPENAI_ENDPOINT", "https://kr.invalid")
    assert provider_settings(SETTINGS, "kr").llm_provider == "local_ollama"


def test_real_kr_revision_candidates_and_scope():
    from conftest import ROOT

    from backend.schemas import AnalysisResult

    path = ROOT / "data/outputs/improvements/golden/kr-analysis.json"
    if not path.exists():
        pytest.skip("Real Korean fixture analysis not present")
    analysis = AnalysisResult.model_validate_json(path.read_text(encoding="utf-8"))
    provider = reviewer("UNCERTAIN")
    response = review_revision(req(analysis, analysis.patent.claims[0].text), SETTINGS, provider)
    context = provider.review_revision.call_args.args[0]
    assert context["jurisdiction"] == "kr"
    assert context["rejections"][0]["statute"] == "특허법 제29조제2항"
    assert len(context["citations"]) == 3
    assert any(s.evidence_id.startswith("SPEC-RETRIEVED") for s in response.sources)
    assert all(c.change_type == "unchanged" for c in response.claim_changes)


def test_embedding_scores_are_separate_and_failure_is_disclosed(analysis):
    request = req(analysis)
    elements = revision_elements(
        request.revised_text, claim_diff(analysis.patent.claims[0].text, request.revised_text)
    )
    _, sources, _, choices, _ = retrieved_context(
        request, [(e.element_id, e.element) for e in elements]
    )
    for e in elements:
        e.candidate_evidence_ids = choices[e.element_id]
    config = SETTINGS.model_copy(update={"local_embedding_model": "test-embedding"})

    def embed(*args, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("POST", "http://localhost"),
            json={"embeddings": [[1.0, 0.0] for _ in kwargs["json"]["input"]]},
        )

    with patch("backend.improvements.revision.httpx.post", side_effect=embed):
        result = similarity(
            config, analysis.patent.claims[0].text, request.revised_text, elements, sources
        )
        assert result.original_claim == 1 and result.method.startswith("local_embedding")
    with patch(
        "backend.improvements.revision.httpx.post", side_effect=httpx.ConnectError("offline")
    ):
        result = similarity(config, "original", "revised", elements, sources)
        assert "실패" in result.note and result.method == "lexical_cosine"


def test_revision_api_and_provider_failure_preserve_analysis(analysis):
    app.dependency_overrides[get_settings] = lambda: SETTINGS
    try:
        with (
            TestClient(app) as api,
            patch("backend.improvements.revision.get_provider", return_value=reviewer()),
        ):
            response = api.post(
                "/improvements/revisions", json=req(analysis).model_dump(mode="json")
            )
            assert response.status_code == 200, response.text
        with (
            TestClient(app) as api,
            patch(
                "backend.improvements.revision.get_provider",
                side_effect=ProviderError("로컬 LLM에 연결할 수 없습니다."),
            ),
        ):
            assert (
                api.post(
                    "/improvements/revisions", json=req(analysis).model_dump(mode="json")
                ).status_code
                == 502
            )
            assert api.get("health").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_revision_session_click_cache_history_and_document_reset(analysis):
    from conftest import ROOT

    data = analysis.model_dump(mode="json")
    with (
        patch("httpx.get", return_value=httpx.Response(200, json={"provider": "local"})),
        patch("httpx.post") as post,
    ):
        post.return_value = httpx.Response(200, json=data)
        ui = AppTest.from_file(ROOT / "frontend/app.py", default_timeout=30).run()
        ui.button(key="demo").click().run()
        ui.sidebar.radio[0].set_value("청구항 분석").run()
        ui.button(key="improve-" + analysis.analysis_id + "-1:all").click().run()
        assert post.call_count == 1  # opening does not invoke an LLM
        for index in range(1, 5):
            text = f"A device comprising a sensor; added unverified feature {index}."
            request = req(analysis, text).model_copy(update={"rejection_id": None})
            review = review_revision(request, SETTINGS, reviewer("UNCERTAIN"))
            post.return_value = httpx.Response(200, json=review.model_dump(mode="json"))
            ui.text_area(key="revision-input-1:all").set_value(text).run()
            ui.button(key="validate-1:all").click().run()
        assert post.call_count == 5
        history = ui.session_state["revision_results"]["1:all"]
        assert len(history) == 3 and [h["session_order"] for h in history] == [2, 3, 4]
        ui.button(key="validate-1:all").click().run()
        assert post.call_count == 5 and ui.session_state["result"] == data
        assert (
            post.call_args.kwargs["json"]["parent_revision_id"]
            == history[-2]["revision"]["revision_id"]
        )
        changed = deepcopy(data)
        changed["analysis_id"] += "-new"
        ui.session_state["result"] = changed
        ui.run()
        assert ui.session_state["revision_results"] == {}
        assert ui.session_state["revision_drafts"] == {}
        assert not ui.exception


def test_revision_html_escapes_content(analysis):
    response = review_revision(req(analysis), SETTINGS, reviewer()).model_dump(mode="json")
    response["assessment"]["revision_summary"] = "<script>alert(1)</script>"
    html = revisions_html([response])
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "명세서 근거" in html and "유사도" in html and "법적" in html


def test_quantities_cannot_be_laundered_through_valid_source_id():
    from backend.improvements.grounding import verify_quantities

    verify_quantities("record at 10 Hz", "A sensor", "The sensor records at 10 Hz.")
    for proposed in ("record at 100 Hz", "temperature below 100°C", "record at 10-100 Hz"):
        with pytest.raises(ValueError, match="수치"):
            verify_quantities(proposed, "A sensor", "The sensor records at 10 Hz.")
