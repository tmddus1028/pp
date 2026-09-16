from pathlib import Path

import streamlit.components.v1 as components

_component = components.declare_component(
    "patent_impact_graph", path=str(Path(__file__).parent / "graph_component")
)


def impact_graph(graph: dict, key: str):
    return _component(graph=graph, key=key, default=None)
