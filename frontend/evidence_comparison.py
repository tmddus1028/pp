"""Compare existing evidence without generating new source links or legal findings."""

import re
from html import escape

import streamlit as st

from frontend.claim_analysis import STATUS_LABELS, display_statute
from frontend.readable_text import readable_text, text_html
from frontend.review_model import build_review_model, relied_references
from frontend.terminology import labels, reference_kind


def comparison_for_claim(model, number, scope="all"):
    claim = next(i for i in model["items"] if i.get("claim_number") == number)
    rejections = [
        r
        for r in model["rejections"]
        if r["rejection_id"] in claim["rejection_ids"]
        and (scope == "all" or r["rejection_id"] == scope)
    ]
    rids = {r["rejection_id"] for r in rejections}
    direct, indirect = rids.intersection(claim["direct"]), rids.intersection(claim["indirect"])
    role, status = (
        ("direct_rejection", "직접 지적")
        if direct
        else ("dependency", "Objection · 추가 검토")
        if claim.get("objected") or claim["status"] == "objected"
        else ("dependency", "종속 영향")
        if indirect
        else ("unaddressed", STATUS_LABELS.get(claim["status"], "추출된 지적 없음"))
    )
    references = {}
    for rejection in rejections:
        for ref in relied_references(rejection):
            entry = references.setdefault(
                ref["citation_id"],
                {
                    "reference": ref,
                    "rejection_ids": [],
                    "claim_numbers": set(),
                    "occurrences": [],
                },
            )
            rid = rejection["rejection_id"]
            if rid not in entry["rejection_ids"]:
                entry["rejection_ids"].append(rid)
                entry["occurrences"].append({"rejection_id": rid, "evidence": ref["evidence"]})
            entry["claim_numbers"].update(rejection["claims"])
    for entry in references.values():
        entry["claim_numbers"] = sorted(entry["claim_numbers"])
    support = [
        i
        for i in model["items"]
        if i["id"] in claim["support_ids"] and rids.intersection(i["rejection_ids"])
    ]
    return {
        "claim": claim,
        "role": role,
        "status": status,
        "rejections": rejections,
        "citations": list(references.values()),
        "support": support,
        "statutes": list(dict.fromkeys(r["statute"] for r in rejections)),
    }


def source(evidence, label, accent="", *, preview=True):
    pages = ", ".join(map(str, evidence["page_numbers"]))
    st.caption(f"{label} · p. {pages}")
    readable_text(
        evidence["text"], f"comparison-source {accent}", label=label + " 원문", expandable=preview
    )


def pdf_link(item_id, scope="all"):
    st.session_state.review_jump = item_id
    st.session_state.review_jump_scope = scope
    st.session_state.next_section = "PDF 검토"


def save_selection():
    st.session_state.comparison_selection = (
        st.session_state.comparison_claim,
        st.session_state.comparison_scope,
    )
    st.session_state.selected_claim = st.session_state.comparison_claim


def change_claim():
    st.session_state.comparison_scope = "all"
    save_selection()


def heading(title, kicker):
    st.markdown(
        f'<div class="comparison-card-heading"><span>{escape(kicker)}</span>'
        f"<h3>{escape(title)}</h3></div>",
        unsafe_allow_html=True,
    )


def render_evidence_comparison(result, initial_claim=None, initial_scope="all"):
    t = labels(result)
    key = result["analysis_id"]
    if st.session_state.get("comparison_id") != key:
        st.session_state.comparison_id = key
        st.session_state.comparison_model = build_review_model(result)
        st.session_state.comparison_selection = (
            result["patent"]["claims"][0]["claim_number"],
            "all",
        )
        for name in ("comparison_claim", "comparison_scope"):
            st.session_state.pop(name, None)
    model = st.session_state.comparison_model
    claims = {i["claim_number"]: i for i in model["items"] if i["kind"] == "claim"}
    if initial_claim in claims:
        scope = initial_scope if initial_scope in claims[initial_claim]["rejection_ids"] else "all"
        st.session_state.comparison_selection = (initial_claim, scope)
        st.session_state.comparison_claim = initial_claim
        st.session_state.comparison_scope = scope
    previous_claim, previous_scope = st.session_state.comparison_selection
    st.session_state.setdefault("comparison_claim", previous_claim)
    st.session_state.setdefault("comparison_scope", previous_scope)

    with st.container(key="evidence-comparison"):
        st.caption(t("선택한 청구항의 원문, 심사관 지적, 명세서 근거, 선행기술을 비교합니다."))
        with st.container(key="comparison-selectors"):
            left, right = st.columns([1, 2])
            with left:
                number = st.selectbox(
                    t("비교할 Claim"),
                    sorted(claims),
                    format_func=lambda n: t(f"Claim {n}"),
                    key="comparison_claim",
                    on_change=change_claim,
                )
            related = {
                r["rejection_id"]: r
                for r in model["rejections"]
                if r["rejection_id"] in claims[number]["rejection_ids"]
            }
            if st.session_state.comparison_scope not in related:
                st.session_state.comparison_scope = "all"
            with right:
                scope = st.selectbox(
                    t("비교할 지적 사유"),
                    ["all", *related],
                    key="comparison_scope",
                    format_func=lambda rid: (
                        "전체 연결 사유"
                        if rid == "all"
                        else f"{rid} · {display_statute(related[rid]['statute'])}"
                    ),
                    on_change=save_selection,
                )
        view = comparison_for_claim(model, number, scope)
        claim = view["claim"]
        st.session_state.comparison_selection = (number, scope)
        st.session_state.selected_claim = number
        statutes = " · ".join(map(display_statute, view["statutes"])) or "연결된 법조항 없음"
        parents = ", ".join(t(f"Claim {n}") for n in claim["depends_on"]) or "독립항"
        children = ", ".join(t(f"Claim {n}") for n in claim["children"]) or "없음"
        st.markdown(
            f'<div class="comparison-overview"><strong>{t("Claim")} {number}</strong>'
            f'<span class="claim-state {view["role"]}">{escape(t(view["status"]))}</span>'
            f"<span>{escape(statutes)}</span><span>명세서 연결 <b>{len(view['support'])}</b>개</span>"
            f"<span>인용문헌 <b>{len(view['citations'])}</b>개</span></div>",
            unsafe_allow_html=True,
        )
        focuses = []
        if any(re.search(r"\b112\b", law) for law in view["statutes"]):
            focuses.append(
                (
                    "112",
                    t("Claim ↔ 명세서 ↔ Office Action"),
                    "지적된 청구항 표현과 명세서 기재를 대조하세요.",
                )
            )
        if any(re.search(r"\b103\b", law) for law in view["statutes"]):
            focuses.append(
                (
                    "103",
                    t("Claim ↔ Office Action ↔ 선행기술"),
                    "심사관이 어떤 인용문헌을 근거로 지적했는지 확인하세요.",
                )
            )
        st.markdown(
            '<div class="comparison-focus">'
            + "".join(
                f'<div data-focus="{section}"><b>§{section} · {escape(path)}</b><span>{escape(prompt)}</span></div>'
                for section, path, prompt in focuses
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        with st.container(key="comparison-grid"):
            top_left, top_right = st.columns(2, gap="medium")
            with top_left, st.container(key="comparison-claim", border=True):
                heading("청구항 원문", t("01 / CLAIM"))
                st.markdown(
                    f"**{t('Claim')} {number} · {'종속항' if claim['depends_on'] else '독립항'}**"
                )
                source(claim["evidence"], t("Claim"), view["role"])
                st.caption(t("상위 Claim: ") + parents)
                st.caption(t("직접 종속 Claim: ") + children)
                st.button(
                    "PDF에서 보기",
                    key="comparison-claim-pdf",
                    on_click=pdf_link,
                    args=(claim["id"], scope),
                )
            with top_right, st.container(key="comparison-oa", border=True):
                heading(t("심사관 지적"), t("02 / OFFICE ACTION"))
                for rejection in view["rejections"]:
                    rid = rejection["rejection_id"]
                    direct = rid in claim["direct"]
                    role = "direct_rejection" if direct else "dependency"
                    st.markdown(
                        f'<div class="comparison-rejection" data-rejection="{escape(rid)}"><b>{escape(rid)} · '
                        f"{escape(display_statute(rejection['statute']))}</b> "
                        f'<span class="claim-state {role}">{"직접 지적" if direct else "종속 영향 · 직접 지적 아님"}</span></div>',
                        unsafe_allow_html=True,
                    )
                    source(rejection["evidence"], rid + t(" · Office Action"), role, preview=True)
                    st.button(
                        t("Office Action에서 보기"),
                        key=f"comparison-oa-{rid}",
                        on_click=pdf_link,
                        args=(f"rejection-{rid}", rid),
                    )
                if not view["rejections"]:
                    st.caption(t("이 Claim에 연결된 심사관 지적이 없습니다."))
            bottom_left, bottom_right = st.columns(2, gap="medium")
            with bottom_left, st.container(key="comparison-specification", border=True):
                heading("명세서 근거", t("03 / SPECIFICATION"))
                if view["support"]:
                    st.caption(
                        t(
                            "해당 지적 사유에서 명시적으로 언급한 위치입니다. 법적 뒷받침 여부를 자동 판정한 결과는 아닙니다."
                        )
                    )
                for item in view["support"]:
                    readable_text(t(item["title"]))
                    st.caption(
                        "연결 이유: "
                        + ", ".join(item["rejection_ids"])
                        + t("의 Office Action 원문이 이 위치를 명시적으로 언급합니다.")
                    )
                    source(item["evidence"], t(item["title"]), "specification")
                    st.button(
                        "명세서 PDF에서 보기",
                        key="comparison-spec-" + item["id"],
                        on_click=pdf_link,
                        args=(item["id"], item["rejection_ids"][0]),
                    )
                if not view["support"]:
                    st.markdown(
                        '<div class="comparison-empty">현재 자동 연결된 명세서 근거가 없습니다.</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("명세서 전체는 PDF 검토에서 확인할 수 있습니다.")
            with bottom_right, st.container(key="comparison-citations", border=True):
                heading("인용 선행기술", t("04 / CITED REFERENCES"))
                if view["citations"]:
                    st.caption(
                        t(
                            "같은 지적 사유에 인용된 문헌입니다. 문헌별 Claim 구성 대응을 자동 판정하지 않습니다."
                        )
                    )
                for entry in view["citations"]:
                    ref = entry["reference"]
                    kind = reference_kind(ref, t, unknown="문헌 유형 미확인")
                    publication = ref.get("publication_number") or " · ".join(
                        str(v) for v in (ref.get("publication"), ref.get("year")) if v
                    )
                    title = " · ".join(
                        v for v in (ref.get("name") or "이름 미확인", kind, publication) if v
                    )
                    with st.expander(title, expanded=False):
                        st.caption(
                            "문헌 역할: "
                            + {
                                "relied_upon": "거절 인용문헌",
                                "supporting_evidence": "보조 증거",
                                "not_relied_upon": "기록 문헌",
                            }.get(ref.get("citation_role", "relied_upon"))
                        )
                        readable_text("이름: " + (ref.get("name") or "기록 없음"))
                        readable_text(
                            "문헌 유형: " + kind
                            if t("Claim") == "청구항"
                            else "type: " + ref.get("type", "unknown")
                        )
                        readable_text(
                            t("Publication number: ")
                            + (ref.get("publication_number") or "기록 없음")
                        )
                        readable_text(
                            t("Publication / journal: ") + (ref.get("publication") or "기록 없음")
                        )
                        readable_text(
                            t("Year: ") + (str(ref["year"]) if ref.get("year") else "기록 없음")
                        )
                        st.caption(t("사용된 지적 사유: ") + ", ".join(entry["rejection_ids"]))
                        st.caption(
                            t("같은 지적 사유에 포함된 Claim: ")
                            + ", ".join(map(str, entry["claim_numbers"]))
                        )
                        for occurrence in entry["occurrences"]:
                            source(
                                occurrence["evidence"],
                                occurrence["rejection_id"] + t(" · OA 인용"),
                                "citation",
                            )
                        st.button(
                            "인용 위치에서 보기",
                            key="comparison-citation-" + ref["citation_id"],
                            on_click=pdf_link,
                            args=("citation-" + ref["citation_id"], entry["rejection_ids"][0]),
                        )
                if not view["citations"]:
                    st.caption("선택한 비교 범위에 연결된 인용문헌이 없습니다.")
        with st.container(key="comparison-summary", border=True):
            st.markdown("**비교 요약**")
            st.caption(
                f"{t('Claim')} {number} · {t(view['status'])} · 상위 {parents} · 직접 종속 {children}"
            )
            for rejection in view["rejections"]:
                claim_chips = "".join(
                    f'<span class="comparison-summary-chip">{n}</span>' for n in rejection["claims"]
                )
                references = (
                    "".join(
                        f'<span class="comparison-summary-reference">{escape(ref.get("name") or "이름 미확인")}'
                        + (
                            f" · {escape(ref['publication_number'])}"
                            if ref.get("publication_number")
                            else ""
                        )
                        + "</span>"
                        for ref in relied_references(rejection)
                    )
                    or '<span class="comparison-summary-empty">연결된 문헌 없음</span>'
                )
                st.markdown(
                    '<section class="comparison-summary-ground" '
                    f'data-rejection="{escape(rejection["rejection_id"])}">'
                    f"<h4>{escape(rejection['rejection_id'])} · "
                    f"{escape(display_statute(rejection['statute']))}</h4>"
                    f'<div class="comparison-summary-label">{t("대상 Claim")}</div>'
                    f'<div class="comparison-summary-claims">{claim_chips}</div>'
                    '<div class="comparison-summary-label">연결 문헌</div>'
                    f'<div class="comparison-summary-references">{references}</div>'
                    f'<div class="comparison-summary-label">{t("Office Action 요약")}</div>'
                    + text_html(rejection["reason_summary"], "comparison-summary-text preview")
                    + '<details class="comparison-summary-original"><summary>원문 더 보기</summary>'
                    f'<div class="comparison-summary-label">{t("Office Action 원문")} · p. '
                    + ", ".join(map(str, rejection["evidence"]["page_numbers"]))
                    + "</div>"
                    + text_html(rejection["evidence"]["text"], "comparison-summary-text")
                    + "</details></section>",
                    unsafe_allow_html=True,
                )
            if not view["rejections"]:
                st.caption(t("현재 분석 결과에 연결된 지적 사유가 없습니다."))
