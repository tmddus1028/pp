import pytest

from backend.analysis.citation_analyzer import citation_id, normalize_publication
from backend.ingestion.adapters import from_text
from backend.llm.structured_extraction import merge_rejections
from backend.office_action.oa_parser import chunk_office_action
from backend.office_action.rejection_extractor import extract_local, normalize_statute


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("35 U.S.C. § 103", "35 USC 103"),
        ("35 USC 102(a)(1)", "35 USC 102(a)(1)"),
        ("§112 (b)", "35 USC 112(b)"),
        ("other", "unknown"),
    ],
)
def test_statute(raw, expected):
    assert normalize_statute(raw) == expected


def test_local_rejections(oa_text):
    doc = from_text(oa_text, "oa.txt", "office_action")
    rejections, _ = extract_local(doc)
    assert [r.claims for r in rejections] == [[1, 2, 3], [6], [7]]
    assert [r.statute for r in rejections] == ["35 USC 103", "35 USC 112(b)", "35 USC 102(a)(1)"]
    assert {c.name for c in rejections[0].cited_references} == {"Smith", "Johnson"}
    assert len(rejections[0].cited_references) == 2


def test_objection_unknown_and_no_false_positive():
    doc = from_text(
        "Claims 1-2 are allowed. Claim 3 is not rejected.\nClaim 4 is objected to because of a typo.",
        "oa.txt",
        "office_action",
    )
    rejections, _ = extract_local(doc)
    assert len(rejections) == 1
    assert rejections[0].action_type == "objection"
    assert rejections[0].statute == "unknown"
    assert rejections[0].claims == [4]


def test_withdrawal_and_empty():
    doc = from_text(
        "Claim 1 is rejected under 35 USC 103. The rejection is withdrawn.",
        "oa.txt",
        "office_action",
    )
    rejections, warnings = extract_local(doc)
    assert rejections == []
    assert any("못했" in w for w in warnings)


def test_cross_page_chunk_and_long_chunk():
    doc = from_text(
        "Claims 1-3 are rejected under\f35 USC 103 over Smith.", "oa.txt", "office_action"
    )
    rejections, _ = extract_local(doc)
    assert rejections[0].evidence.page_numbers == [1, 2]
    long_doc = from_text(
        "Claim 1 is rejected under 35 USC 103. " + "x " * 2000, "oa.txt", "office_action"
    )
    chunks = chunk_office_action(long_doc, 1000)
    assert len(chunks) > 1
    assert all(len(c.text) <= 1000 for c in chunks)
    assert all(long_doc.text[c.start : c.end] == c.text for c in chunks)


def test_distinct_rejections_preserved():
    doc = from_text(
        "Claim 1 is rejected under 35 USC 103 over Smith.\nClaim 1 is rejected under 35 USC 103 over Johnson.",
        "oa.txt",
        "office_action",
    )
    extracted, _ = extract_local(doc)
    merged = merge_rejections(extracted + [extracted[0]])
    assert len(merged) == 2
    assert [r.rejection_id for r in merged] == ["R1", "R2"]


def test_citation_normalization():
    assert normalize_publication("U.S. Patent No. 8,765,432 B2") == "US8765432B2"
    assert normalize_publication("US 2010/0123456 A1") == "US20100123456A1"
    assert normalize_publication("unclear") is None
    assert citation_id("Smith", "US1234567") == citation_id("Smith et al.", "US1234567")


def test_oa_abbreviated_and_slash_separated_references():
    doc = from_text(
        "Claims 3-5 and 8 are rejected under 35 U.S.C. 103 over Singhal "
        "(USPAP 20020062281) in view of Scipioni (USPAP 20120296821)/Del Favero et al "
        "(USPN 8,073,775) and further in view of Davis et al (USPAP 20090070263). "
        "The feature is taught by Davis.",
        "oa.txt",
        "office_action",
    )
    refs = extract_local(doc)[0][0].cited_references
    assert {(r.name, r.publication_number) for r in refs} == {
        ("Singhal", "US20020062281"),
        ("Scipioni", "US20120296821"),
        ("Del Favero et al", "US8073775"),
        ("Davis et al", "US20090070263"),
    }


def test_same_name_different_numbers_not_merged():
    doc = from_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (US 8,111,111) "
        "in view of Smith (US 8,222,222).",
        "oa.txt",
        "office_action",
    )
    refs = extract_local(doc)[0][0].cited_references
    assert {r.publication_number for r in refs} == {"US8111111", "US8222222"}
