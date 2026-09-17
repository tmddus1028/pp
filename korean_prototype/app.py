"""Independent Korean patent review UI; no dependency on the US application."""

import hashlib
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kr_review.models import AnalysisResult, Evidence, ReviewError  # noqa: E402


def review_widget_key(name: str) -> str:
    """Give each successful analysis fresh widgets, even when options are identical."""
    return f"{name}__{st.session_state.get('kr_analysis_generation', 0)}"


def reset_review() -> None:
    """Reset only this prototype's review state for a new analysis."""
    for key in list(st.session_state):
        if key.startswith(("kr_claim", "kr_source", "kr_azure")):
            del st.session_state[key]
    st.session_state.kr_analysis_generation = st.session_state.get("kr_analysis_generation", 0) + 1


def analyze_documents(
    patent_data: bytes,
    patent_filename: str,
    oa_data: bytes,
    oa_filename: str,
    references: list[tuple[str, bytes]],
) -> None:
    from kr_review.service import analyze

    result = analyze(
        patent_data,
        patent_filename,
        oa_data,
        oa_filename,
        references=references,
    )
    reset_review()
    st.session_state.kr_result = result
    uploads = [
        ("patent", patent_data),
        ("office_action", oa_data),
        *(("reference", data) for _, data in references),
    ]
    # Match ingestion's source identity: filenames are labels, not unique keys.
    st.session_state.kr_files = {
        f"{kind}_{hashlib.sha256(data).hexdigest()[:16]}": data for kind, data in uploads
    }


def source_target(evidence: Evidence) -> None:
    st.session_state[review_widget_key("kr_source_document")] = evidence.document_id
    st.session_state[review_widget_key("kr_source_page")] = (
        evidence.page_numbers[0] if evidence.page_numbers else 1
    )
    st.session_state.kr_source_evidence = evidence


def evidence_location(result: AnalysisResult, evidence: Evidence) -> str:
    document = next(item for item in result.documents if item.document_id == evidence.document_id)
    location = document.filename
    if evidence.page_numbers:
        location += " · p. " + ", ".join(map(str, evidence.page_numbers))
    elif evidence.xml_path:
        location += " · XML " + evidence.xml_path
    return location


def original_text(text: str) -> None:
    # st.text preserves source content; CSS controls wrapping without rewriting it.
    with st.container(border=True):
        st.text(text, width="stretch")


def evidence_block(
    result: AnalysisResult, evidence: Evidence, key: str, *, collapsed: bool = False
) -> None:
    st.caption(evidence_location(result, evidence))
    if collapsed:
        with st.expander("원문 펼치기", expanded=False):
            original_text(evidence.text)
    else:
        original_text(evidence.text)
    st.button(
        "원문 위치 선택",
        key=key,
        on_click=source_target,
        args=(evidence,),
        help="원문 확인 탭의 문서와 페이지를 이 근거 위치로 설정합니다.",
    )


def claim_status(result: AnalysisResult, number: int) -> str:
    if number in result.direct_claims:
        return "직접 지적"
    if number in result.dependency_claims:
        return "종속 영향"
    claim = next(item for item in result.claims if item.number == number)
    return "취소" if claim.status == "canceled" else "지적 연결 없음"


def render_claims(result: AnalysisResult) -> None:
    number = st.selectbox(
        "검토할 청구항",
        [claim.number for claim in result.claims],
        index=None,
        placeholder="청구항을 선택하세요",
        format_func=lambda value: f"청구항 {value} · {claim_status(result, value)}",
        key=review_widget_key("kr_claim_selection"),
    )
    if number is None:
        st.caption("청구항을 선택하면 원문과 연결된 거절 사유를 확인할 수 있습니다.")
        return
    claim = next(item for item in result.claims if item.number == number)
    linked = [item for item in result.rejections if number in item.claims]
    st.subheader(f"청구항 {number} · {claim_status(result, number)}")
    parents = ", ".join(f"청구항 {value}" for value in claim.depends_on) or "독립항"
    st.caption("상위 청구항: " + parents)
    if linked:
        st.write("적용 법조항: " + " · ".join(dict.fromkeys(x.statute for x in linked)))
    st.markdown("**청구항 원문**")
    evidence_block(result, claim.evidence, f"kr_claim_original_{number}")
    st.markdown("**심사관 지적**")
    if not linked:
        st.caption("이 청구항에 직접 연결된 거절 사유가 없습니다.")
        if number in result.dependency_claims:
            st.caption("거절된 상위 청구항과의 종속관계에 따라 추가 검토 대상으로 표시됩니다.")
    for rejection in linked:
        with st.expander(f"{rejection.rejection_id} · {rejection.statute}", expanded=False):
            st.caption("대상 청구항: " + ", ".join(map(str, rejection.claims)))
            evidence_block(
                result,
                rejection.evidence,
                f"kr_claim_rejection_{number}_{rejection.rejection_id}",
            )
            citations = [
                item for item in result.citations if item.citation_id in rejection.citation_ids
            ]
            st.markdown("**거절에 사용된 인용문헌**")
            for citation in citations:
                st.write(citation.publication_number + " " + citation.title)
                if citation.document_id:
                    document = next(
                        item
                        for item in result.documents
                        if item.document_id == citation.document_id
                    )
                    st.button(
                        "인용문헌 원문 위치 선택",
                        key=f"kr_claim_reference_{number}_{rejection.rejection_id}_{citation.citation_id}",
                        on_click=source_target,
                        args=(
                            Evidence(
                                document_id=document.document_id,
                                text="",
                                start=0,
                                end=0,
                                page_numbers=[1] if document.pages else [],
                            ),
                        ),
                    )
                else:
                    st.caption("인용문헌 원본이 업로드되지 않았습니다.")


@st.cache_data(show_spinner=False, max_entries=24)
def render_pdf_page(data: bytes, page_number: int) -> bytes:
    from io import BytesIO

    import pypdfium2 as pdfium

    with pdfium.PdfDocument(data) as document:
        page = document[page_number - 1]
        try:
            bitmap = page.render(scale=1.5)
            try:
                image = bitmap.to_pil()
                output = BytesIO()
                image.save(output, format="PNG")
                return output.getvalue()
            finally:
                bitmap.close()
        finally:
            page.close()


def change_source_document() -> None:
    st.session_state[review_widget_key("kr_source_page")] = 1
    st.session_state.pop("kr_source_evidence", None)


def render_source(result: AnalysisResult) -> None:
    documents = {item.document_id: item for item in result.documents}
    kind_labels = {"patent": "특허", "office_action": "의견제출통지서", "reference": "인용문헌"}
    labels = {
        item.document_id: (
            f"{item.filename} · {kind_labels[item.kind]} · {item.document_id[-6:]}"
            if sum(other.filename == item.filename for other in result.documents) > 1
            else item.filename
        )
        for item in result.documents
    }
    document_id = st.selectbox(
        "원문 문서",
        list(documents),
        index=None,
        placeholder="원문 문서를 선택하세요",
        format_func=lambda value: labels[value],
        key=review_widget_key("kr_source_document"),
        on_change=change_source_document,
    )
    if not document_id:
        st.caption("문서를 고르거나 청구항 검토의 ‘원문 위치 선택’을 누르세요.")
        return
    document = documents[document_id]
    data = st.session_state.kr_files.get(document_id)
    if data:
        st.download_button(
            "원본 파일 다운로드",
            data=data,
            file_name=document.filename,
            key=f"kr_source_download_{document_id}",
        )
    evidence = st.session_state.get("kr_source_evidence")
    if evidence and evidence.document_id == document_id and evidence.text:
        with st.expander("선택한 원문 근거", expanded=True):
            st.caption(evidence_location(result, evidence))
            original_text(evidence.text)
    if document.filename.lower().endswith(".pdf") and data and document.pages:
        page_count = max(page.number for page in document.pages)
        page_key = review_widget_key("kr_source_page")
        st.session_state[page_key] = max(1, min(st.session_state.get(page_key, 1), page_count))
        page_number = st.number_input("PDF 페이지", min_value=1, max_value=page_count, key=page_key)
        st.caption(f"전체 {page_count}쪽 · 원본 PDF 페이지")
        try:
            st.image(render_pdf_page(data, int(page_number)), width="stretch")
        except Exception as exc:
            st.warning(f"PDF 미리보기를 표시할 수 없습니다. 원본을 다운로드하세요. ({exc})")
        with st.expander("이 페이지에서 추출된 원문", expanded=False):
            page = next(item for item in document.pages if item.number == page_number)
            original_text(page.text)
    else:
        if document.filename.lower().endswith(".xml"):
            st.caption("XML 원문에는 PDF 페이지 번호가 없습니다. 근거의 XML 경로를 표시합니다.")
        with st.expander("문서 전체 추출 원문", expanded=False):
            original_text(document.text)


def render_azure(result: AnalysisResult) -> None:
    st.caption(
        "선택한 청구항과 연결 근거를 Azure로 검토합니다. "
        "버튼을 누를 때만 전송하며, 로컬 추출 결과와 원문은 유지합니다."
    )
    number = st.session_state.get(review_widget_key("kr_claim_selection"))
    if number is None:
        st.info("청구항 검토 탭에서 먼저 청구항을 선택하세요.")
        return
    st.write(f"검토 대상: 청구항 {number}")
    st.caption("결과는 검토 초안입니다. 제안한 수정은 원문 근거와 함께 확인하세요.")
    if st.button("Azure로 검토", key="kr_azure_run"):
        try:
            from kr_review.review import analyze_with_azure

            with st.spinner("연결된 원문 근거를 Azure로 검토하고 있습니다."):
                review = analyze_with_azure(result, number)
            st.session_state.kr_azure_results = {
                **st.session_state.get("kr_azure_results", {}),
                number: review,
            }
        except (ReviewError, ValueError) as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Azure 검토를 완료하지 못했습니다: {exc}")
    review = st.session_state.get("kr_azure_results", {}).get(number)
    if not review:
        return
    payload = review.model_dump() if hasattr(review, "model_dump") else review
    for warning in payload.get("warnings", []):
        st.warning(warning)
    for finding in payload.get("findings", []):
        st.markdown("**" + finding["topic"] + "**")
        st.write(finding["analysis"])
        st.caption("원문 근거: " + ", ".join(finding.get("evidence_ids", [])))
    st.markdown("**검토 제안**")
    for suggestion in payload.get("suggestions", []):
        st.write(suggestion["text"])
        st.caption("원문 근거: " + ", ".join(suggestion.get("evidence_ids", [])))
    with st.expander("검토에 사용된 원문 근거", expanded=False):
        for source in payload.get("sources", []):
            st.write(source["evidence_id"] + " · " + source["filename"])
            if source.get("page_numbers"):
                st.caption("p. " + ", ".join(map(str, source["page_numbers"])))
            if source.get("xml_path"):
                st.caption(source["xml_path"])
            original_text(source["text"])


def main() -> None:
    st.set_page_config(page_title="Patent Review · 한국어 프로토타입", layout="wide")
    st.markdown(
        """<style>
        .block-container { max-width: 1500px; padding-top: 2rem; }
        [data-testid="stText"], [data-testid="stText"] pre {
            display: block; width: 100%; max-width: 100%; min-width: 0;
            white-space: normal; word-break: normal; overflow-wrap: break-word;
            line-height: 1.65; text-align: left; font-family: inherit;
        }
        [data-testid="stVerticalBlock"], [data-testid="stMarkdownContainer"] {
            min-width: 0;
        }
        [data-testid="stText"] { background: #f6f8fa; padding: 12px;
            border-radius: 6px; box-sizing: border-box; }
        </style>""",
        unsafe_allow_html=True,
    )
    st.title("Patent Review · 한국어 프로토타입")
    st.caption("기존 미국 버전과 별도로 실행하는 한국 특허 검토 화면입니다.")
    with st.sidebar:
        st.subheader("한국 문서 분석")
        st.caption("특허 PDF/TXT와 KIPRIS 의견제출통지서 XML을 지원합니다.")
        if st.button("한국 사례 분석", type="primary", width="stretch"):
            try:
                from kr_review.sample import sample_inputs

                with st.spinner("한국 공개특허와 의견제출통지서를 읽고 있습니다."):
                    analyze_documents(**sample_inputs())
            except (OSError, ReviewError, ValueError) as exc:
                st.error(str(exc))
        st.caption("사례: 10-2019-0000844 · 전자쿠폰 시스템")
        with st.expander("직접 문서 업로드", expanded=False):
            patent = st.file_uploader(
                "한국 특허·청구항", type=["pdf", "txt"], key="kr_upload_patent"
            )
            oa = st.file_uploader("의견제출통지서", type=["xml"], key="kr_upload_oa")
            references = st.file_uploader(
                "인용문헌 PDF (선택)",
                type=["pdf"],
                accept_multiple_files=True,
                key="kr_upload_references",
            )
            if st.button("업로드 문서 분석", disabled=not (patent and oa)):
                try:
                    with st.spinner("업로드한 문서를 분석하고 있습니다."):
                        analyze_documents(
                            patent.getvalue(),
                            patent.name,
                            oa.getvalue(),
                            oa.name,
                            [(item.name, item.getvalue()) for item in references],
                        )
                except (OSError, ReviewError, ValueError) as exc:
                    st.error(str(exc))
    result = st.session_state.get("kr_result")
    if result is None:
        st.info("‘한국 사례 분석’을 누르면 확보한 한국 문서 한 쌍을 바로 검토할 수 있습니다.")
        return
    st.subheader(result.title or "한국 특허 분석 결과")
    st.caption(f"출원번호 {result.application_number} · 의견제출통지 {result.office_action_date}")
    columns = st.columns(4)
    for column, label, value in zip(
        columns,
        ("전체 청구항", "직접 지적", "종속 영향", "인용문헌"),
        (
            len(result.claims),
            len(result.direct_claims),
            len(result.dependency_claims),
            len(result.citations),
        ),
        strict=True,
    ):
        column.metric(label, value)
    with st.expander("문서 처리 정보", expanded=False):
        st.caption("로컬 규칙으로 추출한 구조 정보입니다. Azure 검토는 별도 실행합니다.")
        for warning in result.warnings:
            st.warning(warning)
        for document in result.documents:
            st.write(document.filename)
            st.json(document.metadata, expanded=False)
    claims_tab, source_tab, azure_tab = st.tabs(["청구항 검토", "원문 확인", "Azure 검토"])
    with claims_tab:
        render_claims(result)
    with source_tab:
        render_source(result)
    with azure_tab:
        render_azure(result)


if __name__ == "__main__":
    main()
