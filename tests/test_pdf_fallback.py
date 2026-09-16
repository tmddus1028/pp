import hashlib
import json
import subprocess
import sys
from collections import Counter
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from conftest import ROOT, make_pdf
from fastapi.testclient import TestClient
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.errors import DocumentError
from backend.ingestion import ocr_worker, pdf_open, pdf_open_worker, pdf_reader
from backend.ingestion.adapters import LocalAdapter, from_text
from backend.main import app, get_settings
from backend.office_action.rejection_extractor import extract_local
from backend.service import analyze

FIXTURES = ROOT / "tests/fixtures/pdf_fallback"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pair():
    from backend.config import Settings

    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    documents = [
        adapter.read((FIXTURES / f["filename"]).read_bytes(), f["filename"], kind)
        for f, kind in zip(MANIFEST["files"], ["patent", "office_action"])
    ]
    return analyze(*documents, settings)


def check_pair(result):
    assert [len(d.pages) for d in result.documents] == [47, 13]
    assert [c.claim_number for c in result.patent.claims] == MANIFEST["expected"]["claims"]
    assert len(result.rejections) == 3
    for rejection, expected in zip(result.rejections, MANIFEST["expected"]["rejections"]):
        assert rejection.statute == expected["statute"]
        assert rejection.claims == expected["claims"]
        assert rejection.evidence.page_numbers[0] == expected["start_page"]
        assert {r.name for r in rejection.cited_references} == set(expected["citations"])
    refs = {c.citation_id: c for r in result.rejections for c in r.cited_references}
    assert len(refs) == len([n for n in result.graph.nodes if n.kind == "citation"]) == 5
    assert {r.publication_number for r in refs.values() if r.type == "patent"} == set(
        MANIFEST["expected"]["patent_citations"]
    )
    assert {(r.name, r.publication, r.year) for r in refs.values() if r.type == "npl"} == {
        (r["name"], r["publication"], r["year"]) for r in MANIFEST["expected"]["npl"]
    }


def test_original_files_hashes_and_strict_parser_failure():
    for source in MANIFEST["files"]:
        assert (
            hashlib.sha256((FIXTURES / source["filename"]).read_bytes()).hexdigest()
            == source["sha256"]
        )
    with pytest.raises(PdfReadError, match="Invalid object in /Pages"):
        list(PdfReader(FIXTURES / "pp_vd2.pdf").pages)


def test_real_pdf_pair_counts_and_original_evidence(pair):
    check_pair(pair)
    assert pair.documents[0].metadata.pdf_layout_pages == [46, 47]
    assert pair.documents[1].metadata.pdf_parser in {"pymupdf", "pdfium"}
    assert pair.documents[1].metadata.ocr_used is False
    assert pair.documents[0].metadata.ocr_pages == [35]
    assert "4. The method" not in pair.patent.claims[0].text
    assert pair.patent.claims[11].depends_on == [11]
    documents = {d.document_id: d for d in pair.documents}

    def walk(value):
        if isinstance(value, dict):
            if {"start", "end", "text", "document_id", "page_numbers"} <= value.keys():
                doc = documents[value["document_id"]]
                assert doc.text[value["start"] : value["end"]] == value["text"]
                assert value["page_numbers"] == [
                    p.number for p in doc.pages if p.start < value["end"] and p.end > value["start"]
                ]
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(pair.model_dump())
    for rejection in pair.rejections[1:]:
        for ref in rejection.cited_references:
            if ref.definition_evidence:
                assert ref.definition_evidence.start < ref.evidence.start
                assert rejection.evidence.start <= ref.evidence.start < rejection.evidence.end


def test_real_pair_multipart_upload(settings):
    from backend.schemas import AnalysisResult

    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze/files",
                files={
                    key: (name, (FIXTURES / name).read_bytes(), "application/pdf")
                    for key, name in [("patent", "pp_ex2.pdf"), ("office_action", "pp_vd2.pdf")]
                },
            )
        assert response.status_code == 200, response.text
        check_pair(AnalysisResult.model_validate(response.json()))
    finally:
        app.dependency_overrides.clear()


def test_native_open_order_and_success_stops_fallback(monkeypatch):
    success = {"pages": ["A text page"], "failed": [], "layouts": []}
    first, second = Mock(return_value=success), Mock(return_value=success)
    monkeypatch.setattr(pdf_open_worker, "pymupdf_pages", first)
    monkeypatch.setattr(pdf_open_worker, "pdfium_pages", second)
    assert pdf_open_worker.open_native("x.pdf", 150)["engine"] == "pymupdf"
    second.assert_not_called()
    first.side_effect = ValueError("malformed page tree")
    result = pdf_open_worker.open_native("x.pdf", 150)
    assert result["engine"] == "pdfium" and result["failures"]
    second.assert_called_once()


def test_legacy_parser_is_last_open_fallback(monkeypatch, settings):
    native = Mock(
        return_value={
            "engine": None,
            "pages": [],
            "failed": [],
            "layouts": [],
            "failures": ["both native parsers failed"],
        }
    )
    monkeypatch.setattr(pdf_reader, "open_native_pdf", native)
    result = pdf_reader.extract_pdf(
        make_pdf(["Claims\n1. A useful sensor with a processor."]), settings
    )
    assert result.metadata.pdf_parser == "pypdf"
    assert "processor" in result.pages[0]
    assert not result.metadata.ocr_used


def test_strict_parser_failure_does_not_require_ocr_or_break_patent_cleaning(monkeypatch, settings):
    import backend.ingestion.margin_cleaner as margins

    monkeypatch.setattr(
        pdf_reader, "PdfReader", Mock(side_effect=PdfReadError("Invalid object in /Pages"))
    )
    monkeypatch.setattr(
        margins, "PdfReader", Mock(side_effect=PdfReadError("Invalid object in /Pages"))
    )
    ocr = Mock(side_effect=AssertionError("Readable native text must not need OCR"))
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", ocr)
    doc = LocalAdapter(settings).read(
        make_pdf(["Claims\n1. A useful sensor with a processor."]), "x.pdf", "patent"
    )
    assert "processor" in doc.text and doc.metadata.pdf_parser in {"pdfium", "pymupdf"}
    ocr.assert_not_called()


def test_all_parser_failures_remain_an_error(settings):
    with pytest.raises(DocumentError, match="모두 열기에 실패"):
        pdf_reader.extract_pdf(b"not a PDF", settings)


@pytest.mark.parametrize(
    "back_reference,ambiguous,expected",
    [(True, False, True), (False, False, False), (True, True, False)],
)
def test_alias_requires_explicit_prior_reference_and_unique_bibliography(
    back_reference, ambiguous, expected
):
    first = "Claim 1 is rejected under 35 USC 103 over Smith et al. [WO 2012/058638 A2]."
    if ambiguous:
        first += " Smith et al. [WO 2013/119950 A2]."
    second = "Claim 2 is rejected under 35 USC 103 over Smith et al."
    if back_reference:
        second += " as applied to claim 1 above."
    rejections, _ = extract_local(from_text(first + "\n" + second, "oa.txt", "office_action"))
    ref = rejections[1].cited_references[0]
    assert (ref.definition_evidence is not None) == expected
    assert (ref.type == "patent") == expected


def test_is_are_summary_and_prior_art_claims_are_not_extra_grounds():
    doc = from_text(
        "Claim(s) 1-20 is/are rejected.\nClaims 1-20 are pending.\n"
        "Claims 1-3 is/are rejected under pre-AIA 35 U.S.C. 103(a) over Smith.\n"
        "See claims 1-3 of Smith.",
        "oa.txt",
        "office_action",
    )
    results, _ = extract_local(doc)
    assert len(results) == 1 and results[0].claims == [1, 2, 3]


def test_native_text_fallback_uses_ocr_only_for_sparse_pages(monkeypatch, settings):
    monkeypatch.setattr(pdf_reader, "PdfReader", Mock(side_effect=PdfReadError("bad pages")))
    ocr = Mock(
        return_value={
            "texts": {"2": "Claim 1 is rejected under 35 USC 103 over Smith."},
            "blank_pages": [],
            "renderer": "pdfium",
            "warnings": [],
        }
    )
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", ocr)
    source = (ROOT / "tests/fixtures/ocr/office_action_mixed.pdf").read_bytes()
    result = pdf_reader.extract_pdf(source, settings)
    assert ocr.call_args.args[1] == [2]
    assert result.metadata.ocr_pages == [2]
    assert "103" in result.pages[1]


def test_ocr_renderer_open_failure_tries_pdfium(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "pymupdf", SimpleNamespace(open=Mock(side_effect=ValueError("invalid Pages")))
    )
    doc, engine, warnings = ocr_worker.open_renderer(str(FIXTURES / "pp_vd2.pdf"), "auto")
    try:
        assert engine == "pdfium" and len(doc) == 13 and warnings
    finally:
        doc.close()


@pytest.mark.parametrize("outcome", ["invalid_json", "invalid_pages", "timeout", "crash"])
def test_native_worker_failure_still_allows_legacy_parser(monkeypatch, settings, outcome):
    response = SimpleNamespace(stdout="invalid", returncode=0)
    if outcome == "invalid_pages":
        response.stdout = json.dumps({"engine": "pdfium", "pages": ["text"], "failed": [2]})
    if outcome == "crash":
        response.returncode = 1
    mock = (
        Mock(side_effect=subprocess.TimeoutExpired("worker", 120))
        if outcome == "timeout"
        else Mock(return_value=response)
    )
    monkeypatch.setattr(pdf_open.subprocess, "run", mock)
    result = pdf_reader.extract_pdf(
        make_pdf(["Claims\n1. A system comprising a useful processor."]), settings
    )
    assert result.metadata.pdf_parser == "pypdf"
    assert not result.metadata.ocr_used


def test_claim_column_order_preserves_every_source_glyph():
    import pypdfium2 as pdfium
    import pypdfium2.raw as raw

    result = pdf_open_worker.pdfium_pages(str(FIXTURES / "pp_ex2.pdf"), 150)
    with pdfium.PdfDocument(FIXTURES / "pp_ex2.pdf") as doc:
        for number in result["layouts"]:
            page = doc[number - 1]
            text = page.get_textpage()
            try:
                source = "".join(
                    chr(raw.FPDFText_GetUnicode(text, i)) for i in range(text.count_chars())
                )
                assert Counter(c for c in source if c.strip() and c != "\x00") == Counter(
                    c for c in result["pages"][number - 1] if c.strip()
                )
            finally:
                text.close()
                page.close()


def test_pymupdf_good_claim_order_is_not_replaced_by_bad_legacy_order(monkeypatch, settings):
    good = (
        "What is claimed is:\n1. A useful system comprising a processor.\n2. The system of claim 1."
    )
    bad = good.replace("\n", " ")
    monkeypatch.setattr(
        pdf_reader,
        "open_native_pdf",
        Mock(
            return_value={
                "engine": "pymupdf",
                "pages": [good],
                "failed": [],
                "layouts": [],
                "failures": [],
            }
        ),
    )
    monkeypatch.setattr(pdf_reader, "_without_duplicate_ocr", Mock(return_value=(bad, False)))
    doc = LocalAdapter(settings).read(make_pdf([good]), "claims.pdf", "patent")
    assert doc.text == good
    assert doc.metadata.pdf_layout_pages == [1]


def test_pymupdf_page_text_failure_retains_page_for_ocr(monkeypatch):
    doc = MagicMock()
    doc.__enter__.return_value = doc
    doc.__len__.return_value = 2
    doc.needs_pass = doc.is_encrypted = False
    doc.load_page.side_effect = [
        SimpleNamespace(get_text=Mock(return_value="A readable embedded text page.")),
        SimpleNamespace(get_text=Mock(side_effect=ValueError("bad font"))),
    ]
    monkeypatch.setitem(sys.modules, "pymupdf", SimpleNamespace(open=Mock(return_value=doc)))
    result = pdf_open_worker.pymupdf_pages("x.pdf", 150)
    assert result["pages"] == ["A readable embedded text page.", ""]
    assert result["failed"] == [2]
    doc.__exit__.assert_called_once()
