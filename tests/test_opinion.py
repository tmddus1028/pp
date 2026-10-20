"""Opinion drafts are shown only when every paragraph and amendment checks out against sources."""

from unittest.mock import Mock, patch

import pytest
from conftest import ROOT

from backend.config import Settings
from backend.errors import ProviderError
from backend.improvements.models import Grounding, Strategy
from backend.improvements.opinion import (
    HEADINGS,
    OpinionDraft,
    OpinionParagraph,
    OpinionRequest,
    OpinionSection,
    generate_opinion,
    validate_opinion,
)
from backend.improvements.retrieval import retrieved_context

CLAIM = "쿠폰 서버와 소비자 단말을 포함하는 전자쿠폰 시스템."
SPEC = "상기 쿠폰 서버는 단말의 해상도와 NFC 유무에 따라 쿠폰 형식을 결정한다."
OA = "청구항 1은 인용발명 1 및 2에 의해 쉽게 발명할 수 있으므로 진보성이 없습니다."


def source(eid, kind, text):
    return {"evidence_id": eid, "kind": kind, "evidence": {"text": text}}


def context(originals=True):
    return {
        "claim_text": CLAIM,
        "parents": [],
        "citations": [{"original_available": originals}],
        "sources": [
            source("CLAIM-1", "claim", CLAIM),
            source("OA-R1", "office_action", OA),
            source("SPEC-1", "specification", SPEC),
        ],
    }


def strategy(action="add_limitation"):
    return Strategy(
        title="형식 결정 단계 추가",
        description="명세서의 쿠폰 형식 결정 구성을 청구항 1에 추가",
        target_elements=["쿠폰 서버"],
        action_type=action,
        evidence_ids=["CLAIM-1", "OA-R1", "SPEC-1"],
        grounding=[
            Grounding(
                evidence_id="SPEC-1", quote="단말의 해상도와 NFC 유무에 따라 쿠폰 형식을 결정"
            )
        ],
        expected_effect="인용발명과 차이 명확화",
        tradeoff="권리 범위 축소",
    )


def paragraph(text, eid=None, quote=None):
    grounding = [Grounding(evidence_id=eid, quote=quote)] if eid else []
    return OpinionParagraph(text=text, evidence_ids=[eid] if eid else [], grounding=grounding)


def draft(
    amended=CLAIM[:-1]
    + "으로서, 상기 쿠폰 서버는 단말의 해상도와 NFC 유무에 따라 쿠폰 형식을 결정하는 전자쿠폰 시스템.",
    **override,
):
    paragraphs = {
        "보정사항": paragraph(
            "청구항 1에 명세서의 쿠폰 형식 결정 구성을 추가하였습니다.", "SPEC-1", SPEC
        ),
        "거절이유의 요지": paragraph(
            "심사관은 진보성이 없다고 하였습니다.", "OA-R1", "진보성이 없습니다"
        ),
        "본원발명의 요지": paragraph("본원발명은 전자쿠폰 시스템입니다.", "CLAIM-1", CLAIM),
        "인용발명과의 대비": paragraph(
            "보정된 구성은 인용발명 1, 2 어디에도 개시되어 있지 않습니다.", "SPEC-1", SPEC
        ),
        "결론": paragraph("검토를 부탁드립니다."),
    } | override
    return OpinionDraft(
        amended_claim=amended,
        sections=[OpinionSection(heading=h, paragraphs=[paragraphs[h]]) for h in HEADINGS],
        cautions=[],
    )


def test_grounded_draft_passes_and_reports_added_text():
    changes = validate_opinion(draft(), context(), strategy())
    assert any("해상도" in c.revised for c in changes if c.change_type in {"added", "changed"})


def test_particles_on_added_words_are_not_new_matter():
    amended = (
        CLAIM[:-1] + "으로서, 쿠폰 서버가 해상도를 기준으로 쿠폰 형식을 결정하는 전자쿠폰 시스템."
    )
    validate_opinion(draft(amended), context(), strategy())


@pytest.mark.parametrize(
    "bad, ctx, message",
    [
        (
            draft(CLAIM[:-1] + "으로서, 블록체인 원장에 기록하는 전자쿠폰 시스템."),
            context(),
            "명세서 인용에 없는",
        ),
        (
            draft(**{"보정사항": paragraph("보정", "SPEC-1", "명세서에 없는 문장")}),
            context(),
            "일치하지",
        ),
        (draft(**{"결론": paragraph("명세서 [0099]에 따라 등록됩니다.")}), context(), "문단 번호"),
        (draft(**{"결론": paragraph("따라서 특허됩니다.")}), context(), "확정"),
        (draft(), context(originals=False), "미개시"),
        (draft(**{"거절이유의 요지": paragraph("요지", "CLAIM-1", CLAIM)}), context(), "통지서"),
        (draft(**{"인용발명과의 대비": paragraph("차이가 있습니다.")}), context(), "원문 근거"),
        (draft(amended=None), context(), "보정 청구항이 없습니다"),
    ],
)
def test_ungrounded_drafts_are_rejected(bad, ctx, message):
    with pytest.raises(ValueError, match=message):
        validate_opinion(bad, ctx, strategy())


def test_argument_only_must_not_amend():
    validate_opinion(
        draft(None, **{"인용발명과의 대비": paragraph("구성에 차이가 있습니다.", "SPEC-1", SPEC)}),
        context(),
        strategy("argument_only"),
    )
    with pytest.raises(ValueError, match="보정 없는 대응"):
        validate_opinion(draft(), context(), strategy("argument_only"))


def test_real_korean_case_with_fake_model_repairs_once():
    from backend.jurisdictions.korean import analyze_korean

    data = ROOT / "korean_prototype/data/kr_1020190000844"
    result = analyze_korean(
        (data / "KR20190025857A.pdf").read_bytes(),
        "patent.pdf",
        (data / "office_action_20190409.xml").read_bytes(),
        "oa.xml",
    )
    settings = Settings(_env_file=None, llm_provider="local", improvement_provider="local_ollama")
    request = OpinionRequest(
        analysis=result, claim_number=1, rejection_id="R1", strategy=strategy()
    )
    ctx, *_ = retrieved_context(request, [("selected_claim", result.patent.claims[0].text)])
    by_kind = {s["kind"]: s for s in ctx["sources"]}
    spec, oa, claim = by_kind["specification"], by_kind["office_action"], by_kind["claim"]
    quote = spec["evidence"]["text"].strip()[:40]
    chosen = strategy().model_copy(
        update={
            "evidence_ids": [claim["evidence_id"], oa["evidence_id"], spec["evidence_id"]],
            "grounding": [Grounding(evidence_id=spec["evidence_id"], quote=quote)],
        }
    )
    request = request.model_copy(update={"strategy": chosen})
    good = OpinionDraft(
        amended_claim=ctx["claim_text"] + " " + quote,
        sections=[
            OpinionSection(
                heading=h,
                paragraphs=[
                    paragraph(f"{h} 검토 문단.", oa["evidence_id"], oa["evidence"]["text"][:30])
                ],
            )
            for h in HEADINGS
        ],
        cautions=[],
    )
    bad = good.model_copy(update={"amended_claim": ctx["claim_text"] + " 양자 암호 모듈"})
    fake = Mock()
    fake.complete.side_effect = [bad, good]
    with patch("backend.improvements.opinion.get_provider", return_value=fake):
        response = generate_opinion(request, settings)
    assert fake.complete.call_count == 2
    assert "previous_attempt_rejected_because" in fake.complete.call_args.args[0]
    assert response.draft.amended_claim == good.amended_claim
    assert response.changes and response.draft.cautions[0].startswith("검토용")

    fake.complete.side_effect = [bad, bad]
    with patch("backend.improvements.opinion.get_provider", return_value=fake):
        with pytest.raises(ProviderError, match="근거 검증"):
            generate_opinion(request, settings)

    rules_only = Settings(_env_file=None, llm_provider="local", improvement_provider="local")
    with pytest.raises(ProviderError, match="IMPROVEMENT_PROVIDER"):
        generate_opinion(request, rules_only)


def test_selection_keep_elements_must_survive_the_amendment():
    from backend.improvements.opinion import validate_draft

    good = draft()
    validate_draft(good, context(), True, SPEC, keep=["소비자 단말"])
    with pytest.raises(ValueError, match="유지하기로 한 구성"):
        validate_draft(good, context(), True, SPEC, keep=["포인트 적립 서버"])
    with pytest.raises(ValueError, match="보정 없는 대응"):
        validate_draft(good, context(), False, SPEC)
