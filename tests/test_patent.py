import pytest

from backend.errors import DocumentError
from backend.ingestion.adapters import from_text
from backend.patent.claim_parser import parse_claims
from backend.patent.dependency_parser import (
    build_dependency_graph,
    parse_dependencies,
    parse_number_list,
)
from backend.patent.patent_parser import parse_patent


@pytest.mark.parametrize(
    "text,expected",
    [
        ("The method of claim 1...", [1]),
        ("The apparatus according to claim 3...", [3]),
        ("The system of any one of claims 1-3...", [1, 2, 3]),
        ("The system of claims 1, 3 and 5...", [1, 3, 5]),
        ("The system of claims 1, 3, and 5...", [1, 3, 5]),
        ("The system of claims 1 through 3 or 7...", [1, 2, 3, 7]),
        ("A standalone device.", []),
    ],
)
def test_dependencies(text, expected):
    assert parse_dependencies(text) == expected


@pytest.mark.parametrize("value", ["3-1", "0", "1-9999", "1 banana 4"])
def test_invalid_ranges(value):
    with pytest.raises(DocumentError):
        parse_number_list(value)


def test_claims_and_canceled(patent_text):
    doc = from_text(patent_text, "patent.txt", "patent")
    claims = parse_claims(doc)
    assert len(claims) == 9
    assert claims[4].depends_on == [2, 3, 4]
    assert claims[8].status == "canceled"
    for claim in claims:
        assert doc.text[claim.evidence.start : claim.evidence.end] == claim.text


def test_description_not_parsed_as_claims():
    doc = from_text(
        "Description\n1. A paragraph.\nWhat is claimed is:\n1. A device.\n2. The device of claim 1.\nAbstract\nSome abstract",
        "p.txt",
        "patent",
    )
    claims = parse_claims(doc)
    assert len(claims) == 2
    assert "abstract" not in claims[-1].text.lower()


@pytest.mark.parametrize(
    "text", ["No claims.", "Claims\n1. A device.\n1. A device.", "Claims\n1. (Canceled)."]
)
def test_bad_claims(text):
    with pytest.raises(DocumentError):
        parse_claims(from_text(text, "p.txt", "patent"))


def test_missing_and_cycle():
    doc = from_text("Claims\n2. The system of claim 1.", "p.txt", "patent")
    patent = parse_patent(doc)
    assert any("부모" in w for w in patent.warnings)
    for text in [
        "Claims\n1. The device of claim 1.",
        "Claims\n1. The device of claim 2.\n2. The device of claim 1.",
    ]:
        with pytest.raises(DocumentError):
            build_dependency_graph(parse_claims(from_text(text, "p.txt", "patent")))
