"""Display vocabulary is jurisdiction scoped and never translates source fields."""

from frontend.terminology import checklist_label, component_terms, labels, reference_kind


def test_us_labels_are_identity_and_korean_vocabulary_is_display_only():
    us, kr = labels({"analysis_id": "us-demo"}), labels({"analysis_id": "kr-demo"})
    wording = "Claim 1 · Office Action · Patent / Claims · Objection · 허용"
    assert us(wording) == wording
    assert kr(wording) == "청구항 1 · 의견제출통지서 · 명세서·청구범위 · 추가 지적 · 특허 가능"
    assert (
        kr("CLAIM ANALYSIS / 관련 specification / citation만")
        == "청구항 분석 / 관련 명세서 / 인용문헌만"
    )
    assert kr("특허법 제29조제2항 · 35 U.S.C. §103 · KR20190025857A") == (
        "특허법 제29조제2항 · 35 U.S.C. §103 · KR20190025857A"
    )
    assert kr("허용 Claim / 취소됨 / 계류 중") == "특허 가능 청구항 / 삭제됨 / 심사 중"
    assert component_terms({"analysis_id": "us-demo"}) == {}
    assert component_terms({"analysis_id": "kr-demo"})["Office Action"] == "의견제출통지서"


def test_reference_kind_does_not_call_patent_reference_a_specification():
    us, kr = labels(), labels(korean=True)
    assert reference_kind({"type": "patent"}, kr) == "특허문헌"
    assert reference_kind({"type": "npl"}, kr) == "비특허문헌"
    assert reference_kind({"type": "patent"}, us) == "Patent"
    assert reference_kind({"type": "npl"}, us) == "NPL"
    assert reference_kind({}, us, unknown="문헌 유형 미확인") == "문헌 유형 미확인"


def test_checklist_preserves_embedded_statutes_and_reference_names():
    kr = labels(korean=True)
    direct = "Claim 1: 특허법 제29조제2항 지적 사유와 OA 근거를 대조하세요."
    assert checklist_label(direct, kr) == (
        "청구항 1: 특허법 제29조제2항 거절이유와 의견제출통지서 근거를 대조하세요."
    )
    assert checklist_label(direct, labels()) == direct
    citation = (
        "Patent Claim Research: 심사관이 인용한 내용과 해당 청구항의 구성요소 대응을 확인하세요."
    )
    assert checklist_label(citation, kr) == citation
    dependent = "종속 Claim 2, 3: 상위 청구항과 연결된 추가 검토 범위를 확인하세요."
    assert checklist_label(dependent, kr).startswith("종속 청구항 2, 3:")
