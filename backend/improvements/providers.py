"""Provider boundary shared by explicit improvement and revision requests."""

import json
from typing import Protocol
from urllib.parse import urlparse

import httpx
from openai import APIError

from backend.errors import ProviderError
from backend.improvements.models import ClaimImprovementSuggestion
from backend.improvements.prompts import COMMON, KR, US
from backend.llm.client import OpenAIExtractionClient


class ImprovementProvider(Protocol):
    def generate_improvement(self, context): ...

    def review_revision(self, context, schema, instructions): ...


class StructuredProvider:
    def generate_improvement(self, context):
        prompt = COMMON + (KR if context["jurisdiction"] == "kr" else US)
        return self.complete(context, ClaimImprovementSuggestion, prompt)

    def review_revision(self, context, schema, instructions):
        return self.complete(context, schema, instructions)


class OpenAIImprovementProvider(StructuredProvider):
    def __init__(self, settings, client_factory=OpenAIExtractionClient):
        self.settings, self.client_factory = settings, client_factory

    def complete(self, context, schema, instructions):
        client = self.client_factory(self.settings)
        try:
            response = client.client.responses.parse(
                model=client.model,
                store=False,
                max_output_tokens=6000,
                text_format=schema,
                input=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
            )
            if response.status != "completed" or response.output_parsed is None:
                raise ProviderError("LLM 검토 응답이 완료되지 않았습니다.")
            return schema.model_validate(response.output_parsed)
        except (APIError, ValueError) as exc:
            raise ProviderError(
                "LLM 검토를 생성하지 못했습니다. 연결 또는 응답 형식을 확인하세요."
            ) from exc
        finally:
            client.close()


class AzureImprovementProvider(OpenAIImprovementProvider):
    """Reuse the existing Azure endpoint/deployment setup in OpenAIExtractionClient."""


def local_endpoint(settings):
    url = settings.local_llm_base_url.rstrip("/")
    parsed = urlparse(url)
    # Local means loopback; do not silently send patent text to a cloud-compatible host.
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ProviderError("LOCAL_LLM_BASE_URL은 로컬 loopback Ollama 주소여야 합니다.")
    return url


class OllamaImprovementProvider(StructuredProvider):
    def __init__(self, settings):
        self.settings = settings

    def complete(self, context, schema, instructions):
        if not self.settings.local_llm_model.strip():
            raise ProviderError("LOCAL_LLM_MODEL에 설치한 로컬 모델 이름을 지정하세요.")
        if "cloud" in self.settings.local_llm_model.lower():
            raise ProviderError("local_ollama에는 cloud 모델이 아닌 설치된 로컬 모델을 지정하세요.")
        try:
            response = httpx.post(
                local_endpoint(self.settings) + "/api/chat",
                json={
                    "model": self.settings.local_llm_model,
                    "stream": False,
                    "format": schema.model_json_schema(),
                    "messages": [
                        {
                            "role": "system",
                            "content": instructions + "\nReturn only the supplied JSON schema.",
                        },
                        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                    ],
                    "options": {
                        "temperature": 0,
                        "num_ctx": self.settings.local_llm_context_tokens,
                        "num_predict": 6000,
                    },
                },
                timeout=self.settings.local_llm_timeout_seconds,
                trust_env=False,
                follow_redirects=False,
            )
            if response.status_code == 404:
                raise ProviderError(
                    "로컬 LLM 모델이 없습니다. 설정한 모델을 ollama pull로 설치하세요."
                )
            response.raise_for_status()
            data = response.json()
            if not data.get("done") or data.get("done_reason") == "length":
                raise ProviderError(
                    "로컬 LLM 응답이 중단되었습니다. 완료된 검토로 표시하지 않습니다."
                )
            if data.get("prompt_eval_count", 0) >= self.settings.local_llm_context_tokens - 128:
                raise ProviderError(
                    "로컬 모델 문맥 한도에 도달했습니다. 근거를 줄이거나 context 설정을 늘리세요."
                )
            return schema.model_validate_json(data["message"]["content"])
        except httpx.HTTPError as exc:
            raise ProviderError(
                "로컬 LLM에 연결할 수 없습니다. Ollama 서버·모델·응답 시간을 확인하세요."
            ) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("로컬 LLM 응답이 검토 JSON 형식과 일치하지 않습니다.") from exc


class QwenImprovementProvider(StructuredProvider):
    """Hosted Model Studio Chat Completions; keep the existing evidence gates."""

    def __init__(self, settings):
        self.settings = settings

    def endpoint(self):
        url = self.settings.qwen_base_url.strip().rstrip("/")
        parsed = urlparse(url)
        if not self.settings.qwen_api_key.strip() or not self.settings.qwen_model.strip():
            raise ProviderError("Qwen API 검토에는 QWEN_API_KEY와 QWEN_MODEL 설정이 필요합니다.")
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path != "/compatible-mode/v1"
        ):
            raise ProviderError(
                "QWEN_BASE_URL에 해당 리전의 HTTPS 주소를 지정하세요. "
                "주소는 /compatible-mode/v1로 끝나야 합니다."
            )
        return url + "/chat/completions"

    def complete(self, context, schema, instructions):
        endpoint = self.endpoint()
        try:
            response = httpx.post(
                endpoint,
                headers={"Authorization": "Bearer " + self.settings.qwen_api_key},
                json={
                    "model": self.settings.qwen_model,
                    "stream": False,
                    "enable_thinking": False,
                    "temperature": 0,
                    "max_tokens": 6000,
                    "messages": [
                        {"role": "system", "content": instructions},
                        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema.__name__,
                            "strict": True,
                            "schema": schema.model_json_schema(),
                        },
                    },
                },
                timeout=self.settings.llm_timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            )
            failures = {
                400: "모델의 JSON Schema 지원 여부와 요청 설정을 확인하세요.",
                401: "API 키와 키가 발급된 리전을 확인하세요.",
                403: "모델 접근 권한과 리전을 확인하세요.",
                404: "모델명과 API 주소를 확인하세요.",
                429: "호출 한도 또는 사용 가능 잔액을 확인하세요.",
            }
            if response.status_code in failures:
                raise ProviderError("Qwen API 오류: " + failures[response.status_code])
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("choices"), list):
                raise ValueError("invalid choices")
            choice = body["choices"][0]
            if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
                raise ValueError("invalid message")
            if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
                raise ProviderError(
                    "Qwen 응답이 중단되거나 거절됐습니다. 완료된 검토로 표시하지 않습니다."
                )
            return schema.model_validate_json(choice["message"]["content"])
        except httpx.HTTPError as exc:
            raise ProviderError(
                "Qwen API 연결 또는 응답 시간 오류입니다. 잠시 후 다시 시도하세요."
            ) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Qwen API 응답이 검토 JSON 형식과 일치하지 않습니다.") from exc


def get_provider(settings, client_factory=OpenAIExtractionClient):
    if settings.llm_provider == "qwen":
        return QwenImprovementProvider(settings)
    if settings.llm_provider == "local_ollama":
        return OllamaImprovementProvider(settings)
    if settings.llm_provider == "azure":
        return AzureImprovementProvider(settings, client_factory)
    if settings.llm_provider == "openai":
        return OpenAIImprovementProvider(settings, client_factory)
    raise ProviderError(
        "AI 검토에는 IMPROVEMENT_PROVIDER=qwen, local_ollama, azure 또는 openai 설정이 필요합니다."
    )
