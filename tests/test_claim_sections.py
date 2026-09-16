"""Heading-free claims: actual uploaded PDF plus conservative boundary checks."""

import hashlib

import pytest
from conftest import ROOT
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.errors import DocumentError
from backend.ingestion.adapters import LocalAdapter, from_pages, from_text
from backend.main import app, get_settings
from backend.patent.claim_parser import HEADING, parse_claims

FIXTURE = ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf"
SHA256 = "e8d5120002a99f6a36c9835b2cb7e932e2304fe110e1ae1ac681d64964003cf9"
PREFIX = "Description\n" + "The disclosed embodiments illustrate a deposition process.\n" * 80
CLAIMS = (
    "1. A method comprising depositing a thin film on a substrate.\n"
    "2. The method of claim 1, wherein the substrate comprises sapphire.\n"
    "3. The method according to claim 2, wherein the film comprises gallium oxide."
)


@pytest.fixture(scope="module")
def actual_document():
    data = FIXTURE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA256
    return LocalAdapter(Settings(_env_file=None, llm_provider="local")).read(
        data, FIXTURE.name, "patent"
    )


def test_us20220325409a1_original_pdf_all_twenty_claims(actual_document):
    document = actual_document
    assert len(document.pages) == 18
    assert not document.metadata.ocr_used
    assert HEADING.search(document.text) is None
    assert "US 2022/0325409 A1" in document.text
    claims = parse_claims(document)
    assert [c.claim_number for c in claims] == list(range(1, 21))
    assert claims[0].text.startswith("A method for forming a thin film")
    assert claims[18].text.startswith("The method of claim 18")
    assert claims[19].text.startswith("A thin film comprising")
    assert "19. The method" not in claims[17].text
    assert "20. A thin film" not in claims[18].text
    assert claims[0].evidence.page_numbers == [17]
    assert claims[15].evidence.page_numbers == [18]
    assert claims[18].depends_on == [18]
    assert claims[19].depends_on == [1]
    for claim in claims:
        evidence = claim.evidence
        assert document.text[evidence.start : evidence.end] == claim.text == evidence.text
        assert evidence.page_numbers == [
            p.number for p in document.pages if p.start < evidence.end and p.end > evidence.start
        ]


def test_original_pdf_multipart_analysis_succeeds(settings):
    # Synthetic OA tests transport/analysis only, not a matching prosecution pair.
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app) as client:
            response = client.post(
                "/analyze/files",
                files={
                    "patent": (FIXTURE.name, FIXTURE.read_bytes(), "application/pdf"),
                    "office_action": (
                        "synthetic_oa.txt",
                        b"Claims 1-20 are rejected under 35 U.S.C. 103 over Smith.",
                        "text/plain",
                    ),
                },
            )
        assert response.status_code == 200, response.text
        result = response.json()
        assert [c["claim_number"] for c in result["patent"]["claims"]] == list(range(1, 21))
        assert len(result["rejections"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_heading_free_section_spans_pages_and_stops_at_next_section():
    document = from_pages(
        [
            PREFIX,
            CLAIMS[: CLAIMS.index("2.")],
            CLAIMS[CLAIMS.index("2.") :] + "\nAbstract\nOther text",
        ],
        "claims.json",
        "patent",
    )
    claims = parse_claims(document)
    assert [c.claim_number for c in claims] == [1, 2, 3]
    assert claims[0].evidence.page_numbers == [2]
    assert claims[-1].evidence.page_numbers == [3]
    assert "Other text" not in claims[-1].text
    for claim in claims:
        assert document.text[claim.evidence.start : claim.evidence.end] == claim.text


def test_heading_free_claim_continuation_and_inline_numbers_keep_source_offsets():
    document = from_pages(
        [
            PREFIX + "1. A method comprising depositing",
            " a thin film. " + CLAIMS.split("\n", 1)[1].replace("\n", " "),
        ],
        "claims.json",
        "patent",
    )
    claims = parse_claims(document)
    assert [c.claim_number for c in claims] == [1, 2, 3]
    assert claims[0].evidence.page_numbers == [1, 2]
    assert claims[0].text == "A method comprising depositing\n\na thin film."
    for claim in claims:
        assert document.text[claim.evidence.start : claim.evidence.end] == claim.text


@pytest.mark.parametrize(
    "heading", ["What is claimed is:", "What is claimed:", "I claim:", "We claim:", "Claims"]
)
def test_explicit_headings_take_priority_over_heading_free_candidates(heading):
    document = from_text(PREFIX + CLAIMS + "\n" + heading + "\n1. A device.", "p.txt", "patent")
    claims = parse_claims(document)
    assert len(claims) == 1 and claims[0].text == "A device."


def test_claim_only_text_remains_supported_without_heading():
    assert len(parse_claims(from_text(CLAIMS, "claims.txt", "patent"))) == 3


@pytest.mark.parametrize(
    "candidate",
    [
        CLAIMS.split("\n")[0],  # A single number is insufficient.
        "\n".join(CLAIMS.split("\n")[:2]),
        CLAIMS.replace("3. The", "4. The"),  # A gap is not silently accepted.
        CLAIMS.replace("3. The", "2. The"),
        "1. A method comprising depositing a thin film.\n"
        "2. A device comprising a sapphire substrate.\n"
        "3. A system comprising a gallium oxide film.",  # No dependencies.
        "1. First, clean the substrate.\n2. Then deposit a film.\n3. Inspect claim 1 for details.",
        "1. A review of claim 1 in a published journal.\n"
        "2. A discussion of claim 2 in another publication.\n"
        "3. A summary of claim 3 in the literature.",
        CLAIMS.replace(
            "1. A method comprising depositing a thin film on a substrate.", "1. A label."
        ),
        CLAIMS.replace("claim 1", "claim 99").replace("claim 2", "claim 99"),
    ],
)
def test_numbered_lists_and_unconfirmed_claim_sections_are_rejected(candidate):
    with pytest.raises(DocumentError):
        parse_claims(from_text(PREFIX + candidate, "p.txt", "patent"))


def test_claim_like_list_in_front_half_does_not_confirm_section():
    with pytest.raises(DocumentError):
        parse_claims(from_text(PREFIX + CLAIMS + "\n" + PREFIX * 3, "p.txt", "patent"))


def test_two_plausible_sections_are_ambiguous():
    with pytest.raises(DocumentError):
        parse_claims(from_text(PREFIX + CLAIMS + "\nAppendix\n" + CLAIMS, "p.txt", "patent"))


def test_numbered_bibliography_before_claims_is_not_included():
    document = from_text(
        PREFIX + "References\n1. Smith, Journal (2022).\n2. Jones, Journal (2021).\n" + CLAIMS,
        "p.txt",
        "patent",
    )
    claims = parse_claims(document)
    assert len(claims) == 3
    assert "Smith" not in claims[0].text
