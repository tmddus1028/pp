import json
import subprocess
import sys
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from conftest import ROOT, make_pdf
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from backend.config import Settings
from backend.errors import DocumentError, OCRDependencyError, OCRProcessingError
from backend.ingestion import ocr, ocr_worker, pdf_reader
from backend.ingestion.adapters import LocalAdapter, evidence_at, from_text
from backend.ingestion.text_cleaner import clean_text
from backend.main import app, get_settings
from backend.service import analyze

FIXTURES = ROOT / "tests/fixtures/ocr"
EXPECTED = json.loads((FIXTURES / "expected_pages.json").read_text(encoding="utf-8"))


def reply(pages):
    return {
        "texts": {str(n): EXPECTED[n - 1] for n in pages},
        "blank_pages": [],
        "renderer": "pymupdf",
        "warnings": [],
    }


def read_fixture(name, settings):
    return LocalAdapter(settings).read((FIXTURES / name).read_bytes(), name, "office_action")


def test_text_pdf_never_calls_ocr_or_requires_executable(monkeypatch, settings):
    called = Mock(side_effect=AssertionError("Text PDF must not call OCR"))
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", called)
    settings.tesseract_cmd = "Z:/missing/tesseract.exe"
    doc = read_fixture("office_action_text.pdf", settings)
    assert not doc.metadata.ocr_used
    assert doc.metadata.ocr_pages == []
    assert doc.metadata.ocr_engine is None
    assert [p.text for p in doc.pages] == [clean_text(t) for t in EXPECTED]
    called.assert_not_called()


@pytest.mark.parametrize(
    "name,pages", [("office_action_scan.pdf", [1, 2]), ("office_action_mixed.pdf", [2])]
)
def test_page_selective_fallback_and_raw_text(monkeypatch, settings, name, pages):
    called = Mock(return_value=reply(pages))
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", called)
    doc = read_fixture(name, settings)
    assert called.call_count == 1
    assert called.call_args.args[1] == pages
    assert called.call_args.args[2].ocr_dpi == 300
    assert doc.metadata.ocr_pages == pages
    assert doc.metadata.ocr_raw_text == {n: EXPECTED[n - 1] for n in pages}
    assert [p.number for p in doc.pages] == [1, 2]
    assert [p.text for p in doc.pages] == [clean_text(t) for t in EXPECTED]
    span = evidence_at(doc, doc.pages[0].end - 5, doc.pages[1].start + 5)
    assert span.page_numbers == [1, 2]
    assert doc.text[span.start : span.end] == span.text


def test_sparse_page_with_page_number_still_uses_ocr(monkeypatch, settings):
    reader = PdfReader(FIXTURES / "office_action_scan.pdf")
    header = PdfReader(BytesIO(make_pdf(["1"])))
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.pages[0].merge_page(header.pages[0])
    stream = BytesIO()
    writer.write(stream)
    called = Mock(return_value=reply([1]))
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", called)
    doc = LocalAdapter(settings).read(stream.getvalue(), "sparse.pdf", "office_action")
    assert called.call_args.args[1] == [1]
    assert doc.pages[0].text.startswith("SYNTHETIC")


def test_text_layer_error_falls_back_to_ocr(monkeypatch, settings):
    monkeypatch.setattr(
        pdf_reader, "_without_duplicate_ocr", Mock(side_effect=PdfReadError("bad font"))
    )
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", Mock(return_value=reply([1, 2])))
    doc = read_fixture("office_action_text.pdf", settings)
    assert doc.metadata.ocr_pages == [1, 2]
    assert any("텍스트 레이어 추출에 실패" in w for w in doc.warnings)


def test_ocr_failure_does_not_return_partial_mixed_document(monkeypatch, settings):
    monkeypatch.setattr(
        pdf_reader, "ocr_pdf_pages", Mock(side_effect=OCRProcessingError("PDF 2페이지 OCR 실패"))
    )
    with pytest.raises(OCRProcessingError, match="2페이지"):
        read_fixture("office_action_mixed.pdf", settings)


def test_empty_ocr_is_not_success(monkeypatch, settings):
    result = reply([1, 2])
    result["texts"]["2"] = " \n"
    monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", Mock(return_value=result))
    with pytest.raises(OCRProcessingError, match="2페이지.*모두 실패"):
        read_fixture("office_action_scan.pdf", settings)


def test_invalid_tesseract_and_missing_install_are_distinct(monkeypatch, tmp_path):
    with pytest.raises(OCRDependencyError, match="TESSERACT_CMD 경로"):
        ocr.resolve_tesseract(str(tmp_path / "missing.exe"))
    monkeypatch.setattr(ocr.shutil, "which", lambda value: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    with pytest.raises(OCRDependencyError, match="설치되어 있지"):
        ocr.resolve_tesseract()


def test_env_tesseract_path_with_spaces(tmp_path):
    executable = tmp_path / "OCR Engine" / "tesseract.exe"
    executable.parent.mkdir()
    executable.touch()
    env = tmp_path / "settings.env"
    env.write_text(f"TESSERACT_CMD={executable}\nOCR_DPI=300\n", encoding="utf-8")
    settings = Settings(_env_file=env)
    assert ocr.resolve_tesseract(settings.tesseract_cmd) == str(executable.resolve())


@pytest.mark.parametrize(
    "outcome,error,match",
    [
        (subprocess.TimeoutExpired("worker", 1), OCRProcessingError, "시간이 초과"),
        (OSError("unavailable"), OCRDependencyError, "프로세스를 시작"),
        (SimpleNamespace(stdout="crashed", returncode=1), OCRProcessingError, "정상 결과 없이"),
        (SimpleNamespace(stdout='{"texts":{}}', returncode=0), OCRProcessingError, "누락"),
        (
            SimpleNamespace(stdout='{"error":"eng missing","code":"dependency"}', returncode=1),
            OCRDependencyError,
            "eng missing",
        ),
    ],
)
def test_worker_boundary_errors(monkeypatch, settings, outcome, error, match):
    monkeypatch.setattr(ocr, "resolve_tesseract", lambda configured: "tesseract")
    mock = (
        Mock(side_effect=outcome) if isinstance(outcome, Exception) else Mock(return_value=outcome)
    )
    monkeypatch.setattr(ocr.subprocess, "run", mock)
    with pytest.raises(error, match=match):
        ocr.ocr_pdf_pages(b"pdf", [1], settings)


def test_pymupdf_preferred_and_strict_failure(monkeypatch):
    opened = object()
    module = SimpleNamespace(open=Mock(return_value=opened), csRGB="rgb")
    monkeypatch.setitem(sys.modules, "pymupdf", module)
    assert ocr_worker.open_renderer("x.pdf", "auto") == (opened, "pymupdf", [])
    monkeypatch.setitem(sys.modules, "pymupdf", None)
    with pytest.raises(OCRDependencyError, match="PyMuPDF"):
        ocr_worker.open_renderer("x.pdf", "pymupdf")
    document, renderer, warnings = ocr_worker.open_renderer(
        str(FIXTURES / "office_action_scan.pdf"), "auto"
    )
    document.close()
    assert renderer == "pdfium" and warnings


def test_pymupdf_300_dpi_and_pixel_guard(monkeypatch):
    monkeypatch.setitem(sys.modules, "pymupdf", SimpleNamespace(csRGB="RGB"))
    page = SimpleNamespace(
        rect=SimpleNamespace(width=72, height=72),
        get_pixmap=Mock(return_value=SimpleNamespace(width=2, height=2, samples=b"\xff" * 12)),
    )
    with ocr_worker.render_page([page], "pymupdf", 1, 300, 100000) as image:
        assert image.mode == "RGB"
    page.get_pixmap.assert_called_once_with(dpi=300, colorspace="RGB", alpha=False)
    with pytest.raises(OCRProcessingError, match="이미지 크기 제한"):
        ocr_worker.render_page([page], "pymupdf", 1, 300, 100)


@pytest.mark.parametrize("failure", ["empty", "timeout", "tesseract", "language"])
def test_engine_failures_are_not_masked(monkeypatch, failure):
    import pytesseract

    monkeypatch.setattr(
        pytesseract, "get_languages", lambda **kw: [] if failure == "language" else ["eng"]
    )
    document = Mock()
    monkeypatch.setattr(ocr_worker, "open_renderer", lambda *a: (document, "pymupdf", []))
    monkeypatch.setattr(ocr_worker, "render_page", lambda *a: Image.new("RGB", (20, 20), "black"))
    problem = {
        "empty": "",
        "timeout": RuntimeError("timeout"),
        "tesseract": pytesseract.TesseractError(1, "failed"),
        "language": "unused",
    }[failure]
    monkeypatch.setattr(
        pytesseract,
        "image_to_string",
        Mock(side_effect=problem) if isinstance(problem, Exception) else Mock(return_value=problem),
    )
    with pytest.raises(OCRDependencyError if failure == "language" else OCRProcessingError):
        ocr_worker.recognize(
            {
                "command": "tesseract",
                "path": "x.pdf",
                "renderer": "auto",
                "pages": [2],
                "dpi": 300,
                "timeout": 1,
                "max_pixels": 1000000,
            }
        )
    if failure != "language":
        document.close.assert_called_once()


@pytest.fixture(scope="module")
def live_ocr_documents():
    settings = Settings(_env_file=None, llm_provider="local")
    try:
        ocr.resolve_tesseract(settings.tesseract_cmd)
    except OCRDependencyError:
        pytest.skip(
            "Local Tesseract is not installed; mocked tests still run. Install it to run real OCR tests."
        )
    return {
        name: read_fixture(name, settings)
        for name in ["office_action_scan.pdf", "office_action_mixed.pdf"]
    }


@pytest.mark.ocr_integration
def test_real_scan_has_no_embedded_text_and_preserves_patent_tokens(live_ocr_documents):
    assert all(
        not p.extract_text().strip() for p in PdfReader(FIXTURES / "office_action_scan.pdf").pages
    )
    doc = live_ocr_documents["office_action_scan.pdf"]
    assert doc.metadata.ocr_pages == [1, 2]
    assert doc.metadata.ocr_engine == "tesseract"
    assert doc.metadata.ocr_dpi == 300
    for token in [
        "Claim 1",
        "Claims 1-19",
        "35 U.S.C.",
        "§ 112",
        "§ 103",
        "35 U.S.C. 112(b)",
        "35 U.S.C. 103",
        "14/623,904",
        "Smith",
        "Johnson",
        "US 2010/0123456 A1",
        "8,765,432 B2",
    ]:
        assert token in doc.text, token
        assert any(token in raw for raw in doc.metadata.ocr_raw_text.values()), token
    for page in doc.pages:
        assert page.text == clean_text(doc.metadata.ocr_raw_text[page.number])
        assert doc.text[page.start : page.end] == page.text


@pytest.mark.ocr_integration
def test_real_mixed_ocr_downstream_and_evidence(live_ocr_documents, settings):
    doc = live_ocr_documents["office_action_mixed.pdf"]
    assert doc.metadata.ocr_pages == [2]
    assert doc.pages[0].text == clean_text(EXPECTED[0])
    claims = from_text(
        (FIXTURES / "claims.txt").read_text(encoding="utf-8"), "claims.txt", "patent"
    )
    result = analyze(claims, doc, settings)
    assert [r.statute for r in result.rejections] == ["35 USC 112(b)", "35 USC 103"]
    assert all(r.claims == list(range(1, 20)) for r in result.rejections)
    # Existing section chunking includes the following page's running header.
    # Keep that cross-page span instead of inventing a single-page attribution.
    assert [r.evidence.page_numbers for r in result.rejections] == [[1, 2], [2]]
    assert {(c.name, c.publication_number) for c in result.rejections[1].cited_references} == {
        ("Smith", "US20100123456A1"),
        ("Johnson", "US8765432B2"),
    }
    for r in result.rejections:
        assert doc.text[r.evidence.start : r.evidence.end] == r.evidence.text
        assert all(
            doc.text[c.evidence.start : c.evidence.end] == c.evidence.text
            for c in r.cited_references
        )
    assert not any(i.missing_claims for i in result.impacts)


@pytest.mark.ocr_integration
def test_real_scanned_api_metadata(live_ocr_documents, settings):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze/files",
                files={
                    "patent": ("claims.txt", (FIXTURES / "claims.txt").read_bytes()),
                    "office_action": (
                        "scan.pdf",
                        (FIXTURES / "office_action_scan.pdf").read_bytes(),
                    ),
                },
            )
            assert response.status_code == 200, response.text
            metadata = response.json()["documents"][1]["metadata"]
            assert metadata["ocr_pages"] == [1, 2]
            assert metadata["ocr_raw_text"] == {
                str(n): t
                for n, t in live_ocr_documents[
                    "office_action_scan.pdf"
                ].metadata.ocr_raw_text.items()
            }
            assert response.json()["provider"] == "local"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_api_ocr_errors_do_not_kill_server(monkeypatch, settings):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            for error in [
                OCRDependencyError("Tesseract OCR 미설치"),
                OCRProcessingError("PDF 2페이지 OCR 실패"),
            ]:
                monkeypatch.setattr(pdf_reader, "ocr_pdf_pages", Mock(side_effect=error))
                response = client.post(
                    "/analyze/files",
                    files={
                        "patent": ("claims.txt", (FIXTURES / "claims.txt").read_bytes()),
                        "office_action": (
                            "scan.pdf",
                            (FIXTURES / "office_action_scan.pdf").read_bytes(),
                        ),
                    },
                )
                assert response.status_code == 422
                assert response.json()["detail"] == str(error)
                assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_corrupt_pdf_is_not_reported_as_missing_ocr(settings):
    settings.tesseract_cmd = "missing.exe"
    with pytest.raises(DocumentError, match="파일 손상") as error:
        LocalAdapter(settings).read(b"not a PDF", "bad.pdf", "patent")
    assert type(error.value) is DocumentError
