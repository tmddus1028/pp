from typing import Literal, Protocol
from urllib.parse import urlparse

from openai import APIError, OpenAI

from backend.config import Settings
from backend.errors import ProviderError
from backend.llm.prompts import SYSTEM_PROMPT
from backend.schemas import Model


class ReferenceDraft(Model):
    name: str | None
    publication_number: str | None
    evidence: str


class RejectionDraft(Model):
    action_type: Literal["rejection", "objection"]
    statute: str
    claims: list[int]
    reason_summary: str
    examiner_explanation: str
    cited_references: list[ReferenceDraft]
    evidence: str


class ExtractionBatch(Model):
    rejections: list[RejectionDraft]


class ExtractionClient(Protocol):
    def extract(self, text: str) -> ExtractionBatch: ...


class OpenAIExtractionClient:
    def __init__(self, settings: Settings):
        if settings.llm_provider == "openai":
            if not settings.openai_api_key or not settings.openai_model:
                raise ProviderError(
                    "OpenAI 모드에는 OPENAI_API_KEY와 OPENAI_MODEL 설정이 필요합니다."
                )
            self.model = settings.openai_model
            self.client = OpenAI(
                api_key=settings.openai_api_key, timeout=settings.llm_timeout_seconds, max_retries=1
            )
        elif settings.llm_provider == "azure":
            endpoint = settings.azure_openai_endpoint.rstrip("/")
            if (
                not settings.azure_openai_api_key
                or not settings.azure_openai_deployment
                or urlparse(endpoint).scheme != "https"
                or not urlparse(endpoint).netloc
            ):
                raise ProviderError(
                    "Azure 모드에는 HTTPS ENDPOINT, API_KEY, DEPLOYMENT 설정이 필요합니다."
                )
            self.model = settings.azure_openai_deployment
            base_url = endpoint if endpoint.endswith("/openai/v1") else endpoint + "/openai/v1"
            self.client = OpenAI(
                api_key=settings.azure_openai_api_key,
                base_url=base_url + "/",
                timeout=settings.llm_timeout_seconds,
                max_retries=1,
            )
        else:
            raise ProviderError("local 모드에는 외부 LLM client가 필요하지 않습니다.")

    def extract(self, text: str) -> ExtractionBatch:
        try:
            response = self.client.responses.parse(
                model=self.model,
                store=False,
                text_format=ExtractionBatch,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
        except APIError as exc:
            raise ProviderError(
                f"LLM 요청이 실패했습니다 ({type(exc).__name__}). 설정과 연결을 확인하세요."
            ) from exc
        except ValueError as exc:
            raise ProviderError("LLM 응답을 지정된 JSON schema로 해석하지 못했습니다.") from exc
        if response.status != "completed" or response.output_parsed is None:
            raise ProviderError("LLM이 추출을 완료하지 못했거나 요청을 거절했습니다.")
        return response.output_parsed

    def close(self) -> None:
        self.client.close()
