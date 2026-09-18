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
        st.session_state.improvement_open = {}
        st.session_state.revision_results = {}
        st.session_state.revision_errors = {}
        st.session_state.revision_drafts = {}
        for key in list(st.session_state):
            if key.startswith("revision-input-"):
                del st.session_state[key]


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
            json={
                "analysis": result,
                "claim_number": number,
                "rejection_id": rejection_id,
                "require_llm": True,
            },
            timeout=650,
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
        st.session_state.improvement_open[key] = True
    if st.session_state.improvement_open.get(key):
        with st.expander("개선 방안", expanded=True):
            if st.button("AI 개선안 생성", key="generate-" + key):
                with st.spinner("관련 원문으로 AI 검토를 요청합니다…"):
                    request_improvement(result, number, rejection_id)
            error = st.session_state.improvement_errors.get(key)
            if error:
                st.error(error)
            review = st.session_state.improvement_results.get(key)
            if review:
                st.markdown(improvement_html(review), unsafe_allow_html=True)
            st.markdown("**수정 Claim 검증**")
            text = st.text_area(
                "수정 Claim",
                key="revision-input-" + key,
                max_chars=12000,
                value=st.session_state.revision_drafts.get(key, ""),
            )
            st.session_state.revision_drafts[key] = text
            if st.button("수정본 검증", key="validate-" + key):
                with st.spinner("변경점과 명세서 근거를 검토합니다…"):
                    request_revision(result, number, rejection_id, text)
            if error := st.session_state.revision_errors.get(key):
                st.error(error)
            st.markdown(
                revisions_html(st.session_state.revision_results.get(key, [])),
                unsafe_allow_html=True,
            )


def request_revision(result, number, rejection_id, text):
    prepare_session(result)
    key = cache_key(number, rejection_id)
    st.session_state.revision_drafts[key] = text
    st.session_state.revision_errors.pop(key, None)
    history = st.session_state.revision_results.setdefault(key, [])
    digest = hashlib.sha256(text.encode()).hexdigest()
    if any(r["revision"]["text_hash"] == digest for r in history):
        return
    if not text.strip():
        st.session_state.revision_errors[key] = "수정 청구항을 입력하세요."
        return
    try:
        endpoint = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        response = httpx.post(
            endpoint + "/improvements/revisions",
            json={
                "analysis": result,
                "claim_number": number,
                "rejection_id": rejection_id,
                "revised_text": text,
                "parent_revision_id": history[-1]["revision"]["revision_id"] if history else None,
            },
            timeout=1250,
        )
        if response.is_error:
            raise ValueError(str(response.json().get("detail", "")))
        from backend.improvements.revision_models import RevisionReview

        review = RevisionReview.model_validate(response.json())
        if (
            review.analysis_id != result["analysis_id"]
            or review.rejection_id != rejection_id
            or review.revision.original_claim_number != number
            or review.revision.text_hash != digest
            or review.revision.text != text
        ):
            raise ValueError("수정본 검토의 사건·범위·입력 내용이 현재 요청과 다릅니다.")
        data = review.model_dump(mode="json")
        data["session_order"] = history[-1].get("session_order", len(history)) + 1 if history else 1
        history.append(data)
        del history[:-3]
    except (httpx.HTTPError, ValueError) as exc:
        st.session_state.revision_errors[key] = "수정본 검증을 완료하지 못했습니다. " + (
            str(exc) if isinstance(exc, ValueError) else "서버 연결 또는 응답 시간을 확인하세요."
        )


def revisions_html(history):
    out = []
    names = {"added": "추가", "removed": "삭제", "changed": "변경", "unchanged": "유지"}
    for index, review in reversed(list(enumerate(history, 1))):
        rev, draft = review["revision"], review["assessment"]
        out.append(
            f'<details class="revision-result" open><summary>Revision {review.get("session_order", index)} · 수정본 검증 결과</summary>'
        )
        out.append(text_html(rev["created_at"]))
        out.append(text_html("검토용 AI 판단 · " + review["provider"]))
        out.append(text_html(draft["revision_summary"]))
        out.append(
            "<details><summary>입력한 수정 Claim</summary>" + text_html(rev["text"]) + "</details>"
        )
        out.append("<h4>원 Claim과 변경점</h4>")
        for change in review["claim_changes"]:
            if change["change_type"] == "unchanged":
                continue
            out.append(
                text_html(
                    names[change["change_type"]]
                    + ": "
                    + change["original"]
                    + " → "
                    + change["revised"]
                )
            )
        if all(c["change_type"] == "unchanged" for c in review["claim_changes"]):
            out.append(text_html("원 청구항과 동일합니다."))
        out.append("<h4>명세서 근거 · LLM 검토</h4>")
        elements = {e["element_id"]: e for e in review["elements"]}
        statuses = {
            "SUPPORTED": "지원 확인(LLM 판단)",
            "PARTIALLY_SUPPORTED": "일부 근거",
            "NOT_FOUND": "검색 근거 찾지 못함",
            "UNCERTAIN": "판단 불확실",
        }
        for support in draft["specification_support"]:
            element = elements[support["element_id"]]
            out.append(
                text_html(
                    element["element_id"]
                    + " · "
                    + names[element["change_type"]]
                    + " · "
                    + statuses[support["status"]]
                )
            )
            out.append(text_html(element["element"]))
            out.append(text_html(support["reason"]))
            out.append(text_html("근거: " + ", ".join(support["evidence_ids"])))
        out.append("<h4>기존 거절 대응 재검토</h4>")
        responses = {
            "POTENTIALLY_ADDRESSES": "대응 가능성 있음 · 검토 필요",
            "PARTIALLY_ADDRESSES": "일부 대응 가능성 있음",
            "DOES_NOT_ADDRESS": "지적에 대응하지 못한 것으로 검토됨",
            "INSUFFICIENT_EVIDENCE": "근거 부족 · 판단 제한",
        }
        for response in draft["rejection_response"]:
            out.append(text_html(response["rejection_id"] + " · " + responses[response["status"]]))
            out.append(text_html(response["reason"]))
            out.append(text_html("근거: " + ", ".join(response["evidence_ids"])))
        out.append("<h4>유사도 · 참고 지표</h4>")
        sim = review["similarity"]
        out.append(text_html(sim["method"] + " · " + sim["note"]))
        for label, value in [
            ("원 Claim 대비", sim["original_claim"]),
            *sim["specification"].items(),
        ]:
            out.append(
                text_html(
                    str(label)
                    + ": "
                    + (f"{value:.1%}" if value is not None else "계산할 근거 없음")
                )
            )
        for line in (
            review["new_matter_risks"]
            + draft["remaining_issues"]
            + draft["cautions"]
            + review["limitations"]
        ):
            out.append(text_html(line))
        used = {
            eid
            for item in draft["specification_support"] + draft["rejection_response"]
            for eid in item["evidence_ids"]
        }
        for source in review["sources"]:
            if source["evidence_id"] in used:
                label = (
                    source["evidence_id"]
                    + " · p."
                    + ",".join(map(str, source["evidence"]["page_numbers"]))
                )
                out.append(
                    "<details><summary>"
                    + escape(label)
                    + "</summary>"
                    + text_html(source["evidence"]["text"])
                    + "</details>"
                )
        out.append("</details>")
    return "".join(out)


def component_revisions():
    return {
        key: revisions_html(history)
        for key, history in st.session_state.get("revision_results", {}).items()
    }
