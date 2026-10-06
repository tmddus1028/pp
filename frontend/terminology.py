from pathlib import Path

from backend.view.terminology import *  # noqa: F403  ponytail: shim until Streamlit is removed

TERMINOLOGY_JS = Path(__file__).with_name("terminology.js").read_text(encoding="utf-8")
