"""Structured, explicitly requested reviews with conservative evidence gates."""

import os
import re
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values

from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.context import REWRITE_PHRASE, build_context
from backend.improvements.grounding import verify_quantities, verify_source_mentions
from backend.improvements.models import ClaimImprovementSuggestion, ImprovementResponse
from backend.improvements.providers import get_provider
from backend.improvements.retrieval import retrieved_context
from backend.llm.client import OpenAIExtractionClient

DISCLAIMER = (
    "검토용 개선 방안입니다. 자동 제출용 문안이 아니며 원문·출원 이력 및 전문가 검토가 필요합니다."
)


class ReviewProviderSettings(Settings):
    llm_provider: Literal["local", "local_ollama", "openai", "azure", "qwen"] = "local"


def provider_settings(settings, jurisdiction):
    selected = (
        settings.llm_provider
        if settings.improvement_provider == "inherit"
        else settings.improvement_provider
    )
    if jurisdiction == "kr" and settings.improvement_provider not in {
        "local",
        "local_ollama",
        "qwen",
    }:
        path = Path(__file__).resolve().parents[2] / "korean_prototype" / ".env"
        values = dotenv_values(path, interpolate=False)
        config = {
            key: (
                os.environ.get("KR_AZURE_OPENAI_" + key, values.get("KR_AZURE_OPENAI_" + key)) or ""
            ).strip()
            for key in ("ENDPOINT", "API_KEY", "DEPLOYMENT")
        }
        if any(config.values()):
            if not all(config.values()):
                raise ProviderError("한국 개선 검토의 KR_AZURE_OPENAI 설정이 불완전합니다.")
            return Settings(
                _env_file=None,
                llm_provider="azure",
                azure_openai_endpoint=config["ENDPOINT"],
                azure_openai_api_key=config["API_KEY"],
                azure_openai_deployment=config["DEPLOYMENT"],
                llm_timeout_seconds=settings.llm_timeout_seconds,
            )
    return ReviewProviderSettings(
        _env_file=None, **{**settings.model_dump(), "llm_provider": selected}
    )


def local_review(context):
    """Deterministic review questions/abstention, never masquerading as model reasoning."""
    sources = {s["evidence_id"]: s for s in context["sources"]}
    claim_id = f"CLAIM-{context['claim_number']}"
    element = context["claim_text"][:180]
    strategies, comparisons, bases = [], [], []
    for rejection in context["rejections"]:
        rid, eid = rejection["rejection_id"], rejection["evidence_id"]
        text = sources[eid]["evidence"]["text"]
        law = rejection["statute"]
        names = ", ".join(
            dict.fromkeys(
                c["name"] or c["publication_number"] or c["citation_id"]
                for c in context["citations"]
                if c["rejection_id"] == rid
            )
        )
        bases.append(
            {
                "rejection_id": rid,
                "statute": law,
                "problem": "심사관이 기재한 근거를 확인하세요: " + text[:350],
                "evidence_ids": [eid],
            }
        )
        if rejection["action_type"] == "objection":
            continue
        if re.search(r"\b103\b", law) or "29조제2항" in law.replace(" ", ""):
            title = f"{rid}: 인용문헌 조합과 선택 구성의 대응 재검토"
            description = f"선택 구성 ‘{element}’을 {names or '심사관이 인용한 문헌'}에서 어떻게 제시했다고 설명하는지, 결합 이유와 함께 원문에서 대조하는 논점을 검토할 수 있습니다. 선행문헌 본문이 없어 차이의 존재는 확인되지 않았습니다."
            comparisons.append(
                {
                    "claim_element": element,
                    "examiner_position": text[:350],
                    "assessment": "not_verified",
                    "evidence_ids": [claim_id, eid],
                }
            )
        elif re.search(r"\b112\b", law):
            types = [
                label
                for pattern, label in [
                    (r"written\s+description", "기재 뒷받침"),
                    (r"enablement|not\s+enable|fails?\s+to\s+enable", "실시가능성"),
                    (r"indefiniteness|indefinite|antecedent\s+basis", "명확성·선행기재"),
                ]
                if re.search(pattern, text, re.I)
            ]
            title = f"{rid}: §112 " + (" / ".join(types) if types else "유형 미확인") + " 근거 대조"
            description = (
                f"선택 구성 ‘{element}’에 관한 심사관의 구체적 표현과 명세서 기재를 대조하는 논점을 검토할 수 있습니다. "
                + (
                    "원문에서 확인된 검토 항목: " + ", ".join(types)
                    if types
                    else "현재 근거만으로 §112 세부 유형을 추정하지 않습니다."
                )
            )
        else:
            title = f"{rid}: 명시된 지적과 선택 구성의 대응 확인"
            description = f"선택 구성 ‘{element}’에 대해 {law}의 어떤 지적이 실제로 연결되는지 제공 원문에서 확인해야 합니다. 구체적 수정안은 제시하지 않습니다."
        strategies.append(
            {
                "title": title,
                "description": description,
                "target_elements": [element],
                "action_type": "argument_only",
                "evidence_ids": [claim_id, eid],
                "grounding": [{"evidence_id": eid, "quote": text[:350]}],
                "expected_effect": "심사관 주장과 재검토할 부분을 구분하는 데 사용할 수 있습니다. 반박의 성립은 미검증입니다.",
                "tradeoff": "원문 확인 전에는 수정 또는 반박의 타당성을 확정할 수 없습니다.",
            }
        )
    if context["conditional_rewrite_supported"]:
        ids = (
            [claim_id, "STATUS"]
            + [p["evidence_id"] for p in context["parents"]]
            + [r["evidence_id"] for r in context["rejections"] if r["action_type"] == "objection"]
        )
        text = sources["STATUS"]["evidence"]["text"]
        phrase = REWRITE_PHRASE.search(text)[0]
        strategies.append(
            {
                "title": "독립항 형태로 재작성하는 방향",
                "description": "심사관이 명시한 조건에 따라 상위·중간 청구항의 모든 한정을 포함하여 독립항으로 재작성하는 방향을 검토할 수 있습니다.",
                "target_elements": [element],
                "action_type": "dependency_rewrite",
                "evidence_ids": ids,
                "grounding": [{"evidence_id": "STATUS", "quote": phrase}],
                "expected_effect": "심사관이 제시한 재작성 조건을 검토할 수 있습니다.",
                "tradeoff": "모든 인용 한정을 누락 없이 포함해야 하며 특허 가능성을 보증하지 않습니다.",
            }
        )
    return ClaimImprovementSuggestion.model_validate(
        {
            "claim_number": context["claim_number"],
            "jurisdiction": context["jurisdiction"],
            "issue_summary": "선택된 지적: "
            + " · ".join(r["rejection_id"] + " / " + r["statute"] for r in context["rejections"]),
            "rejection_basis": bases,
            "element_comparison": comparisons,
            "strategies": strategies,
            "optional_example": {
                "available": False,
                "text": None,
                "disclaimer": DISCLAIMER,
                "evidence_ids": [],
                "grounding": [],
            },
            "missing_evidence": context["missing_evidence"],
            "cautions": [
                DISCLAIMER,
                "로컬 규칙 모드의 검토 항목입니다. AI가 기술적 차별성이나 구체적 보정안을 판단한 결과가 아닙니다.",
            ],
        }
    )


def validate_suggestion(draft, context):
    sources = {s["evidence_id"]: s for s in context["sources"]}
    claim_id = f"CLAIM-{context['claim_number']}"
    if (
        draft.claim_number != context["claim_number"]
        or draft.jurisdiction != context["jurisdiction"]
    ):
        raise ValueError("개선안의 청구항 또는 관할이 요청과 다릅니다.")
    narrative = [draft.issue_summary, *(b.problem for b in draft.rejection_basis)]
    narrative += [
        value
        for s in draft.strategies
        for value in (s.title, s.description, s.expected_effect, s.tradeoff)
    ]
    for value in narrative:
        verify_source_mentions(value, context)
    if any(
        re.search(
            r"이렇게\s*(?:수정|보정|하면).*?(?:특허됩니다|등록됩니다)|거절이\s*(?:반드시\s*)?해소됩니다|(?:guarantees?\s+(?:allowance|patentability))",
            value,
            re.I,
        )
        for value in narrative
    ):
        raise ValueError("개선안에 허용·거절 해소를 확정하는 표현이 포함되어 있습니다.")
    expected = {r["rejection_id"]: r for r in context["rejections"]}
    if len(draft.rejection_basis) != len(expected) or {
        b.rejection_id for b in draft.rejection_basis
    } != set(expected):
        raise ValueError("개선안의 거절 사유 범위가 요청과 다릅니다.")

    def evidence(ids, grounding=()):
        if not set(ids) <= sources.keys():
            raise ValueError("개선안이 제공되지 않은 근거 ID를 사용했습니다.")
        for quote in grounding:
            if (
                quote.evidence_id not in ids
                or quote.quote not in sources[quote.evidence_id]["evidence"]["text"]
            ):
                raise ValueError("개선안의 근거 인용문이 제공 원문과 일치하지 않습니다.")

    for basis in draft.rejection_basis:
        source = expected[basis.rejection_id]
        evidence(basis.evidence_ids)
        if basis.statute != source["statute"] or source["evidence_id"] not in basis.evidence_ids:
            raise ValueError("개선안의 법조항 또는 심사관 근거가 일치하지 않습니다.")
    claim_texts = [context["claim_text"]] + [p["text"] for p in context["parents"]]

    def target(elements):
        if any(not e.strip() or not any(e in text for text in claim_texts) for e in elements):
            raise ValueError("개선안이 원문에서 확인되지 않은 청구항 요소를 지정했습니다.")

    def core(ids):
        if claim_id not in ids or not any(sources[i]["kind"] == "office_action" for i in ids):
            raise ValueError("개선안에 선택 청구항과 심사관 근거가 함께 필요합니다.")

    def specification(ids, grounding):
        if not any(sources[q.evidence_id]["kind"] == "specification" for q in grounding):
            raise ValueError("구체적인 수정 제안에는 실제 명세서 근거와 원문 인용이 필요합니다.")

    for comparison in draft.element_comparison:
        evidence(comparison.evidence_ids)
        target([comparison.claim_element])
        core(comparison.evidence_ids)
    for strategy in draft.strategies:
        evidence(strategy.evidence_ids, strategy.grounding)
        target(strategy.target_elements)
        core(strategy.evidence_ids)
        if strategy.action_type not in {"argument_only", "dependency_rewrite"}:
            specification(strategy.evidence_ids, strategy.grounding)
            quotes = " ".join(
                q.quote
                for q in strategy.grounding
                if sources[q.evidence_id]["kind"] == "specification"
            )
            verify_quantities(strategy.description, context["claim_text"], quotes)
        if strategy.action_type == "dependency_rewrite":
            required = {"STATUS", *(p["evidence_id"] for p in context["parents"])}
            if (
                not context["conditional_rewrite_supported"]
                or not required <= set(strategy.evidence_ids)
                or not any(q.evidence_id == "STATUS" for q in strategy.grounding)
            ):
                raise ValueError(
                    "독립항 재작성에 관한 심사관의 명시적 근거와 전체 종속관계가 필요합니다."
                )
    example = draft.optional_example
    evidence(example.evidence_ids, example.grounding)
    if example.available:
        if not example.text or not example.disclaimer:
            raise ValueError("예시 수정 표현의 문안 또는 주의 문구가 없습니다.")
        core(example.evidence_ids)
        specification(example.evidence_ids, example.grounding)
        verify_source_mentions(example.text, context)
        verify_quantities(
            example.text,
            context["claim_text"],
            " ".join(
                q.quote
                for q in example.grounding
                if sources[q.evidence_id]["kind"] == "specification"
            ),
        )
    elif example.text is not None or example.evidence_ids or example.grounding:
        raise ValueError("미제공 예시에 수정 문안 또는 근거가 포함되어 있습니다.")
    return draft


def generate_improvement(request, settings, client_factory=OpenAIExtractionClient):
    context, sources, digest = build_context(request)
    config = provider_settings(settings, context["jurisdiction"])
    if request.require_llm:
        if config.llm_provider == "local":
            raise ProviderError(
                "AI 개선안에는 IMPROVEMENT_PROVIDER=qwen, local_ollama, azure 또는 openai 설정이 필요합니다."
            )
        context, sources, digest, _, _ = retrieved_context(
            request, [("selected_claim", context["claim_text"])]
        )
    if config.llm_provider == "local":
        draft = local_review(context)
    else:
        draft = get_provider(config, client_factory).generate_improvement(context)
    try:
        validate_suggestion(draft, context)
    except ValueError as exc:
        raise ProviderError("개선 방안의 근거 검증에 실패했습니다. " + str(exc)) from exc
    draft.missing_evidence = list(
        dict.fromkeys(context["missing_evidence"] + draft.missing_evidence)
    )
    draft.cautions = list(
        dict.fromkeys(
            [DISCLAIMER, "근거 ID와 인용문 일치는 기술적·법적 타당성을 보증하지 않습니다."]
            + draft.cautions
        )
    )
    return ImprovementResponse(
        analysis_id=request.analysis.analysis_id,
        claim_number=request.claim_number,
        rejection_id=request.rejection_id,
        evidence_hash=digest,
        provider=config.llm_provider,
        status="abstained"
        if not draft.strategies
        else "limited"
        if draft.missing_evidence or config.llm_provider == "local"
        else "review",
        suggestion=draft,
        sources=sources,
        limitations=["제공된 관련 발췌만 검토합니다. 원본 청구항은 수정하지 않습니다."],
    )
