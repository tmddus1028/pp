from io import BytesIO
from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from backend.config import Settings
from backend.ingestion.adapters import from_text
from backend.service import analyze

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings():
    return Settings(_env_file=None, llm_provider="local")


@pytest.fixture
def patent_text():
    return (ROOT / "data/raw/demo_patent.txt").read_text(encoding="utf-8")


@pytest.fixture
def oa_text():
    return (ROOT / "data/raw/demo_office_action.txt").read_text(encoding="utf-8")


@pytest.fixture
def result(patent_text, oa_text, settings):
    return analyze(
        from_text(patent_text, "patent.txt", "patent"),
        from_text(oa_text, "oa.txt", "office_action"),
        settings,
    )


def make_pdf(pages):
    output = BytesIO()
    pdf = canvas.Canvas(output)
    for text in pages:
        obj = pdf.beginText(50, 780)
        obj.setFont("Helvetica", 10)
        for line in text.splitlines():
            obj.textLine(line)
        pdf.drawText(obj)
        pdf.showPage()
    pdf.save()
    return output.getvalue()
