import hashlib
import json
import os
import sys
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from frontend.claim_analysis import render_analysis  # noqa: E402
from frontend.evidence_comparison import render_evidence_comparison  # noqa: E402
from frontend.pdf_review import pdf_review  # noqa: E402
from frontend.readable_text import READABLE_CSS, observe_readable_overflow  # noqa: E402
from frontend.relationship_map import relationship_map  # noqa: E402
from frontend.terminology import labels  # noqa: E402
from frontend.visual_theme import BRAND_HTML, HERO_DECORATION, upload_header  # noqa: E402

st.set_page_config(page_title="Patent Review · PDF 검토", page_icon="▤", layout="wide")
load_dotenv(ROOT / ".env")
API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
st.markdown(
    "<style>"
    + (ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    + READABLE_CSS
    + "</style>",
    unsafe_allow_html=True,
)


def api_request(path, **kwargs):
    response = httpx.post(API_URL + path, timeout=600, **kwargs)
    if response.is_error:
        try:
            detail = response.json().get("detail", "분석 요청이 실패했습니다.")
        except ValueError:
            detail = "API 응답을 확인할 수 없습니다. 서버 상태를 확인하세요."
        raise ValueError(str(detail))
    return response.json()


def current_labels():
    return labels(
        st.session_state.get("result"),
        korean=st.session_state.get("upload_jurisdiction") == "한국 특허",
    )


@st.dialog("설정")
def settings_dialog():
    t = current_labels()
    st.write("현재 분석 모드: " + provider.upper())
    st.write("OCR과 PDF 화면 렌더링은 로컬에서 처리합니다.")
    if provider != "local":
        st.info(t("Office Action 텍스트는 설정된 LLM 공급자로 전송됩니다."))
    st.caption("분석 공급자와 OCR 실행 경로는 프로젝트의 .env 설정을 사용합니다.")


@st.dialog("PDF 검토 도움말")
def help_dialog():
    t = current_labels()
    st.write(
        "검토 카드를 선택하면 원문의 해당 페이지로 이동합니다. PDF 하이라이트를 클릭하면 연결된 카드가 열립니다."
    )
    st.write(
        "빨강은 직접 지적, 노랑은 종속 영향, 초록은 인용 문헌, 청록은 명시적으로 연결된 설명·근거입니다."
    )
    st.write(
        t(
            "종속항이라도 직접 지적된 경우에는 빨강이 우선합니다. 거절 사유 필터로 각 사유의 영향을 따로 볼 수 있습니다."
        )
    )
    st.write(
        t(
            "인용 문헌은 Office Action에서 인용된 위치를 보여줍니다. 명세서·도면은 원문에 명시된 연결만 표시합니다."
        )
    )
    st.caption(
        "좌표를 확실하게 찾지 못한 경우 원문 페이지와 텍스트 근거를 표시합니다. 이 도구는 전문적인 법률 검토를 대체하지 않습니다."
    )


if st.session_state.get("next_section"):
    st.session_state.section = st.session_state.pop("next_section")
try:
    provider = httpx.get(API_URL + "/health", timeout=3).json()["provider"]
except (httpx.HTTPError, ValueError, KeyError):
    provider = "연결 대기"

with st.sidebar:
    st.markdown(BRAND_HTML, unsafe_allow_html=True)
    st.caption("AI와 함께하는 특허 검토")
    st.divider()
    section = st.radio(
        "작업 공간",
        ["문서 업로드", "PDF 검토", "청구항 분석", "관계 지도", "근거 비교"],
        key="section",
        label_visibility="collapsed",
    )
    st.markdown('<div class="sidebar-space"></div>', unsafe_allow_html=True)
    if st.button("⚙  설정", key="settings_nav", width="stretch"):
        settings_dialog()
    if st.button("?  도움말", key="help_nav", width="stretch"):
        help_dialog()
    st.caption(provider.upper() + " · Patent Review")

previous_section = st.session_state.get("previous_section")
section_changed = previous_section != section
if section_changed:
    st.session_state.previous_section = section
    # A sidebar click can arrive in the same rerun as the component's last choice.
    # Consume that already-delivered value before deriving the destination's context.
    prefix = {"PDF 검토": ("pdf", "review"), "관계 지도": ("relationships", "relationship")}.get(
        previous_section
    )
    if prefix and "result" in st.session_state:
        widget, state_key = prefix
        pending = st.session_state.get(widget + "-" + st.session_state.result["analysis_id"])
        ui = st.session_state.get(state_key + "_ui")
        if (
            isinstance(pending, dict)
            and ui is not None
            and pending.get("navigation") == st.session_state.get(state_key + "_navigation")
            and pending.get("nonce") != st.session_state.get(state_key + "_event")
        ):
            incoming = pending.get("ui", {})
            model = st.session_state[state_key + "_model"]
            choices = model["items"] if state_key == "review" else model["nodes"]
            selected = incoming.get("selected")
            if selected is None or any(item["id"] == selected for item in choices):
                st.session_state[state_key + "_ui"] = {
                    **ui,
                    **{k: incoming[k] for k in ui if k in incoming},
                }
                st.session_state[state_key + "_event"] = pending["nonce"]
                if state_key == "review":
                    item = next((i for i in choices if i["id"] == selected), {})
                    st.session_state.selected_claim = item.get("claim_number")


def change_jurisdiction():
    st.session_state.upload_jurisdiction = st.session_state.jurisdiction_selector
    # A country switch must not display the previous country's analysis/assets.
    for key in ("result", "pdf_assets"):
        st.session_state.pop(key, None)
    for key in (
        "improvement_identity",
        "improvement_results",
        "improvement_errors",
        "improvement_open",
        "revision_results",
        "revision_errors",
        "revision_drafts",
    ):
        st.session_state.pop(key, None)


def upload_documents():
    t = current_labels()
    with st.container(key="upload-hero"):
        st.caption(t("WORKSPACE / DOCUMENTS"))
        st.title("원문을 펼치고, 검토를 시작하세요.")
        st.write(
            t("같은 시점의 청구항과 Office Action을 연결하여 원문에서 검토 근거를 확인합니다.")
        )
        st.markdown(HERO_DECORATION, unsafe_allow_html=True)
    with st.container(key="upload-options"):
        country_column, input_column = st.columns([1, 2], gap="large")
    jurisdiction = country_column.radio(
        "특허 관할",
        ["미국 특허", "한국 특허"],
        index=1 if st.session_state.get("upload_jurisdiction") == "한국 특허" else 0,
        horizontal=True,
        key="jurisdiction_selector",
        on_change=change_jurisdiction,
        label_visibility="collapsed",
    )
    korean = jurisdiction == "한국 특허"
    st.session_state.upload_jurisdiction = jurisdiction
    api_suffix = "?jurisdiction=KR" if korean else ""
    input_prefix = "kr_" if korean else ""
    mode = input_column.radio(
        "입력 방법", ["파일 업로드", "텍스트 입력"], horizontal=True, key="input_mode"
    )
    first, second = st.columns(2, gap="large")
    files = []
    reference_files = []
    if mode == "파일 업로드":
        with first, st.container(border=True, key="upload-card-patent"):
            st.markdown(
                upload_header(t("01 · Patent / Claims"), "검토할 특허·청구항 원문"),
                unsafe_allow_html=True,
            )
            st.subheader(t("01 · Patent / Claims"))
            st.caption("검토할 특허·청구항 원문")
            patent = st.file_uploader(
                t("Patent PDF"),
                type=["pdf", "txt"] if korean else ["pdf", "txt", "json"],
                key=input_prefix + "patent_upload",
            )
        with second, st.container(border=True, key="upload-card-oa"):
            st.markdown(
                upload_header(t("02 · Office Action"), t("해당 청구항에 대한 심사 의견서")),
                unsafe_allow_html=True,
            )
            st.subheader(t("02 · Office Action"))
            st.caption(t("해당 청구항에 대한 심사 의견서"))
            oa = st.file_uploader(
                "의견제출통지서 XML / PDF" if korean else t("Office Action PDF"),
                type=["xml", "pdf"] if korean else ["pdf", "txt", "json"],
                key=input_prefix + "oa_upload",
            )
            if korean:
                with st.expander("인용발명 원문 (선택)", expanded=False):
                    refs = st.file_uploader(
                        "인용발명 PDF",
                        type=["pdf"],
                        accept_multiple_files=True,
                        key="kr_reference_upload",
                    )
                    reference_files = [(ref.name, ref.getvalue()) for ref in refs]
        ready = patent is not None and oa is not None
        if ready:
            files = [(patent.name, patent.getvalue()), (oa.name, oa.getvalue())]
    else:
        patent_text = first.text_area(
            t("01 · Patent / Claims"), height=280, key=input_prefix + "patent_text"
        )
        oa_text = second.text_area(
            t("02 · Office Action"), height=280, key=input_prefix + "oa_text"
        )
        ready = bool(patent_text.strip() and oa_text.strip())
    run, demo, _ = st.columns([1, 1.5, 3])
    analyze_clicked = run.button(
        "분석 시작", type="primary", disabled=not ready, key="analyze", width="stretch"
    )
    demo_clicked = demo.button("예제 분석 · 가상 문서", key="demo", width="stretch")
    st.caption(
        "PDF 원본은 변경하지 않습니다. TXT/XML 입력은 텍스트 원문으로 검토할 수 있습니다."
        if korean
        else "PDF 원본은 변경하지 않습니다. TXT/JSON 입력은 텍스트 원문으로 검토할 수 있습니다."
    )
    if analyze_clicked or demo_clicked:
        try:
            with st.spinner(t("청구항과 지적 사유를 분석하고 있습니다…")):
                if demo_clicked:
                    demo_patent = "kr_demo_patent.txt" if korean else "demo_patent.txt"
                    demo_oa = "kr_demo_office_action.xml" if korean else "demo_office_action.txt"
                    result = api_request(
                        "/analyze/text" + api_suffix,
                        json={
                            "patent_text": (ROOT / "data/raw" / demo_patent).read_text(
                                encoding="utf-8"
                            ),
                            "office_action_text": (ROOT / "data/raw" / demo_oa).read_text(
                                encoding="utf-8"
                            ),
                        },
                    )
                    files = []
                elif mode == "파일 업로드":
                    result = api_request(
                        "/analyze/files" + api_suffix,
                        files=[
                            ("patent", files[0]),
                            ("office_action", files[1]),
                            *[("references", ref) for ref in reference_files],
                        ],
                    )
                else:
                    result = api_request(
                        "/analyze/text" + api_suffix,
                        json={"patent_text": patent_text, "office_action_text": oa_text},
                    )
            st.session_state.result = result
            st.session_state.pdf_assets = {
                document["document_id"]: data
                for document in result["documents"]
                for name, data in files + reference_files
                if Path(name).suffix.lower() == ".pdf"
                and document["filename"] == name
                and (
                    not korean
                    or document["document_id"].endswith(hashlib.sha256(data).hexdigest()[:16])
                )
            }
            for key in [
                "improvement_identity",
                "review_model_id",
                "claim_list_id",
                "comparison_id",
                "review_compare_entered",
                "selected_claim",
                "selected_citation",
                "last_graph_choice",
                "last_citation_choice",
                "relationship_model_id",
                "relationship_jump",
                "relationship_jump_scope",
                "review_jump",
                "review_jump_scope",
                "comparison_jump",
                "comparison_jump_scope",
            ]:
                st.session_state.pop(key, None)
            st.session_state.next_section = "PDF 검토"
            st.rerun()
        except httpx.HTTPError:
            st.error(
                "API에 연결할 수 없거나 응답 시간이 초과되었습니다. backend 실행 상태를 확인하세요."
            )
        except ValueError as exc:
            st.error(str(exc))
    if "result" not in st.session_state:
        st.markdown(
            '<div class="upload-note"><b>원문과 설명을 나란히</b><br>검토 카드와 하이라이트를 오가며 지적 사유, 인용문헌, 종속관계를 확인하세요.</div>',
            unsafe_allow_html=True,
        )


if section == "문서 업로드":
    upload_documents()
elif "result" not in st.session_state:
    st.title(section)
    st.info(current_labels()("먼저 Patent와 Office Action을 업로드하여 분석을 시작하세요."))
    if st.button("문서 업로드로 이동"):
        st.session_state.next_section = "문서 업로드"
        st.rerun()
else:
    result = st.session_state.result
    st.caption(
        current_labels()(
            "WORKSPACE / "
            + {
                "청구항 분석": "CLAIM ANALYSIS",
                "관계 지도": "RELATIONSHIP MAP",
                "근거 비교": "EVIDENCE COMPARISON",
            }.get(section, "DOCUMENT REVIEW")
        )
    )
    st.title(section)
    if section == "청구항 분석":
        render_analysis(result)
    elif section == "근거 비교":
        number = st.session_state.pop("comparison_jump", None)
        scope = st.session_state.pop("comparison_jump_scope", "all")
        if number is None and section_changed:
            if previous_section in ("PDF 검토", "청구항 분석"):
                number = st.session_state.get("selected_claim")
                if previous_section == "PDF 검토":
                    scope = st.session_state.get("review_ui", {}).get("scope", "all")
            elif previous_section == "관계 지도":
                selected = st.session_state.get("relationship_ui", {}).get("selected")
                node = next((n for n in result["graph"]["nodes"] if n["id"] == selected), {})
                number = node.get("claim_number")
                scope = st.session_state.get("relationship_ui", {}).get("scope", "all")
        render_evidence_comparison(result, initial_claim=number, initial_scope=scope)
    elif section == "관계 지도":
        relationship_map(
            result,
            initial_item=st.session_state.pop("relationship_jump", None),
            initial_scope=st.session_state.pop("relationship_jump_scope", "all"),
        )
    else:
        pdf_review(
            result,
            st.session_state.get("pdf_assets", {}),
            initial_item=st.session_state.pop("review_jump", None),
            initial_scope=st.session_state.pop("review_jump_scope", "all"),
            reset_selection=section_changed,
        )
        with st.expander("문서 처리 안내 및 분석 결과"):
            for document in result["documents"]:
                metadata = document.get("metadata", {})
                if metadata.get("ocr_used"):
                    pages = metadata.get("ocr_pages", [])
                    st.info(
                        f"{document['filename']}: 스캔 PDF가 감지되어 OCR을 수행했습니다. ({len(pages)}페이지)"
                    )
                    st.caption("OCR 페이지: " + ", ".join(map(str, pages)))
                with st.expander(document["filename"] + " · 추출 원문"):
                    st.code(document["text"], language=None, wrap_lines=True)
                    if metadata.get("ocr_raw_text"):
                        st.caption("OCR 엔진 원문 · 보정하지 않은 출력")
                        for text in metadata["ocr_raw_text"].values():
                            st.code(text, language=None, wrap_lines=True)
            for warning in result["warnings"]:
                st.caption(warning)
            st.download_button(
                "분석 JSON 다운로드",
                json.dumps(result, ensure_ascii=False, indent=2),
                file_name=f"patent-review-{result['analysis_id']}.json",
                mime="application/json",
            )

observe_readable_overflow()
