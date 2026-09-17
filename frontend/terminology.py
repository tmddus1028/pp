"""Jurisdiction-specific display labels. Never apply these to source/evidence text."""

import re
from pathlib import Path

# Longest phrases win. Shared with both iframe components; identifiers stay unchanged.
KOREAN_TERMS = {
    "Patent / Claims": "명세서·청구범위",
    "Patent · 특허 문헌": "특허문헌",
    "NPL · 비특허 문헌": "비특허문헌",
    "OFFICE ACTION": "의견제출통지서",
    "Office Action": "의견제출통지서",
    "CITED REFERENCES": "인용문헌",
    "CLAIM ANALYSIS": "청구항 분석",
    "RELATIONSHIP MAP": "관계 지도",
    "EVIDENCE COMPARISON": "근거 비교",
    "DOCUMENT REVIEW": "문서 검토",
    "SPECIFICATION": "명세서",
    "WORKSPACE / DOCUMENTS": "작업 공간 / 문서 업로드",
    "WORKSPACE": "작업 공간",
    "Review Panel": "검토 패널",
    "PDF Viewer": "PDF 뷰어",
    "Publication / journal": "간행물·학술지",
    "Publication number": "문헌 번호",
    "Publication": "문헌 번호·간행물",
    "Year": "발행 연도",
    "Claims": "청구항",
    "Claim": "청구항",
    "CLAIM": "청구항",
    "Patent": "명세서",
    "OA": "의견제출통지서",
    "NPL": "비특허문헌",
    "citation": "인용문헌",
    "specification": "명세서",
    "Paragraph": "문단",
    "Figure": "도면",
    "drawing": "도면",
    # These are display labels, not conversions of US legal outcomes to KR decisions.
    "Objection": "추가 지적",
    "허용 가능성": "특허 가능성",
    "허용 여부": "특허 가능 여부",
    "허용": "특허 가능",
    "취소됨": "삭제됨",
    "계류 중": "심사 중",
    "거절/지적 사유": "거절이유",
    "거절 / 지적 사유": "거절이유",
    "거절 사유": "거절이유",
    "지적 사유": "거절이유",
    "심사 의견서": "의견제출통지서",
    "심사관 지적": "거절이유",
    "관련 citation": "관련 인용문헌",
    "관련 specification": "관련 명세서",
}


def korean_mode(result):
    return str(result.get("analysis_id", "")).startswith("kr-")


def label_pattern(terms):
    # ASCII boundaries permit Korean particles (Claim이) but protect e.g. PatentReview.
    return "|".join(
        (r"(?<![A-Za-z])" if term[0].isascii() and term[0].isalpha() else "")
        + re.escape(term)
        + (r"(?![A-Za-z])" if term[-1].isascii() and term[-1].isalpha() else "")
        for term in sorted(terms, key=len, reverse=True)
    )


_PATTERN = re.compile(label_pattern(KOREAN_TERMS))
TERMINOLOGY_JS = Path(__file__).with_name("terminology.js").read_text(encoding="utf-8")


def labels(result=None, *, korean=False):
    enabled = korean or (result is not None and korean_mode(result))

    def translate(text):
        return _PATTERN.sub(lambda match: KOREAN_TERMS[match[0]], text) if enabled else text

    return translate


def component_terms(result):
    return KOREAN_TERMS if korean_mode(result) else {}


def reference_kind(ref, translate, *, unknown="문헌"):
    # A patent reference is a patent publication, not the uploaded specification.
    kind = {"patent": "Patent", "npl": "NPL"}.get(ref.get("type"), unknown)
    return "특허문헌" if kind == "Patent" and translate("Claim") == "청구항" else translate(kind)


def checklist_label(text, translate):
    """Localize generated instructions, preserving interpolated laws/reference names."""
    match = re.fullmatch(r"(Claim \d+: )(.*)( 지적 사유와 OA 근거를 대조하세요\.)", text)
    if match:
        return translate(match[1]) + match[2] + translate(match[3])
    match = re.fullmatch(
        r"(종속 Claim [\d, ]+: )(상위 청구항과 연결된 추가 검토 범위를 확인하세요\.)", text
    )
    if match:
        return translate(match[1]) + match[2]
    if text == "OA가 지적한 청구항 일부가 입력에 없습니다. OA 당시의 청구항 버전을 확인하세요.":
        return translate(text)
    return text
