"""Shared source-text presentation; escaping preserves every original character."""

from html import escape
from pathlib import Path

import streamlit as st

READABLE_CSS = Path(__file__).with_suffix(".css").read_text(encoding="utf-8")


def text_html(text, class_name="", *, label=None, collapsed_lines=5, expandable=False):
    # Literal blank lines otherwise let Markdown reinterpret embedded HTML as paragraphs.
    content = escape(text).replace("\r", "&#13;").replace("\n", "&#10;").replace("\t", "&#9;")
    attributes = f' role="region" tabindex="0" aria-label="{escape(label)}"' if label else ""
    html = (
        f'<div class="readable-text {escape(class_name)}"{attributes}>'
        f'<span class="readable-text-content">{content}</span></div>'
    )
    if expandable:
        lines = max(1, int(collapsed_lines))
        html = (
            f'<div class="readable-panel" style="--readable-lines:{lines}">{html}'
            '<details class="readable-toggle"><summary><span class="readable-more">더 보기</span>'
            '<span class="readable-less">접기</span></summary></details></div>'
        )
    return html


def readable_text(text, class_name="", **options):
    st.markdown(text_html(text, class_name, **options), unsafe_allow_html=True)
