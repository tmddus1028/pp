"""Compact Claim review over the existing analysis result; no new legal inference."""

import json
import re
from html import escape

import streamlit as st

from frontend.improvements import prepare_session, render_improvement
from frontend.readable_text import readable_text
from frontend.review_model import build_review_model, relied_references
from frontend.terminology import checklist_label, labels, reference_kind

FILTERS = ["전체", "직접 지적", "추가 검토", "허용"]
STATUS_LABELS = {
    "objected": "Objection · 추가 검토",
    "allowed": "허용",
    "withdrawn": "심사 대상 제외",
    "canceled": "취소됨",
    "pending": "계류 중",
    "unknown": "추출된 지적 없음",
}


def claim_rows(result):
    model = build_review_model(result)
    rows = []
    for item in model["items"]:
        if item["kind"] != "claim":
            continue
        role, label = (
            ("direct_rejection", "직접 지적")
            if item["direct"]
            else ("dependency", "Objection · 추가 검토")
            if item["objected"] or item["status"] == "objected"
            else ("dependency", "추가 검토 · 종속 영향")
            if item["indirect"]
            else ("unaddressed", STATUS_LABELS.get(item["status"], "추출된 지적 없음"))
        )
        # Match the PDF's direct-first status. Other dependency grounds remain in details.
        primary = item["direct"] or item["objected"] or item["indirect"]
        rejections = [r for r in model["rejections"] if r["rejection_id"] in item["rejection_ids"]]
        statutes = list(
            dict.fromkeys(
                r["statute"]
                for r in rejections
                if r["rejection_id"] in primary and r["statute"] != "unknown"
            )
        )
        rows.append(
            {**item, "role": role, "label": label, "statutes": statutes, "rejections": rejections}
        )
    return sorted(rows, key=lambda row: row["claim_number"]), model


def filter_claims(rows, selected_filter, query):
    query = query.strip()
    if query and (len(query) > 5 or not re.fullmatch(r"[0-9]+", query)):
        return []
    return [
        row
        for row in rows
        if (not query or row["claim_number"] == int(query))
        and (
            selected_filter == "전체"
            or (selected_filter == "직접 지적" and row["role"] == "direct_rejection")
            or (selected_filter == "추가 검토" and row["role"] == "dependency")
            or (selected_filter == "허용" and row["status"] == "allowed")
            or (
                selected_filter in ("§112", "§103")
                and any(
                    re.search(rf"\b{selected_filter[1:]}\b", statute) for statute in row["statutes"]
                )
            )
        )
    ]


def display_statute(statute):
    return re.sub(r"\b35\s+U\.?S\.?C\.?", "35 U.S.C.", statute, flags=re.I)


def evidence_view(evidence, prefix):
    pages = ", ".join(map(str, evidence["page_numbers"]))
    st.caption(f"{prefix} · p. {pages}")
    readable_text(evidence["text"], "claim-evidence", label=prefix + " 원문", expandable=True)


def processing_details(result):
    used = any(d.get("metadata", {}).get("ocr_used") for d in result["documents"])
    st.markdown(
        '<div class="analysis-complete">✓ 문서 분석 완료'
        + (" · OCR 사용됨" if used else "")
        + "</div>",
        unsafe_allow_html=True,
    )
    with st.expander("문서 처리 정보 보기", expanded=False):
        st.caption("분석 provider: " + result["provider"])
        if any(d["filename"].lower().endswith(".pdf") for d in result["documents"]):
            st.caption("PDF 화면 renderer: PDFium")
        for document in result["documents"]:
            metadata = document.get("metadata", {})
            st.text(document["filename"])
            st.caption("OCR 사용 여부: " + ("사용" if metadata.get("ocr_used") else "미사용"))
            st.caption("OCR 엔진: " + (metadata.get("ocr_engine") or "기록 없음 / 해당 없음"))
            st.caption(
                "OCR 페이지: " + (", ".join(map(str, metadata.get("ocr_pages", []))) or "없음")
            )
            st.caption(
                "OCR PDF renderer: " + (metadata.get("ocr_renderer") or "기록 없음 / 해당 없음")
            )
            with st.expander(document["filename"] + " · 추출 원문 / debug"):
                st.code(document["text"], language=None, wrap_lines=True)
                if metadata.get("removed_margins"):
                    st.caption("분석에서 제외한 PDF 헤더/푸터")
                    st.json(metadata["removed_margins"], expanded=False)
                for number, raw in metadata.get("ocr_raw_text", {}).items():
                    st.caption(f"OCR Page {number} · 보정하지 않은 엔진 원문")
                    st.code(raw, language=None, wrap_lines=True)
        warnings = list(
            dict.fromkeys(
                result.get("warnings", [])
                + [w for d in result["documents"] for w in d.get("warnings", [])]
            )
        )
        if warnings:
            st.caption("warning / debug 정보")
            for warning in warnings:
                st.text(warning)
        st.download_button(
            "분석 JSON 다운로드",
            json.dumps(result, ensure_ascii=False, indent=2),
            file_name=f"patent-review-{result['analysis_id']}.json",
            mime="application/json",
        )


def open_claim(number):
    st.session_state.selected_claim = number
    st.session_state.review_jump = f"claim-{number}"
    st.session_state.review_jump_scope = "all"
    st.session_state.next_section = "PDF 검토"


def save_filters():
    st.session_state.claim_list_filters = (
        st.session_state.claim_status_filter,
        st.session_state.claim_number_search,
    )


def save_check(item_id, widget_key):
    value = st.session_state[widget_key]
    st.session_state.claim_list_checked[item_id] = value
    if st.session_state.get("review_model_id") == st.session_state.claim_list_id:
        st.session_state.review_ui["checked"][item_id] = value


def claim_details(row, model, result):
    t = labels(result)
    st.markdown(t("**Claim 원문**"))
    evidence_view(row["evidence"], t("Patent"))
    st.caption(t("직접 종속 Claim: ") + (", ".join(map(str, row["children"])) or "없음"))
    st.markdown(t("**Office Action 근거**"))
    if row.get("status_evidence"):
        evidence_view(row["status_evidence"], t(STATUS_LABELS.get(row["status"], "청구항 상태")))
    for rejection in row["rejections"]:
        rid = rejection["rejection_id"]
        relationship = (
            "직접 지적"
            if rid in row["direct"]
            else t("Objection")
            if rid in row["objected"]
            else "종속 영향"
        )
        statute = (
            t("Objection")
            if rejection["action_type"] == "objection"
            else display_statute(rejection["statute"])
        )
        readable_text(f"{statute} · {relationship}")
        evidence_view(rejection["evidence"], t("Office Action"))
    if not row["rejections"]:
        st.caption(t("추출된 지적 사유가 없습니다."))
    st.markdown(
        f'<span class="claim-detail-label citation">{t("관련 citation")}</span>',
        unsafe_allow_html=True,
    )
    references = {
        ref["citation_id"]: ref
        for rejection in row["rejections"]
        for ref in relied_references(rejection)
    }
    if references:
        st.caption(
            t("해당 지적 사유에 인용된 문헌입니다. 개별 Claim 구성과의 대응은 원문에서 확인하세요.")
        )
        for ref in references.values():
            kind = reference_kind(ref, t)
            title = " · ".join(filter(None, [ref.get("name"), ref.get("publication_number"), kind]))
            with st.expander(title):
                st.caption(
                    "문헌 역할: "
                    + {
                        "relied_upon": "거절 인용문헌",
                        "supporting_evidence": "보조 증거",
                        "not_relied_upon": "기록 문헌",
                    }.get(ref.get("citation_role", "relied_upon"))
                )
                if ref.get("publication"):
                    readable_text(
                        ref["publication"] + (f" ({ref['year']})" if ref.get("year") else "")
                    )
                evidence_view(ref["evidence"], t("OA 인용"))
    else:
        st.caption("연결된 인용문헌이 없습니다.")
    st.markdown(
        f'<span class="claim-detail-label specification">{t("관련 specification")}</span>',
        unsafe_allow_html=True,
    )
    support = [i for i in model["items"] if i["id"] in row["support_ids"]]
    for item in support:
        evidence_view(item["evidence"], t(item["title"]))
    if not support:
        st.caption("원문에서 확인된 명시적 명세서·도면 연결이 없습니다.")
    st.markdown("**체크리스트**")
    entries = [
        entry
        for impact in model["impacts"]
        for entry in impact["review_items"]
        if impact["rejection_id"] in row["rejection_ids"]
        and row["claim_number"] in entry["claim_numbers"]
    ]
    for entry in entries:
        key = f"claim-check-{result['analysis_id']}-{row['claim_number']}-{entry['item_id']}"
        st.session_state[key] = st.session_state.claim_list_checked.get(entry["item_id"], False)
        st.checkbox(
            checklist_label(entry["text"], t),
            key=key,
            on_change=save_check,
            args=(entry["item_id"], key),
        )
    if not entries:
        st.caption("연결된 체크리스트 항목이 없습니다.")
    if row["rejection_ids"]:
        render_improvement(result, row["claim_number"])


def render_analysis(result):
    t = labels(result)
    prepare_session(result)
    key = result["analysis_id"]
    if st.session_state.get("claim_list_id") != key:
        st.session_state.claim_list_id = key
        st.session_state.claim_list_filters = ("전체", "")
        st.session_state.claim_list_checked = {}
        for name in ("claim_status_filter", "claim_number_search"):
            st.session_state.pop(name, None)
    if st.session_state.get("review_model_id") == key:
        st.session_state.claim_list_checked.update(st.session_state.review_ui.get("checked", {}))
        selected = st.session_state.review_ui.get("selected", "")
        if selected and re.fullmatch(r"claim-\d+", selected):
            st.session_state.selected_claim = int(selected[6:])
    rows, model = claim_rows(result)
    with st.container(key="claim-analysis"):
        processing_details(result)
        with st.container(key="claim-metrics"):
            metrics = st.columns(5)
            for col, label, count in zip(
                metrics,
                [
                    "전체 청구항",
                    t("거절/지적 사유"),
                    t("직접 지적 Claim"),
                    t("추가 검토 Claim"),
                    t("허용 Claim"),
                ],
                [
                    len(rows),
                    len(result["rejections"]),
                    sum(r["role"] == "direct_rejection" for r in rows),
                    sum(r["role"] == "dependency" for r in rows),
                    sum(r["status"] == "allowed" for r in rows),
                ],
            ):
                col.metric(label, count)
        first, second = st.columns([3, 1], vertical_alignment="bottom")
        saved_filter, saved_query = st.session_state.claim_list_filters
        st.session_state.setdefault("claim_status_filter", saved_filter)
        st.session_state.setdefault("claim_number_search", saved_query)
        if st.session_state.claim_status_filter not in FILTERS:
            st.session_state.claim_status_filter = "전체"
            st.session_state.claim_list_filters = ("전체", st.session_state.claim_number_search)
        with first:
            chosen = st.radio(
                t("Claim 상태 필터"),
                FILTERS,
                format_func=t,
                horizontal=True,
                key="claim_status_filter",
                label_visibility="collapsed",
                on_change=save_filters,
            )
        with second:
            query = st.text_input(
                t("Claim 번호 검색"),
                placeholder="예: 14",
                max_chars=8,
                key="claim_number_search",
                on_change=save_filters,
            )
        visible = filter_claims(rows, chosen, query)
        st.caption(f"{len(visible)} / {len(rows)}개 청구항")
        if not visible:
            st.markdown(
                '<div class="claim-empty">'
                + t("조건에 맞는 Claim이 없습니다. 필터 또는 번호를 확인하세요.")
                + "</div>",
                unsafe_allow_html=True,
            )
        for row in visible:
            number = row["claim_number"]
            selected = st.session_state.get("selected_claim") == number
            parents = ", ".join(t(f"Claim {n}") for n in row["depends_on"]) or "독립항"
            statutes = " · ".join(map(display_statute, row["statutes"])) or "—"
            with st.container(key=f"claim-row-{number}", border=True):
                left, right = st.columns([5, 1], vertical_alignment="center")
                with left:
                    st.markdown(
                        f'<div class="claim-summary {row["role"]}{" selected" if selected else ""}" data-claim="{number}">'
                        f'<div class="claim-heading"><strong>{t("Claim")} {number}</strong>'
                        f'<span class="claim-state {row["role"]}">{escape(t(row["label"]))}</span>'
                        + ('<span class="claim-current">선택됨</span>' if selected else "")
                        + f'</div><div class="claim-statutes">{escape(statutes)}</div>'
                        f'<div class="claim-relations">{t("상위 Claim")} · {escape(parents)}'
                        f"<span>{t('직접 종속 Claim')} · {len(row['children'])}개</span></div></div>",
                        unsafe_allow_html=True,
                    )
                with right:
                    st.button(
                        "PDF에서 보기",
                        key=f"claim-pdf-{number}",
                        width="stretch",
                        on_click=open_claim,
                        args=(number,),
                    )
                with st.expander(t(f"Claim {number} 상세 보기"), expanded=False):
                    claim_details(row, model, result)
