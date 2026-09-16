import json
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI

from backend.config import Settings
from backend.errors import ExtractionError, ProviderError
from backend.ingestion.adapters import from_text
from backend.llm.client import (
    ExtractionBatch,
    OpenAIExtractionClient,
    ReferenceDraft,
    RejectionDraft,
)
from backend.llm.prompts import SYSTEM_PROMPT
from backend.llm.structured_extraction import extract_structured, validate_draft
from backend.office_action.oa_parser import Chunk

TEXT = "Claims 1-2 are rejected under 35 USC 103 over Smith (US 8,765,432 B2)."


def draft():
    return RejectionDraft(
        action_type="rejection",
        statute="35 USC 103",
        claims=[1, 2],
        reason_summary="Examiner combines cited teachings.",
        examiner_explanation="See evidence.",
        cited_references=[
            ReferenceDraft(
                name="Smith", publication_number="US8765432B2", evidence="Smith (US 8,765,432 B2)"
            )
        ],
        evidence=TEXT,
    )


def test_prompt_constraints():
    assert "untrusted" in SYSTEM_PROMPT
    assert "Do not invent" in SYSTEM_PROMPT
    assert "dependent claims" in SYSTEM_PROMPT


def test_grounded_output():
    document = from_text(TEXT, "oa.txt", "office_action")
    result = validate_draft(draft(), Chunk(TEXT, 0, len(TEXT)), document, "openai")
    assert result.claims == [1, 2]
    assert result.cited_references[0].publication_number == "US8765432B2"
    assert result.evidence.text == TEXT


@pytest.mark.parametrize(
    "field,value",
    [
        ("evidence", "fabricated text"),
        ("claims", [1, 99]),
        ("statute", "35 USC 102"),
        ("action_type", "objection"),
    ],
)
def test_reject_unsupported_drafts(field, value):
    item = draft().model_copy(update={field: value})
    with pytest.raises(ExtractionError):
        validate_draft(
            item, Chunk(TEXT, 0, len(TEXT)), from_text(TEXT, "oa.txt", "office_action"), "openai"
        )


def test_citation_hallucination():
    item = draft()
    item.cited_references[0].publication_number = "US9999999B2"
    with pytest.raises(ExtractionError):
        validate_draft(
            item, Chunk(TEXT, 0, len(TEXT)), from_text(TEXT, "oa.txt", "office_action"), "openai"
        )


def test_injected_client_and_chunk_merge():
    client = SimpleNamespace(extract=lambda text: ExtractionBatch(rejections=[draft()]))
    rejections, _ = extract_structured(from_text(TEXT, "oa.txt", "office_action"), client, "azure")
    assert rejections[0].extraction_method == "azure"


@pytest.mark.parametrize("provider", ["openai", "azure"])
def test_sdk_transport_contract(provider):
    settings = Settings(
        _env_file=None,
        llm_provider=provider,
        openai_api_key="test-key",
        openai_model="test-model",
        azure_openai_api_key="azure-test-key",
        azure_openai_deployment="test-deployment",
        azure_openai_endpoint="https://example.openai.azure.com",
    )
    client = OpenAIExtractionClient(settings)
    original = client.client
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "test-model",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_test",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "annotations": [],
                                "text": ExtractionBatch(rejections=[draft()]).model_dump_json(),
                            }
                        ],
                    }
                ],
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": [],
            },
        )

    client.client = OpenAI(
        api_key="test",
        base_url=str(original.base_url),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    original.close()
    try:
        output = client.extract(TEXT)
        assert output.rejections[0].claims == [1, 2]
        assert captured["body"]["store"] is False
        assert captured["body"]["text"]["format"]["strict"] is True
        assert captured["body"]["model"] == (
            "test-model" if provider == "openai" else "test-deployment"
        )
        if provider == "azure":
            assert str(client.client.base_url).endswith("/openai/v1/")
    finally:
        client.close()


def test_configuration_failure():
    with pytest.raises(ProviderError):
        OpenAIExtractionClient(
            Settings(_env_file=None, llm_provider="openai", openai_api_key="", openai_model="")
        )
    with pytest.raises(ProviderError):
        OpenAIExtractionClient(
            Settings(_env_file=None, llm_provider="azure", azure_openai_endpoint="")
        )


def test_refusal_handled():
    client = OpenAIExtractionClient(
        Settings(_env_file=None, llm_provider="openai", openai_api_key="test", openai_model="test")
    )
    client.client.close()
    client.client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=lambda **kwargs: SimpleNamespace(status="completed", output_parsed=None)
        )
    )
    with pytest.raises(ProviderError, match="거절"):
        client.extract(TEXT)
