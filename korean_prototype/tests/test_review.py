import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, OpenAI

from kr_review import review
from kr_review.models import (
    AnalysisResult,
    Citation,
    Claim,
    Document,
    Evidence,
    Page,
    Rejection,
    ReviewError,
)


def evidence(document, text, **kwargs):
    start = document.text.index(text)
    return Evidence(
        document_id=document.document_id, text=text, start=start, end=start + len(text), **kwargs
    )


@pytest.fixture
def analysis():
    claim_text = "쿠폰을 관리하고 공급자 위치를 제공하는 전자쿠폰 시스템."
    patent_text = f"청구항 1\n{claim_text}\n\n[0001] 쿠폰 관리부는 공급자 위치를 저장한다.\n[0002] 쿠폰 발행 정보를 저장한다."
    patent = Document(
        document_id="P",
        filename="patent.pdf",
        kind="patent",
        text=patent_text,
        pages=[Page(number=1, text=patent_text, start=0, end=len(patent_text))],
    )
    oa_text = (
        "이 출원의 청구항 제1항은 특허법 제29조제2항에 따라 거절됩니다.\n\n"
        "인용발명 1의 공급자 위치(단락 [0031] 참조)와 인용발명 2의 쿠폰 발급(단락 [0041], [0082], [0140] 참조)에 대응한다."
    )
    oa = Document(document_id="OA", filename="oa.xml", kind="office_action", text=oa_text)
    ref1_text = (
        "[0031] 공급자 위치를 쿠폰 화면에 표시한다.\n[0041] THIS_IS_THE_WRONG_REFERENCE_PARAGRAPH."
    )
    ref2_text = "[0031] THIS_IS_ALSO_WRONG.\n[0041] 쿠폰 발급 요청을 저장한다.\n[0082] 쿠폰 정보를 제공한다.\n[0140] 쿠폰 번호로 사용 처리한다."
    refs = [
        Document(document_id="REF1", filename="ref1.pdf", kind="reference", text=ref1_text),
        Document(document_id="REF2", filename="ref2.pdf", kind="reference", text=ref2_text),
    ]
    unrelated = Document(
        document_id="OTHER", filename="unrelated.pdf", kind="reference", text="NEVER_SEND_THIS"
    )
    citations = [
        Citation(
            citation_id=f"C{i}",
            publication_number=f"102015000000{i}",
            evidence=evidence(oa, f"인용발명 {i}"),
            document_id=f"REF{i}",
        )
        for i in [1, 2]
    ]
    return AnalysisResult(
        documents=[patent, oa, *refs, unrelated],
        claims=[Claim(number=1, text=claim_text, evidence=evidence(patent, claim_text))],
        rejections=[
            Rejection(
                rejection_id="R1",
                claims=[1],
                statute="특허법 제29조제2항",
                explanation=oa_text,
                evidence=evidence(oa, oa_text, xml_path="/PatentOpinionSubmission/Reasons"),
                citation_ids=["C1", "C2"],
            )
        ],
        citations=citations,
        direct_claims=[1],
        dependency_claims=[],
    )


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(review, "ENV_PATH", tmp_path / "prototype" / ".env")
    for key in ("ENDPOINT", "API_KEY", "DEPLOYMENT"):
        monkeypatch.delenv(f"KR_AZURE_OPENAI_{key}", raising=False)


def configure(monkeypatch):
    monkeypatch.setenv("KR_AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("KR_AZURE_OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("KR_AZURE_OPENAI_DEPLOYMENT", "test-deployment")


def make_client(monkeypatch, draft=None, status="completed", error=None):
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(status=status, output_parsed=draft)
    if error:
        client.responses.parse.side_effect = error
    factory = Mock(return_value=client)
    monkeypatch.setattr(review, "OpenAI", factory)
    return client, factory


def valid_draft():
    return review.ReviewDraft(
        findings=[
            review.Finding(
                topic="지적 설명",
                analysis="제공된 청구항의 쿠폰 구성을 비교합니다.",
                evidence_ids=["S1"],
            )
        ],
        suggestions=[
            review.Suggestion(text="명세서 뒷받침과 차이점을 추가 확인하세요.", evidence_ids=["S1"])
        ],
    )


@pytest.mark.parametrize("marker_at_end", [False, True])
def test_paragraph_slice_keeps_first_sentence_and_excludes_next_paragraph(marker_at_end):
    if marker_at_end:
        first = "  공급자 위치를 표시하는 첫 문장.[0031]\n쿠폰 발행을 설명하는 나머지 문장.\n"
        second = "  다음 문단의 첫 문장은 포함되면 안 된다.[0032]\n다음 문단의 나머지."
    else:
        first = "  [0031]공급자 위치를 표시하는 첫 문장.\n쿠폰 발행을 설명하는 나머지 문장.\n"
        second = "  [0032]다음 문단의 첫 문장은 포함되면 안 된다.\n다음 문단의 나머지."
    prefix = "공개특허 헤더\n발명의 설명\n"
    original = prefix + first + second
    spans = review._spans(original)
    excerpts = {number: original[start:end] for start, end, number in spans}
    assert excerpts["0031"] == first
    assert excerpts["0032"] == second
    assert spans[0][0] == len(prefix)
    assert spans[0][1] == spans[1][0]


def test_inline_paragraph_markers_remain_distinct():
    original = "[0001]첫 번째 문단.[0002]두 번째 문단."
    spans = review._spans(original)
    assert [(original[start:end], number) for start, end, number in spans] == [
        ("[0001]첫 번째 문단.", "0001"),
        ("[0002]두 번째 문단.", "0002"),
    ]


def test_local_context_exact_sources_correct_reference_paragraphs(analysis, monkeypatch):
    factory = Mock(side_effect=AssertionError("Local retrieval must not contact Azure"))
    monkeypatch.setattr(review, "OpenAI", factory)
    before = analysis.model_dump_json()
    context = review.build_review_context(analysis, 1)
    docs = {d.document_id: d for d in analysis.documents}
    assert all(source.text in docs[source.document_id].text for source in context.sources)
    assert context.sources[0].page_numbers == [1]
    assert any(
        "제29조제2항에 따라 거절" in s.text for s in context.sources if s.document_id == "OA"
    )
    assert any(s.xml_path == "/PatentOpinionSubmission/Reasons" for s in context.sources)
    ref1 = "".join(s.text for s in context.sources if s.document_id == "REF1")
    ref2 = "".join(s.text for s in context.sources if s.document_id == "REF2")
    assert "[0031]" in ref1 and "WRONG" not in ref1
    assert all(number in ref2 for number in ["[0041]", "[0082]", "[0140]"])
    assert "WRONG" not in ref2
    assert all(s.document_id != "OTHER" for s in context.sources)
    assert analysis.model_dump_json() == before
    factory.assert_not_called()


def test_reference_typo_and_reordered_registry_do_not_cross_link_paragraphs(analysis):
    # The actual KIPO notice spells one occurrence "인용방명 1". Only local
    # matching accepts that spelling; no source text is corrected.
    oa = analysis.documents[1]
    oa.text = oa.text.replace("인용발명 1", "인용방명 1")
    analysis.rejections[0].evidence = evidence(oa, oa.text)
    analysis.citations[0].evidence = evidence(oa, "인용방명 1")
    analysis.citations.reverse()
    context = review.build_review_context(analysis, 1)
    ref1 = "".join(s.text for s in context.sources if s.document_id == "REF1")
    ref2 = "".join(s.text for s in context.sources if s.document_id == "REF2")
    assert "[0031]" in ref1 and "WRONG" not in ref1
    assert all(number in ref2 for number in ["[0041]", "[0082]", "[0140]"])
    assert "WRONG" not in ref2
    assert any("인용방명 1" in s.text for s in context.sources if s.document_id == "OA")


def test_context_is_bounded_and_missing_reference_is_disclosed(analysis):
    oa = analysis.documents[1]
    oa.text += "\n\n" + ("전자쿠폰 원문 " * 10_000)
    analysis.rejections[0].evidence = evidence(oa, oa.text)
    analysis.citations[1].document_id = None
    context = review.build_review_context(analysis, 1)
    assert sum(len(s.text) for s in context.sources) <= review.MAX_CONTEXT_CHARS
    assert len(context.sources) <= review.MAX_SOURCES
    assert sum(len(s.text) for s in context.sources if s.document_id == "OA") < len(oa.text)
    assert any("일부 근거" in warning for warning in context.warnings)
    assert any("본문이 없어" in warning for warning in context.warnings)


def test_missing_configuration_does_not_use_root_or_legacy_keys(analysis, monkeypatch, tmp_path):
    (tmp_path / ".env").write_text(
        "KR_AZURE_OPENAI_API_KEY=parent-env-must-not-be-used\n", encoding="utf-8"
    )
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "existing-app-secret-must-not-be-used")
    factory = Mock()
    monkeypatch.setattr(review, "OpenAI", factory)
    with pytest.raises(ReviewError, match="설정이 없습니다"):
        review.analyze_with_azure(analysis, 1)
    factory.assert_not_called()


def test_configuration_file_is_explicit_and_environment_takes_precedence(monkeypatch):
    review.ENV_PATH.parent.mkdir()
    review.ENV_PATH.write_text(
        "KR_AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/openai/v1/\nKR_AZURE_OPENAI_API_KEY=file-key\nKR_AZURE_OPENAI_DEPLOYMENT=file-deployment\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KR_AZURE_OPENAI_DEPLOYMENT", "env-deployment")
    assert review._azure_settings() == (
        "https://example.openai.azure.com/openai/v1/",
        "file-key",
        "env-deployment",
    )


def test_grounded_review_returns_original_sources_and_preserves_input(analysis, monkeypatch):
    configure(monkeypatch)
    client, factory = make_client(monkeypatch, valid_draft())
    before = analysis.model_dump_json()
    response = review.analyze_with_azure(analysis, 1)
    args = client.responses.parse.call_args.kwargs
    assert args["store"] is False and args["max_output_tokens"] == 4_000
    assert args["model"] == "test-deployment"
    payload = json.loads(args["input"][1]["content"])
    assert "NEVER_SEND_THIS" not in args["input"][1]["content"]
    assert response.sources[0].model_dump() == payload["sources"][0]
    assert response.provider == "azure" and response.claim_number == 1
    assert response.findings[0].evidence_ids == ["S1"]
    assert analysis.model_dump_json() == before
    assert factory.call_args.kwargs["max_retries"] == 0
    client.close.assert_called_once()


@pytest.mark.parametrize("kind", ["findings", "suggestions"])
def test_invented_sources_rejected(analysis, monkeypatch, kind):
    configure(monkeypatch)
    draft = valid_draft()
    getattr(draft, kind)[0].evidence_ids = ["invented"]
    client, _ = make_client(monkeypatch, draft)
    with pytest.raises(ReviewError, match="제공되지 않은 근거"):
        review.analyze_with_azure(analysis, 1)
    client.close.assert_called_once()


@pytest.mark.parametrize("kind", ["findings", "suggestions"])
def test_each_finding_and_suggestion_requires_evidence(analysis, monkeypatch, kind):
    configure(monkeypatch)
    draft = valid_draft().model_dump()
    draft[kind][0]["evidence_ids"] = []
    make_client(monkeypatch, draft)
    with pytest.raises(ReviewError, match="형식"):
        review.analyze_with_azure(analysis, 1)


@pytest.mark.parametrize(
    "error,expected",
    [
        (APITimeoutError(request=httpx.Request("POST", "https://example.test")), "시간이 초과"),
        (APIConnectionError(request=httpx.Request("POST", "https://example.test")), "요청이 실패"),
        (ValueError("schema invalid; sensitive provider detail"), "형식"),
        (ImportError("DLL load failed; sensitive provider detail"), "필수 모듈"),
    ],
)
def test_provider_failures_are_explicit_and_client_closes(analysis, monkeypatch, error, expected):
    configure(monkeypatch)
    client, _ = make_client(monkeypatch, error=error)
    with pytest.raises(ReviewError, match=expected) as caught:
        review.analyze_with_azure(analysis, 1)
    assert "sensitive provider detail" not in str(caught.value)
    client.close.assert_called_once()


def test_incomplete_response_is_not_success(analysis, monkeypatch):
    configure(monkeypatch)
    make_client(monkeypatch, None, status="incomplete")
    with pytest.raises(ReviewError, match="완료하지 못했"):
        review.analyze_with_azure(analysis, 1)


def test_modified_evidence_cannot_be_submitted(analysis, monkeypatch):
    configure(monkeypatch)
    factory = Mock()
    monkeypatch.setattr(review, "OpenAI", factory)
    analysis.claims[0].evidence.text = "LLM이 수정한 원문"
    with pytest.raises(ReviewError, match="원문과 일치하지"):
        review.analyze_with_azure(analysis, 1)
    factory.assert_not_called()


def test_actual_sdk_structured_parse_with_mock_transport(analysis, monkeypatch):
    """Exercise the installed SDK and its JSON schema without a cloud request."""
    configure(monkeypatch)
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_mock",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "test-deployment",
                "parallel_tool_calls": False,
                "tools": [],
                "tool_choice": "auto",
                "output": [
                    {
                        "id": "msg_mock",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": valid_draft().model_dump_json(),
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    monkeypatch.setattr(
        review,
        "OpenAI",
        lambda **kwargs: OpenAI(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handle))
        ),
    )
    response = review.analyze_with_azure(analysis, 1)
    assert response.findings[0].topic == "지적 설명"
    assert requests[0]["store"] is False
    assert requests[0]["text"]["format"]["type"] == "json_schema"
    assert requests[0]["text"]["format"]["strict"] is True
