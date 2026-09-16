"""Read-only presentation of the existing graph; no analysis or PDF processing."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from frontend.readable_text import READABLE_CSS, READABLE_JS
from frontend.review_model import build_review_model

_component = components.declare_component(
    "patent_relationship_map", path=str(Path(__file__).parent / "relationship_map_component")
)


def build_relationship_model(result):
    review = build_review_model(result)
    items = {item["id"]: item for item in review["items"]}
    nodes = []
    for node in result["graph"]["nodes"]:
        item_id = {
            "claim": f"claim-{node.get('claim_number')}",
            "citation": f"citation-{node['id']}",
            "rejection": f"rejection-{node['id']}",
        }.get(node["kind"])
        nodes.append({**node, "item_id": item_id if item_id in items else None})
    return {
        "analysis_id": result["analysis_id"],
        "nodes": nodes,
        "edges": [
            {key: edge.get(key) for key in ("source", "target", "relation", "citation_role")}
            for edge in result["graph"]["edges"]
        ],
        "items": list(items.values()),
        "rejections": review["rejections"],
        "impacts": review["impacts"],
        "documents": [{"filename": d["filename"], "kind": d["kind"]} for d in review["documents"]],
    }


def relationship_map(result, initial_item=None, initial_scope="all"):
    key = result["analysis_id"]
    if st.session_state.get("relationship_model_id") != key:
        st.session_state.relationship_model_id = key
        st.session_state.relationship_model = build_relationship_model(result)
        st.session_state.relationship_ui = {
            "selected": None,
            "filter": "all",
            "scope": "all",
            "direct_only": False,
            "dependencies": False,
            "citations": True,
            "expanded": [],
        }
        st.session_state.relationship_event = None
        st.session_state.relationship_navigation = 0
    model = st.session_state.relationship_model
    if initial_item:
        node = next((n for n in model["nodes"] if n["item_id"] == initial_item), None)
        item = next((i for i in model["items"] if i["id"] == initial_item), None)
        if node is None and item and item["rejection_ids"]:
            node = next((n for n in model["nodes"] if n["id"] == item["rejection_ids"][0]), None)
        if node:
            st.session_state.relationship_ui.update(
                selected=node["id"],
                filter="all",
                scope=initial_scope if item and initial_scope in item["rejection_ids"] else "all",
                direct_only=False,
                dependencies=node["kind"] == "claim",
                citations=True,
            )
            st.session_state.relationship_navigation += 1
    event = _component(
        readable_css=READABLE_CSS,
        readable_js=READABLE_JS,
        model=model,
        ui=st.session_state.relationship_ui,
        navigation=st.session_state.relationship_navigation,
        key="relationships-" + key,
        default=None,
    )
    if (
        isinstance(event, dict)
        and event.get("nonce") != st.session_state.relationship_event
        and event.get("navigation") == st.session_state.relationship_navigation
    ):
        incoming = event.get("ui", {})
        selected = incoming.get("selected")
        if selected is not None and not any(n["id"] == selected for n in model["nodes"]):
            return
        ui = st.session_state.relationship_ui
        st.session_state.relationship_ui = {**ui, **{k: incoming[k] for k in ui if k in incoming}}
        st.session_state.relationship_event = event["nonce"]
        if event.get("action") == "open_comparison":
            node = next((n for n in model["nodes"] if n["id"] == selected), None)
            if node and node["kind"] == "claim" and node["item_id"]:
                st.session_state.comparison_jump = node["claim_number"]
                st.session_state.comparison_jump_scope = incoming.get("scope", "all")
                st.session_state.next_section = "근거 비교"
        if event.get("action") == "open_pdf":
            node = next((n for n in model["nodes"] if n["id"] == selected), None)
            if node and node["item_id"]:
                st.session_state.review_jump = node["item_id"]
                st.session_state.review_jump_scope = incoming.get("scope", "all")
                st.session_state.next_section = "PDF 검토"
        st.rerun()
