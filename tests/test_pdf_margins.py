import re
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from backend.ingestion.adapters import LocalAdapter, from_pages
from backend.ingestion.margin_cleaner import clean_patent_margins
from backend.ingestion.text_cleaner import clean_text
from backend.patent.patent_parser import parse_patent
from backend.schemas import OCRMetadata


def patent_pdf():
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=(612, 792))
    pages = [
        ["Claims", "1. A method of treating cancer with indazol-"],
        [
            "3-yl)-2-((R)-2-methoxy-1-methyl-ethylamino).",
            "The label contains US 2020/0123456 A1 and a date May 7, 2020.",
            "US 2020/0123456 A1",
            "Patent Application Publication",
            "May 7, 2020",
            "123",
            "2. The method of claim 1, wherein the chemical is administered.",
        ],
    ]
    for number, lines in enumerate(pages, 1):
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, 762, "EXAMPLE RUNNING HEADER")
        pdf.drawString(50, 738, "Patent Application Publication")
        pdf.drawString(50, 718, "US 2020/0123456 A1")
        for i, line in enumerate(lines):
            pdf.drawString(50, 650 - i * 22, line)
        # Deliberately emit this header after body: PDF reading order != geometry.
        pdf.drawString(410, 738, "May 7, 2020")
        pdf.drawString(50, 20, "EXAMPLE RUNNING FOOTER")
        pdf.drawString(300, 20, str(number))
        pdf.showPage()
    pdf.save()
    return output.getvalue(), pages


def test_repeated_headers_removed_and_body_preserved(settings):
    data, body = patent_pdf()
    with patch("backend.ingestion.pdf_reader.ocr_pdf_pages") as ocr:
        doc = LocalAdapter(settings).read(data, "patent.pdf", "patent")
    ocr.assert_not_called()
    assert [p.text for p in doc.pages] == ["\n".join(lines) for lines in body]
    assert doc.text.count("US 2020/0123456 A1") == 2  # Body mentions retained.
    assert len(doc.metadata.removed_margins) == 12
    assert {r.page_number for r in doc.metadata.removed_margins} == {1, 2}
    assert {r.position for r in doc.metadata.removed_margins} == {"header", "footer"}


def test_cross_page_claim_and_offsets_keep_chemical_hyphens(settings):
    data, _ = patent_pdf()
    doc = LocalAdapter(settings).read(data, "patent.pdf", "patent")
    claims = parse_patent(doc).claims
    assert len(claims) == 2
    assert "indazol-\n\n3-yl)-2-((R)-2-methoxy-1-methyl-ethylamino)" in claims[0].text
    assert claims[1].depends_on == [1]
    assert claims[0].evidence.page_numbers == [1, 2]
    for claim in claims:
        ev = claim.evidence
        assert doc.text[ev.start : ev.end] == ev.text == claim.text
    for page in doc.pages:
        assert doc.text[page.start : page.end] == page.text


def test_office_action_txt_and_json_unchanged(settings):
    data, _ = patent_pdf()
    doc = LocalAdapter(settings).read(data, "oa.pdf", "office_action")
    assert not doc.metadata.removed_margins
    assert "EXAMPLE RUNNING HEADER" in doc.text
    for suffix, data in [
        ("txt", b"Claims\n1. US 2020/0123456 A1 describes a method."),
        ("json", b'{"pages":[{"text":"Claims\\n1. US 2020/0123456 A1 describes a method."}]}'),
    ]:
        doc = LocalAdapter(settings).read(data, "claims." + suffix, "patent")
        assert "US 2020/0123456 A1" in doc.text
        assert not doc.metadata.removed_margins


def test_repeated_body_near_margin_is_preserved(settings):
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=(612, 792))
    for number in [1, 2]:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, 650, "Claims" if number == 1 else "continued treatment")
        pdf.drawString(50, 41, "lation, misregulation or deletion thereof might play a role by")
        pdf.drawString(50, 30, "changing the treatment response.")
        pdf.showPage()
    pdf.save()
    doc = LocalAdapter(settings).read(output.getvalue(), "patent.pdf", "patent")
    assert doc.text.count("lation, misregulation or deletion thereof might play a role by") == 2
    assert not doc.metadata.removed_margins


def test_ocr_cleaning_preserves_raw_engine_output():
    data, _ = patent_pdf()
    original = [
        "US 2020/0123456 A1\nMay 7, 2020\nClaims\n1. A compound containing indazol-",
        "US 2020/0123456 A1\nMay 7, 2020\n3-yl)-2-methoxy.\n2. The compound of claim 1.",
    ]
    raw = dict(enumerate(original, 1))
    metadata = OCRMetadata(ocr_used=True, ocr_pages=[1, 2], ocr_raw_text=raw)
    texts = clean_patent_margins(data, original, metadata)
    doc = from_pages(texts, "scan.pdf", "patent", metadata=metadata)
    assert "US 2020/0123456 A1" not in doc.text
    assert doc.metadata.ocr_raw_text == raw
    assert "indazol-\n\n3-yl)-2-methoxy" in parse_patent(doc).claims[0].text


@pytest.fixture(scope="module")
def actual_patent():
    return Path(__file__).parent / "fixtures/patent_headers/us20150283132a1_pages_40_41.pdf"


def test_actual_patent_claims_and_only_margin_removals(actual_patent, settings):
    data = actual_patent.read_bytes()
    raw_pages = [page.extract_text() for page in PdfReader(BytesIO(data)).pages]
    doc = LocalAdapter(settings).read(data, actual_patent.name, "patent")
    claims = parse_patent(doc).claims
    assert [c.claim_number for c in claims] == list(range(1, 20))
    assert claims[0].evidence.page_numbers == [1, 2]  # Source PDF pages 40 and 41.
    assert "US 2015/0283132 A1" not in "\n".join(c.text for c in claims)
    assert "Oct. 8, 2015" not in "\n".join(c.text for c in claims)
    assert "1H-indazol\n\n3-yl)-2-((R)-2-methoxy" in claims[0].text
    assert claims[11].text.endswith("NTRK2, and NTRK3.")
    for index, original in enumerate(raw_pages, 1):
        for removed in [r for r in doc.metadata.removed_margins if r.page_number == index]:
            assert re.fullmatch(r"(?:US 2015/0283132 A1|Oct\. 8, 2015|38|39)", removed.text.strip())
            assert original.count(removed.text) == 1
            original = original.replace(removed.text, "", 1)
        assert clean_text(original) == doc.pages[index - 1].text
