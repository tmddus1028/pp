"""One review-only presentation shared by Streamlit and the PDF detail iframe."""

import hashlib
import json
import os
from html import escape

import httpx
import streamlit as st

from frontend.readable_text import text_html


def prepare_session(result):
    token = hashlib.sha256(
        json.dumps(result, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    identity = (result["analysis_id"], token)
    if st.session_state.get("improvement_identity") != identity:
        st.session_state.improvement_identity = identity
        st.session_state.improvement_results = {}
        st.session_state.improvement_errors = {}


def cache_key(number, rejection_id):
    return f"{number}:{rejection_id or 'all'}"


def request_improvement(result, number, rejection_id=None):
    prepare_session(result)
    key = cache_key(number, rejection_id)
    if key in st.session_state.improvement_results:
        return
    st.session_state.improvement_errors.pop(key, None)
    try:
        endpoint = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        response = httpx.post(
            endpoint + "/improvements",
            json={"analysis": result, "claim_number": number, "rejection_id": rejection_id},
            timeout=180,
        )
        if response.is_error:
            detail = response.json().get("detail", "")
            raise ValueError(str(detail))
        from backend.improvements.models import ImprovementResponse

        review = ImprovementResponse.model_validate(response.json())
        if (
            review.analysis_id != result["analysis_id"]
            or review.claim_number != number
            or review.rejection_id != rejection_id
        ):
            raise ValueError("응답의 사건·청구항·거절 사유가 현재 요청과 다릅니다.")
        st.session_state.improvement_results[key] = review.model_dump(mode="json")
    except (httpx.HTTPError, ValueError) as exc:
        # Never overwrite the original analysis or display an error as a successful review.
        detail = (
            str(exc) if isinstance(exc, ValueError) else "서버 연결 또는 응답 시간을 확인하세요."
        )
        st.session_state.improvement_errors[key] = "개선 방안을 생성하지 못했습니다. " + detail


def improvement_html(review):
    draft = review["suggestion"]
    out = ["<p><strong>검토용 개선 방안</strong></p>"]
    out.append(
        text_html(
            "로컬 규칙 기반 검토 항목 · 외부 AI 호출 없음"
            if review["provider"] == "local"
            else review["provider"] + " · AI 검토 초안"
        )
    )
    out.extend(["<h4>왜 지적됐나</h4>", text_html(draft["issue_summary"])])
    for basis in draft["rejection_basis"]:
        out.extend(
            [
                text_html(basis["rejection_id"] + " · " + basis["statute"]),
                text_html(basis["problem"]),
            ]
        )
    if draft["element_comparison"]:
        out.append("<h4>구성요소 대비 · 선행문헌 원문 대비 미검증</h4>")
        for comparison in draft["element_comparison"]:
            out.append(text_html(comparison["claim_element"]))
            out.append(text_html("심사관 기재: " + comparison["examiner_position"]))
            out.append(text_html("근거: " + ", ".join(comparison["evidence_ids"])))
    for title, argument in [("수정 방향", False), ("검토 가능한 반박 논점", True)]:
        out.append("<h4>" + title + "</h4>")
        strategies = [
            s for s in draft["strategies"] if (s["action_type"] == "argument_only") == argument
        ]
        if not strategies:
            out.append(text_html("현재 근거와 검토 방식으로는 구체적인 제안을 제시하지 않습니다."))
        for strategy in strategies:
            out.append("<p><strong>" + escape(strategy["title"]) + "</strong></p>")
            for value in [
                strategy["description"],
                "검토할 청구항 요소: " + " / ".join(strategy["target_elements"]),
                "근거: " + ", ".join(strategy["evidence_ids"]),
                strategy["expected_effect"],
                "주의: " + strategy["tradeoff"],
            ]:
                out.append(text_html(value))
    out.append("<h4>근거</h4>")
    used = {eid for b in draft["rejection_basis"] for eid in b["evidence_ids"]}
    used.update(eid for s in draft["strategies"] for eid in s["evidence_ids"])
    used.update(eid for c in draft["element_comparison"] for eid in c["evidence_ids"])
    used.update(draft["optional_example"]["evidence_ids"])
    for source in review["sources"]:
        if source["evidence_id"] not in used:
            continue
        evidence = source["evidence"]
        label = (
            source["evidence_id"]
            + " · "
            + source["label"]
            + " · p. "
            + ", ".join(map(str, evidence["page_numbers"]))
        )
        out.append(
            "<details><summary>"
            + escape(label)
            + "</summary>"
            + text_html(evidence["text"])
            + "</details>"
        )
    if draft["optional_example"]["available"]:
        example = draft["optional_example"]
        out.append(
            "<details><summary>예시 수정 표현 보기 · 검토용 예시</summary>"
            + text_html(example["text"])
            + text_html(example["disclaimer"])
            + "</details>"
        )
    out.append("<h4>근거 부족 및 주의점</h4>")
    for line in draft["missing_evidence"] + draft["cautions"] + review["limitations"]:
        out.append(text_html(line))
    return "".join(out)


def component_reviews():
    return {
        key: improvement_html(value)
        for key, value in st.session_state.get("improvement_results", {}).items()
    }


def render_improvement(result, number, rejection_id=None):
    key = cache_key(number, rejection_id)
    if st.button("개선 방안 보기", key="improve-" + result["analysis_id"] + "-" + key):
        with st.spinner("관련 근거를 바탕으로 검토용 개선 방안을 준비합니다…"):
            request_improvement(result, number, rejection_id)
    error = st.session_state.get("improvement_errors", {}).get(key)
    if error:
        st.error(error)
    review = st.session_state.get("improvement_results", {}).get(key)
    if review:
        with st.expander("개선 방안", expanded=True):
            st.markdown(improvement_html(review), unsafe_allow_html=True)
