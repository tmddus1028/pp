import json
import sys

import pytest
from conftest import ROOT

from backend.cli import main
from backend.errors import DocumentError
from backend.ingestion.adapters import LocalAdapter
from backend.office_action.rejection_extractor import extract_local
from backend.patent.patent_parser import parse_patent
from backend.service import analyze


def test_cli_output(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli",
            "--patent",
            str(ROOT / "data/raw/demo_patent.txt"),
            "--office-action",
            str(ROOT / "data/raw/demo_office_action.txt"),
            "--provider",
            "local",
            "--output",
            str(output),
        ],
    )
    assert main() == 0
    assert len(json.loads(output.read_text(encoding="utf-8"))["rejections"]) == 3


def test_cli_missing_file(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli",
            "--patent",
            str(tmp_path / "missing.txt"),
            "--office-action",
            str(tmp_path / "missing_oa.txt"),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_public_excerpt_is_explicit_about_missing_version(settings):
    root = ROOT / "data/raw/uspto"
    adapter = LocalAdapter(settings)
    result = analyze(
        adapter.read((root / "US20140201856A1_claims.json").read_bytes(), "claims.json", "patent"),
        adapter.read(
            (root / "application_14040405_oa_excerpt.txt").read_bytes(), "oa.txt", "office_action"
        ),
        settings,
    )
    assert len(result.patent.claims) == 1
    assert len(result.rejections) == 2
    assert all(
        r.statute == "unknown" for r in result.rejections
    )  # double patenting is not invented as 103
    assert result.impacts[0].missing_claims
    assert all(
        1 not in r.claims for r in result.rejections
    )  # cited patent claim 1 is not the applicant's claim
    assert any(
        c.publication_number == "US9505827" for r in result.rejections for c in r.cited_references
    )


def test_official_112f_interpretation_is_not_rejection(settings):
    path = ROOT / "data/raw/uspto/official_112f_sample.pdf"
    doc = LocalAdapter(settings).read(path.read_bytes(), path.name, "office_action")
    assert len(doc.pages) == 3
    assert extract_local(doc)[0] == []


def test_public_pdf_does_not_silently_parse_specification_as_claims(settings, monkeypatch):
    # Preserve the missing-claims guard when OCR cannot identify a claims listing.
    # Real OCR recognition is covered by the image-only fixtures in test_ocr.py.
    monkeypatch.setattr(
        "backend.ingestion.pdf_reader.ocr_pdf_pages",
        lambda data, pages, config: {
            "texts": {str(n): "No recognizable claims listing on this page." for n in pages},
            "blank_pages": [],
            "renderer": "pymupdf",
            "warnings": [],
        },
    )
    path = ROOT / "data/raw/uspto/US20140201856A1.pdf"
    doc = LocalAdapter(settings).read(path.read_bytes(), path.name, "patent")
    assert len(doc.pages) == 127
    assert doc.warnings
    with pytest.raises(DocumentError):
        parse_patent(doc)
