import json
from io import BytesIO

import pytest
from conftest import make_pdf
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from backend.errors import DocumentError
from backend.ingestion.adapters import LocalAdapter, evidence_at, from_pages, from_text
from backend.ingestion.dataset_adapter import claims_from_csv
from backend.ingestion.pdf_reader import read_pdf
from backend.ingestion.text_cleaner import clean_text


def test_clean_text():
    assert clean_text("  A\tB\r\n\ufb01lter\u00ad \x00") == "A B\nfilter"


def test_page_offsets_and_cross_page_evidence():
    doc = from_pages(["  abc  ", "def"], "oa.txt", "office_action")
    evidence = evidence_at(doc, 1, 7)
    assert evidence.text == "bc\n\nde"
    assert evidence.page_numbers == [1, 2]
    assert doc.pages[1].start == 5
    with pytest.raises(ValueError):
        evidence_at(doc, 3, 3)


def test_pdf_text_and_blank_page():
    pages, warnings = read_pdf(make_pdf(["Claims\n1. A useful system comprising a processor.", ""]))
    assert "processor" in pages[0]
    assert any("2" in w for w in warnings)


def test_pdf_corrupt_scanned_encrypted_and_page_limit():
    with pytest.raises(DocumentError):
        read_pdf(b"bad pdf")
    with pytest.raises(DocumentError, match="OCR"):
        read_pdf(make_pdf([""]))
    with pytest.raises(DocumentError, match="1~1"):
        read_pdf(make_pdf(["text page one", "page two"]), max_pages=1)
    writer = PdfWriter()
    writer.append_pages_from_reader(PdfReader(BytesIO(make_pdf(["protected text"]))))
    writer.encrypt("password")
    output = BytesIO()
    writer.write(output)
    with pytest.raises(DocumentError, match="암호"):
        read_pdf(output.getvalue())


def test_adapters_json_txt_pdf(settings):
    adapter = LocalAdapter(settings)
    text = "Claims\n1. A useful system comprising a processor."
    assert adapter.read(text.encode(), "x.txt", "patent").text == text
    payload = json.dumps(
        {"pages": [{"text": text}, {"text": "2. The system of claim 1."}]}
    ).encode()
    assert len(adapter.read(payload, "x.json", "patent").pages) == 2
    assert "processor" in adapter.read(make_pdf([text]), "x.pdf", "patent").text


@pytest.mark.parametrize(
    "data,name", [(b"\xff", "x.txt"), (b"{}", "x.json"), (b"hi", "x.docx"), (b" ", "x.txt")]
)
def test_adapter_errors(data, name, settings):
    with pytest.raises(DocumentError):
        LocalAdapter(settings).read(data, name, "patent")


def test_limits(settings):
    settings.max_upload_mb = 1
    with pytest.raises(DocumentError):
        LocalAdapter(settings).read(b"a" * (1024 * 1024 + 1), "a.txt", "patent")
    with pytest.raises(DocumentError):
        from_text("x" * 2000, "x.txt", "patent", max_chars=1000)


def test_csv_adapter(tmp_path):
    path = tmp_path / "claims.csv"
    path.write_text(
        "id,no,text\n001,1,A device.\n001,2,The device of claim 1.\n002,1,Other device.\n"
    )
    doc = claims_from_csv(path, "001", id_column="id", number_column="no", text_column="text")
    assert "Other device" not in doc.text
    assert doc.text.startswith("Claims\n1.")
    with pytest.raises(DocumentError):
        claims_from_csv(path, "001", id_column="wrong", number_column="no", text_column="text")
    with pytest.raises(DocumentError):
        claims_from_csv(path, "003", id_column="id", number_column="no", text_column="text")


@pytest.mark.parametrize("variant", ["duplicate", "unique", "visible", "untagged"])
def test_only_tagged_matching_invisible_ocr_is_deduplicated(variant):
    text = "Claims\n1. A processor that receives a signal from a sensor and sends the signal to a server.\n2. The processor of claim 1 configured to store the signal in a memory."
    writer = PdfWriter()
    writer.append_pages_from_reader(PdfReader(BytesIO(make_pdf([text]))))
    page = writer.pages[0]
    original = page.get_contents().get_data()
    tagged = original.replace(b"BT", b"BT 3 Tr")
    second = original.replace(b"BT", b"BT 3 Tr")
    if variant == "unique":
        tagged = (
            tagged.replace(b"processor", b"actuator")
            .replace(b"signal", b"command")
            .replace(b"server", b"gateway")
        )
    if variant == "visible":
        second = original.replace(b"BT", b"BT 0 Tr")
    if variant != "untagged":
        tagged = b"/OCRPageInfo << /L /en >> BDC\n" + tagged + b"\nEMC\n"
    stream = DecodedStreamObject()
    stream.set_data(tagged + second)
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    extracted, warnings = read_pdf(output.getvalue())
    assert any("중복 OCR" in w for w in warnings) == (variant == "duplicate")
    assert extracted[0].count("Claims") == (1 if variant == "duplicate" else 2)
