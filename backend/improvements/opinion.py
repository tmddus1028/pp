"""Response draft (의견서) written from what the attorney chose; every paragraph is source-checked.

Two entry points share one generate/validate loop:
- generate_from_selection: the attorney's confirmed per-issue selection (reference cases,
  direction, instructions, amendment scope) saved in PostgreSQL — the main product flow.
- generate_opinion: an AI strategy card (/improvements/opinion), kept for the API.
"""

import re
from typing import Literal

from pydantic import Field

from backend.errors import ProviderError
from backend.improvements.context import build_context
from backend.improvements.grounding import verify_quantities, verify_source_mentions
from backend.improvements.models import Grounding, ImprovementRequest, ReviewEvidence, Strategy
from backend.improvements.prompts import COMMON, KR
from backend.improvements.providers import get_provider
from backend.improvements.retrieval import retrieved_context
from backend.improvements.revision import claim_diff
from backend.improvements.revision_models import TextChange
from backend.improvements.service import provider_settings, squash
from backend.llm.client import OpenAIExtractionClient
from backend.precedents import repository
from backend.schemas import Model

HEADINGS = ("보정사항", "거절이유의 요지", "본원발명의 요지", "인용발명과의 대비", "결론")
GROUNDED = {"거절이유의 요지", "인용발명과의 대비"}
GUARANTEE = re.compile(r"특허됩니다|등록됩니다|거절이\s*(?:반드시\s*)?해소됩니다", re.I)
NOT_DISCLOSED = re.compile(r"(?:개시|기재|시사|제시)[^.。\n]{0,12}않")
# Claim connectors that carry no technical content; everything else added must exist in a source.
CONNECTORS = {
    "상기",
    "있어서",
    "포함하는",
    "포함하되",
    "포함하며",
    "것을",
    "특징으로",
    "하는",
    "하고",
    "되는",
    "및",
    "또는",
    "있는",
    "위한",
    "통해",
    "따라",
    "의해",
    "기초하여",
    "이용하여",
    "추가로",
    "기준으로",
    "기반으로",
}


def known(word, text):
    """Korean attaches particles/endings (센서를, 결정하는): accept a stem of at least half the word."""
    return any(word[:k] in text for k in range(len(word), max(2, (len(word) + 1) // 2) - 1, -1))


OPINION_PROMPT = """You draft a Korean 의견서 (response to a 의견제출통지서) for ONE strategy that a
patent attorney already selected (selected_strategy). It is a review draft, never a filing.
Write exactly these sections in order: 보정사항, 거절이유의 요지, 본원발명의 요지, 인용발명과의 대비, 결론.
인용발명과의 대비 compares 목적, 구성, 효과 (in that order, as separate paragraphs when possible).
Every paragraph lists evidence_ids and grounding quotes copied VERBATIM from the supplied sources.
거절이유의 요지 must quote the office_action source. 인용발명과의 대비 must quote sources too.
If selected_strategy.action_type is argument_only, amended_claim is null and 보정사항 says no amendment.
Otherwise amended_claim is the full amended claim: the original claim text plus ONLY limitations
quoted from SPEC sources of the strategy (copy their technical wording). Do not add other content.
Never state that a cited invention does not disclose something unless every citation has
original_available true. Never promise allowance. Mention KIPRIS precedents only as 참고.
"""


SELECTION_PROMPT = """The attorney already chose how to answer this issue (attorney_selection);
follow it instead of choosing a strategy yourself. direction: 반박 = argue only (amended_claim null),
보정 = amend, 반박과 보정 = amend and argue. Put emphasize first in 인용발명과의 대비, use
use_arguments, never use exclude_arguments. keep_elements must stay verbatim in amended_claim.
add_elements says what to add: take the technical wording from SPEC sources only. Respect
forbidden_changes. reference_cases are other applications the attorney chose as precedent: follow
their pattern (added_limitation, outcome) only as 참고, never cite them as evidence or facts.
"""


class OpinionRequest(ImprovementRequest):
    strategy: Strategy


Direction = Literal["반박", "보정", "반박과 보정", "추가 조사", "보류"]
AMENDING = {"보정", "반박과 보정"}


class Selection(Model):
    """One issue's confirmed choice (요구사항 5장). Stored as-is in selections.record."""

    claim_number: int = Field(gt=0, le=10000)
    rejection_id: str = Field(min_length=1, max_length=40)
    precedent_ids: list[str] = Field(default_factory=list, max_length=10)
    direction: Direction
    emphasize: str = Field(default="", max_length=2000)
    use_arguments: str = Field(default="", max_length=2000)
    exclude_arguments: str = Field(default="", max_length=2000)
    keep_elements: list[str] = Field(default_factory=list, max_length=20)
    add_elements: str = Field(default="", max_length=2000)
    forbidden_changes: str = Field(default="", max_length=2000)
    confirmed_by: str = Field(min_length=1, max_length=80)


class OpinionParagraph(Model):
    text: str = Field(min_length=1, max_length=4000)
    evidence_ids: list[str]
    grounding: list[Grounding]


class OpinionSection(Model):
    heading: Literal["보정사항", "거절이유의 요지", "본원발명의 요지", "인용발명과의 대비", "결론"]
    paragraphs: list[OpinionParagraph] = Field(min_length=1)


class OpinionDraft(Model):
    amended_claim: str | None
    sections: list[OpinionSection]
    cautions: list[str]


class OpinionResponse(Model):
    analysis_id: str
    claim_number: int
    rejection_id: str | None
    provider: str
    draft: OpinionDraft
    changes: list[TextChange]
    sources: list[ReviewEvidence]
    limitations: list[str]


def content_words(text):
    return {w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", text) if w not in CONNECTORS}


def check_quotes(sources, ids, grounding):
    if not set(ids) <= sources.keys():
        raise ValueError("제공되지 않은 근거 ID를 사용했습니다.")
    for quote in grounding:
        if quote.evidence_id not in ids or squash(quote.quote) not in squash(
            sources[quote.evidence_id]["evidence"]["text"]
        ):
            raise ValueError("근거 인용문이 제공 원문과 일치하지 않습니다.")


def validate_opinion(draft, context, strategy):
    """Checks for a draft written from an AI strategy card."""
    sources = {s["evidence_id"]: s for s in context["sources"]}
    spec = " ".join(
        q.quote for q in strategy.grounding if sources[q.evidence_id]["kind"] == "specification"
    )
    return validate_draft(draft, context, strategy.action_type != "argument_only", spec)


def validate_draft(draft, context, amend, spec, keep=()):
    """Paragraph grounding for every draft; new-matter and kept wording when it amends."""
    sources = {s["evidence_id"]: s for s in context["sources"]}
    if [s.heading for s in draft.sections] != list(HEADINGS):
        raise ValueError("의견서 섹션 구성이 정해진 순서와 다릅니다.")
    all_originals = all(c["original_available"] for c in context["citations"])
    for section in draft.sections:
        for paragraph in section.paragraphs:
            check_quotes(sources, paragraph.evidence_ids, paragraph.grounding)
            verify_source_mentions(paragraph.text, context)
            if GUARANTEE.search(paragraph.text):
                raise ValueError("의견서에 등록·거절 해소를 확정하는 표현이 있습니다.")
            if NOT_DISCLOSED.search(paragraph.text) and not all_originals:
                raise ValueError("원문을 확보하지 못한 인용발명에 대해 미개시를 단정했습니다.")
            if section.heading in GROUNDED and not paragraph.grounding:
                raise ValueError(f"'{section.heading}' 문단에 원문 근거가 없습니다.")
        if section.heading == "거절이유의 요지" and not any(
            sources[q.evidence_id]["kind"] == "office_action"
            for p in section.paragraphs
            for q in p.grounding
        ):
            raise ValueError("거절이유의 요지에 심사관 통지서 인용이 필요합니다.")

    original = context["claim_text"]
    if not amend:
        if draft.amended_claim is not None:
            raise ValueError("보정 없는 대응인데 보정 청구항이 있습니다.")
        return []
    if not draft.amended_claim or squash(draft.amended_claim) == squash(original):
        raise ValueError("보정 대응인데 보정 청구항이 없습니다.")
    missing = [k for k in keep if squash(k) not in squash(draft.amended_claim)]
    if missing:
        raise ValueError(f"유지하기로 한 구성이 보정 청구항에서 빠졌습니다: {missing[0][:40]}")
    # New matter: words added to the claim must come from SPEC text (or the claim/ancestor text).
    # ponytail: word-level check, not a legal new-matter ruling.
    if not spec:
        raise ValueError("보정 근거가 될 명세서 인용이 없습니다.")
    allowed = squash(spec + original + "".join(p["text"] for p in context["parents"]))
    changes = claim_diff(original, draft.amended_claim)
    added = " ".join(c.revised for c in changes if c.change_type in {"added", "changed"})
    unknown = {w for w in content_words(added) if not known(w, allowed)}
    if unknown:
        raise ValueError(
            f"보정 청구항에 명세서 인용에 없는 표현이 있습니다: {', '.join(sorted(unknown)[:5])}"
        )
    verify_quantities(draft.amended_claim, original, spec)
    return changes


MODEL_SETTING = {
    "local_ollama": "local_llm_model",
    "anthropic": "anthropic_model",
    "qwen": "qwen_model",
    "openai": "openai_model",
    "azure": "azure_openai_deployment",
}


def _context(request, settings):
    # Same retrieval as /improvements so evidence IDs resolve to the same text.
    context, _, _ = build_context(request)
    context, sources, _, _, _ = retrieved_context(
        request,
        [("selected_claim", context["claim_text"])],
        spec_mode=settings.improvement_spec_mode,
        max_chars=settings.improvement_context_chars,
    )
    config = provider_settings(settings, context["jurisdiction"])
    if config.llm_provider == "local":
        raise ProviderError(
            "의견서 초안에는 IMPROVEMENT_PROVIDER=local_ollama, anthropic, qwen, azure 또는 openai 설정이 필요합니다."
        )
    return context, sources, config


def _generate(request, context, sources, config, settings, prompt, validate, client_factory):
    provider = get_provider(config, client_factory)
    # ponytail: one whole-draft call; split per section if local models fail validation often.
    draft = provider.complete(context, OpinionDraft, prompt)
    for attempt in range(1 + settings.improvement_repair_attempts):
        try:
            changes = validate(draft)
            break
        except ValueError as exc:
            if attempt == settings.improvement_repair_attempts:
                raise ProviderError("의견서 초안의 근거 검증에 실패했습니다. " + str(exc)) from exc
            draft = provider.complete(
                {**context, "previous_attempt_rejected_because": str(exc)}, OpinionDraft, prompt
            )
    draft.cautions = list(
        dict.fromkeys(
            [
                "검토용 의견서 초안입니다. 제출 전 원문·출원 이력과 변리사 검토가 필요합니다.",
                "근거 인용문 일치는 기술적·법적 타당성을 보증하지 않습니다.",
            ]
            + draft.cautions
        )
    )
    return OpinionResponse(
        analysis_id=request.analysis.analysis_id,
        claim_number=request.claim_number,
        rejection_id=request.rejection_id,
        provider=config.llm_provider,
        draft=draft,
        changes=changes,
        sources=sources,
        limitations=["원본 청구항과 사건 결과는 수정하지 않습니다."],
    )


def generate_opinion(request, settings, client_factory=OpenAIExtractionClient):
    context, sources, config = _context(request, settings)
    by_id = {s["evidence_id"]: s for s in context["sources"]}
    try:
        check_quotes(by_id, request.strategy.evidence_ids, request.strategy.grounding)
    except ValueError as exc:
        raise ValueError(
            "선택한 대응 방안의 근거가 현재 사건 문서와 맞지 않습니다. 대응 방안을 다시 받아 주세요."
        ) from exc
    context = {**context, "selected_strategy": request.strategy.model_dump(mode="json")}
    return _generate(
        request,
        context,
        sources,
        config,
        settings,
        COMMON + KR + OPINION_PROMPT,
        lambda draft: validate_opinion(draft, context, request.strategy),
        client_factory,
    )


def check_selection(selection, result):
    """Reject a selection that points at the wrong claim, issue or unknown cases (before saving)."""
    claim = next(
        (c for c in result.patent.claims if c.claim_number == selection.claim_number), None
    )
    if claim is None:
        raise ValueError("선택한 청구항이 사건에 없습니다.")
    if not any(r.rejection_id == selection.rejection_id for r in result.rejections):
        raise ValueError("선택한 거절 쟁점이 사건에 없습니다.")
    unknown = [i for i in selection.precedent_ids if repository.get(i) is None]
    if unknown:
        raise ValueError(f"참고 사례를 찾을 수 없습니다: {unknown[0]}")
    absent = [k for k in selection.keep_elements if squash(k) not in squash(claim.text)]
    if absent:
        raise ValueError(f"유지할 구성은 현재 청구항 문구에서 골라야 합니다: {absent[0][:40]}")


def generate_from_selection(result, selection, settings, client_factory=OpenAIExtractionClient):
    """Draft for one confirmed selection. Returns (response, model name) for the draft record."""
    if selection.direction not in {"반박", *AMENDING}:
        raise ValueError(f"'{selection.direction}'으로 정한 쟁점은 초안을 작성하지 않습니다.")
    check_selection(selection, result)
    request = ImprovementRequest(
        analysis=result, claim_number=selection.claim_number, rejection_id=selection.rejection_id
    )
    context, sources, config = _context(request, settings)
    cases = [repository.summary(repository.get(i)) for i in selection.precedent_ids]
    context = {
        **context,
        "attorney_selection": selection.model_dump(mode="json", exclude={"confirmed_by"}),
        "reference_cases": cases,
    }
    spec = " ".join(
        s["evidence"]["text"] for s in context["sources"] if s["kind"] == "specification"
    )
    amend = selection.direction in AMENDING
    response = _generate(
        request,
        context,
        sources,
        config,
        settings,
        COMMON + KR + OPINION_PROMPT + SELECTION_PROMPT,
        lambda draft: validate_draft(draft, context, amend, spec, selection.keep_elements),
        client_factory,
    )
    return response, getattr(config, MODEL_SETTING.get(config.llm_provider, ""), "") or "unknown"
