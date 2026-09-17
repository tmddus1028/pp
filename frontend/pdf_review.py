import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from frontend.improvements import component_reviews, prepare_session, request_improvement
from frontend.pdf_adapter import attach_coordinates, render_page, search_boxes
from frontend.readable_text import READABLE_CSS
from frontend.review_model import build_review_model
from frontend.terminology import TERMINOLOGY_JS, component_terms

_component = components.declare_component(
    "patent_pdf_review", path=str(Path(__file__).parent / "pdf_review_component")
)


def pdf_review(
    result, assets, initial_item=None, compare=False, initial_scope="all", reset_selection=False
):
    key = result["analysis_id"]
    prepare_session(result)
    context_claim = st.session_state.get("selected_claim")
    if st.session_state.get("review_model_id") != key:
        with st.spinner("원문과 검토 위치를 연결하고 있습니다…"):
            model = attach_coordinates(build_review_model(result), result, assets)
        for document in model["documents"]:
            data = assets.get(document["id"])
            document["pdf_download"] = base64.b64encode(data).decode() if data else None
        first = model["items"][0]
        st.session_state.review_model_id = key
        st.session_state.review_model = model
        st.session_state.review_ui = {
            "document": first["evidence"]["document_id"],
            "page": first["evidence"]["page_numbers"][0],
            "selected": None,
            "expanded": None,
            "viewer_evidence": None,
            "active_rejection": None,
            "scope": "all",
            "filter": "all",
            "checked": {},
            "zoom": 100,
            "fit": "width",
            "search": "",
        }
        st.session_state.review_images = {}
        st.session_state.review_searches = {}
        st.session_state.review_event = None
        st.session_state.review_navigation = 0
        st.session_state.selected_claim = None
    model, ui = st.session_state.review_model, st.session_state.review_ui
    ui.setdefault("expanded", None)
    ui.setdefault("viewer_evidence", ui.get("selected"))
    ui.setdefault("active_rejection", None)
    if reset_selection:
        ui.update(
            selected=None, expanded=None, viewer_evidence=None, active_rejection=None, filter="all"
        )
        st.session_state.selected_claim = None
        st.session_state.review_navigation += 1
    if initial_item:
        item = next((i for i in model["items"] if i["id"] == initial_item), None)
        if item:
            st.session_state.review_navigation += 1
            selection = item
            if item["kind"] == "rejection":
                selection = next(
                    (i for i in model["items"] if i["id"] == f"claim-{context_claim}"), None
                )
            ui.update(
                selected=selection["id"] if selection else None,
                expanded=selection["id"] if selection else None,
                viewer_evidence=item["id"],
                active_rejection=(
                    item["rejection_ids"][0] if item["kind"] == "rejection" else None
                ),
                document=item["evidence"]["document_id"],
                page=item["evidence"]["page_numbers"][0],
                filter="all",
                scope=initial_scope if initial_scope in item["rejection_ids"] else "all",
                search="",
            )
            st.session_state.selected_claim = selection.get("claim_number") if selection else None
    if compare and st.session_state.get("review_compare_entered") != key:
        oa = next(d for d in model["documents"] if d["kind"] == "office_action")
        ui.update(document=oa["id"], page=1)
        st.session_state.review_navigation += 1
        st.session_state.review_compare_entered = key
    document = next(d for d in model["documents"] if d["id"] == ui["document"])
    cache = st.session_state.review_images
    image_key = (ui["document"], ui["page"])
    if image_key not in cache:
        data = assets.get(ui["document"])
        try:
            cache[image_key] = (
                render_page(data, ui["page"])
                if data
                else {
                    "image": None,
                    "width": 612,
                    "height": 792,
                }
            )
        except (RuntimeError, ValueError, OSError) as exc:
            cache[image_key] = {
                "image": None,
                "width": 612,
                "height": 792,
                "error": f"PDF 페이지 렌더링 실패: {exc}",
            }
        if len(cache) > 12:
            del cache[next(iter(cache))]
    page = {
        **cache[image_key],
        "document": ui["document"],
        "number": ui["page"],
        "text": document["pages"][ui["page"] - 1]["text"],
        "search_query": ui.get("search", ""),
    }
    if ui.get("search") and assets.get(ui["document"]):
        search_key = (*image_key, ui["search"][:300])
        searches = st.session_state.review_searches
        if search_key not in searches:
            original = next(d for d in result["documents"] if d["document_id"] == ui["document"])
            words = original.get("metadata", {}).get("ocr_words", {})
            words = words.get(str(ui["page"]), words.get(ui["page"]))
            try:
                searches[search_key] = search_boxes(
                    assets[ui["document"]], ui["page"], page["text"], ui["search"][:300], words
                )
            except (RuntimeError, ValueError, OSError):
                searches[search_key] = []
            if len(searches) > 20:
                del searches[next(iter(searches))]
        page["search_boxes"] = searches[search_key]
    event = _component(
        improvements=component_reviews(),
        improvement_errors=st.session_state.get("improvement_errors", {}),
        terminology_js=TERMINOLOGY_JS,
        terminology=component_terms(result),
        readable_css=READABLE_CSS,
        model=model,
        ui=ui,
        page=page,
        navigation=st.session_state.review_navigation,
        key="pdf-" + key,
        default=None,
    )
    if (
        isinstance(event, dict)
        and event.get("nonce") != st.session_state.review_event
        and event.get("navigation") == st.session_state.review_navigation
    ):
        incoming = event.get("ui", {})
        doc = next((d for d in model["documents"] if d["id"] == incoming.get("document")), None)
        number = incoming.get("page")
        if doc and isinstance(number, int) and 1 <= number <= len(doc["pages"]):
            st.session_state.review_ui = {**ui, **{k: incoming[k] for k in ui if k in incoming}}
            st.session_state.review_event = event["nonce"]
            selected_item = next(
                (item for item in model["items"] if item["id"] == incoming.get("selected")), None
            )
            st.session_state.selected_claim = (
                selected_item.get("claim_number") if selected_item else None
            )
            if (
                event.get("action") == "improve_claim"
                and selected_item
                and selected_item["kind"] == "claim"
            ):
                rid = event.get("improvement_rejection")
                if rid is None or rid in selected_item["rejection_ids"]:
                    with st.spinner("관련 근거를 바탕으로 검토용 개선 방안을 준비합니다…"):
                        request_improvement(result, selected_item["claim_number"], rid)
            if (
                event.get("action") == "open_comparison"
                and selected_item
                and selected_item["kind"] == "claim"
            ):
                st.session_state.comparison_jump = selected_item["claim_number"]
                st.session_state.comparison_jump_scope = incoming.get("scope", "all")
                st.session_state.next_section = "근거 비교"
            if event.get("action") == "open_map":
                selected = incoming.get("selected")
                if any(item["id"] == selected for item in model["items"]):
                    st.session_state.relationship_jump = selected
                    st.session_state.relationship_jump_scope = incoming.get("scope", "all")
                else:
                    st.session_state.pop("relationship_jump", None)
                    st.session_state.pop("relationship_jump_scope", None)
                st.session_state.next_section = "관계 지도"
            st.rerun()
