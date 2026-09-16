from pathlib import Path

import pytest

from backend.analysis.citation_analyzer import extract_citations, normalize_publication
from backend.graph.graph_builder import build_graph
from backend.ingestion.adapters import from_pages, from_text
from backend.llm.client import RejectionDraft
from backend.llm.structured_extraction import validate_draft
from backend.office_action.oa_parser import chunk_office_action
from backend.office_action.rejection_extractor import extract_local
from backend.service import analyze

FIXTURE = Path(__file__).parent / "fixtures/citations/office_action_14623904_reconstructed.txt"
PATENTS = {"WO2009013126A1", "WO2008074749A1", "WO2013119950A2"}


@pytest.fixture
def citation_result(settings):
    patent = from_text(
        "Claims\n1. A method of treating cancer using a compound.\n"
        + "\n".join(
            f"{n}. The method of claim 1, wherein the compound is administered."
            for n in range(2, 20)
        ),
        "claims.txt",
        "patent",
    )
    text = FIXTURE.read_text(encoding="utf-8")
    # Put NPL across a real document page boundary to check citation-level pages.
    split = text.index("(2010)")
    oa = from_pages([text[:split], text[split:]], FIXTURE.name, "office_action")
    return analyze(patent, oa, settings)


def test_all_three_wo_patents(citation_result):
    first, second = citation_result.rejections
    assert first.statute == "35 USC 112"
    assert not first.cited_references
    assert second.statute == "35 USC 103(a)"
    assert second.claims == list(range(1, 20))
    patents = [r for r in second.cited_references if r.type == "patent"]
    assert {r.publication_number for r in patents} == PATENTS
    assert {r.name for r in patents} == {"Lombardi et al", "Bendiera et al", "Hout et al"}


def test_both_npl_and_exact_source_spans(citation_result):
    oa = citation_result.documents[1]
    refs = citation_result.rejections[1].cited_references
    npl = [r for r in refs if r.type == "npl"]
    assert {(r.name, r.publication, r.year) for r in npl} == {
        ("Greco et al", "Molecular and Cellular Endocrinology", 2010),
        ("Lipska et al", "BMC Cancer", 2009),
    }
    assert npl[0].evidence.page_numbers == [1, 2]
    assert npl[1].evidence.page_numbers == [2]
    assert all(r.publication_number is None for r in npl)
    for ref in refs:
        ev = ref.evidence
        assert ref.raw_text == ev.text == oa.text[ev.start : ev.end]
        assert ev.page_numbers == [
            p.number for p in oa.pages if p.start < ev.end and p.end > ev.start
        ]
        assert len(ev.text) < 200


def test_five_graph_nodes_and_no_duplicate_edges(citation_result):
    refs = citation_result.rejections[1].cited_references
    assert len(refs) == len({r.citation_id for r in refs}) == 5
    citation_result.rejections[1].cited_references += refs
    graph = build_graph(citation_result.patent, citation_result.rejections, citation_result.impacts)
    nodes = [n for n in graph.nodes if n.kind == "citation"]
    assert len(nodes) == 5
    assert "Lombardi et al · WO2009/013126 A1" in {n.label for n in nodes}
    assert "Greco et al · NPL" in {n.label for n in nodes}
    edges = [e for e in graph.edges if e.relation == "cites"]
    assert len(edges) == 5
    assert all(e.source == "R2" for e in edges)
    assert {e.target for e in edges} == {n.id for n in nodes}


def test_distinct_papers_with_identical_or_similar_authors():
    text = (
        "Claim 1 is rejected under 35 USC 103 over Greco et al., BMC Cancer (2009), 9:436, pp. 1-9; "
        "Greco et al., BMC Cancer (2009), 9:437, pp. 1-9; "
        "Greco et al., BMC Cancer (2010), 9:436, pp. 1-9; "
        "Grecco et al., BMC Cancer (2009), 9:436, pp. 1-9; "
        "Greco et al., Molecular and Cellular Endocrinology (2009), 9:436, pp. 1-9; "
        "and Greco et al., BMC Cancer (2009), 9:436, pp. 1-9."
    )
    refs = extract_local(from_text(text, "oa.txt", "office_action"))[0][0].cited_references
    assert len(refs) == 5
    assert all(r.type == "npl" for r in refs)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("WO2009/013126 A1", "WO2009013126A1"),
        ("WO 2013 / 119950 A2", "WO2013119950A2"),
        ("WO2008074749A1", "WO2008074749A1"),
        ("US 2010/0123456 A1", "US20100123456A1"),
    ],
)
def test_publication_normalization(raw, expected):
    assert normalize_publication(raw) == expected


def test_em_dash_authors_and_no_npl_from_prose():
    text = (
        "Claim 1 is rejected under 35 USC 103 over Lombardi et al. — WO2009/013126 A1. "
        "Bendiera et al. — WO2008/074749 A1; Hout et al. — WO2013/119950 A2. "
        "Greco et al. Discussed a treatment in 2010."
    )
    refs = extract_local(from_text(text, "oa.txt", "office_action"))[0][0].cited_references
    assert len(refs) == 3
    assert all(ref.name and ref.type == "patent" for ref in refs)


def test_structured_extraction_completes_source_chunk(citation_result):
    oa = citation_result.documents[1]
    chunk = next(c for c in chunk_office_action(oa) if "Lombardi" in c.text)
    short_evidence = chunk.text[: chunk.text.index("as unpatentable")].strip()
    draft = RejectionDraft(
        action_type="rejection",
        statute="35 USC 103(a)",
        claims=list(range(1, 20)),
        reason_summary="Existing model summary",
        examiner_explanation="Existing explanation",
        cited_references=[],
        evidence=short_evidence,
    )
    rejection = validate_draft(draft, chunk, oa, "openai")
    assert len(rejection.cited_references) == 5
    assert rejection.reason_summary == draft.reason_summary
    assert rejection.evidence.text == short_evidence


def test_shared_citation_has_edges_to_each_rejection():
    oa = from_text(
        "Claim 1 is rejected under 35 USC 103 over Hout (WO2013/119950 A2).\n"
        "Claim 2 is rejected under 35 USC 103 over Hout (WO2013/119950 A2).",
        "oa.txt",
        "office_action",
    )
    refs = [r.cited_references[0] for r in extract_local(oa)[0]]
    assert refs[0].citation_id == refs[1].citation_id
    assert refs[0].evidence.start != refs[1].evidence.start


def test_npl_volume_issue_boundaries_are_part_of_identity():
    oa = from_text(
        "Claim 1 is rejected under 35 USC 103 over Greco et al., Cancer Research (2010), "
        "Vol. 321(1), pp. 44-49; and Greco et al., Cancer Research (2010), "
        "Vol. 32(11), pp. 44-49.",
        "oa.txt",
        "office_action",
    )
    refs = extract_local(oa)[0][0].cited_references
    assert len(refs) == 2
    assert refs[0].citation_id != refs[1].citation_id


def test_repeated_patent_can_omit_kind_without_merging_different_kinds():
    oa = from_text(
        "Claim 1 is rejected under 35 USC 103 over Hout (WO2013/119950 A2). "
        "The examiner repeats Hout (WO2013/119950). "
        "Smith (WO2010/123456 A1) and Smith (WO2010/123456 A2) are distinct publications.",
        "oa.txt",
        "office_action",
    )
    # Bibliographic identity is independent of whether a reference is relied upon.
    from backend.ingestion.adapters import evidence_at

    refs = extract_citations(oa.text, evidence_at(oa, 0, len(oa.text)), oa)
    assert {r.publication_number for r in refs} == {
        "WO2013119950A2",
        "WO2010123456A1",
        "WO2010123456A2",
    }
