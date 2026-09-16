from collections import Counter

import pytest
from conftest import ROOT

from backend.analysis.citation_analyzer import name_key
from backend.config import Settings
from backend.ingestion.adapters import LocalAdapter, from_text
from backend.schemas import AnalysisResult
from backend.service import analyze
from frontend.review_model import build_review_model

RELIED = {"liu", "donmez", "bakke", "huang", "yao", "nakayama", "motamedi"}
EXPECTED = {
    "R1": {"liu", "donmez"},
    "R2": {"liu", "donmez", "bakke"},
    "R3": {"liu", "donmez", "huang"},
    "R4": {"liu", "donmez", "yao", "nakayama"},
    "R5": {"liu", "donmez", "yao", "nakayama", "motamedi"},
}


@pytest.fixture(scope="module")
def real_result():
    settings = Settings(_env_file=None, llm_provider="local")
    adapter = LocalAdapter(settings)
    return analyze(
        adapter.read(
            (ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf").read_bytes(), "pp_ex3.pdf", "patent"
        ),
        adapter.read(
            (ROOT / "tests/fixtures/oa_status/pp_vd3.pdf").read_bytes(),
            "pp_vd3.pdf",
            "office_action",
        ),
        settings,
    )


def names(result, role):
    return {name_key(c.display_name) for c in result.citations if role in c.citation_roles}


def test_original_pdf_seven_relied_one_supporting_two_recorded(real_result):
    assert names(real_result, "relied_upon") == RELIED
    assert names(real_result, "supporting_evidence") == {"wei"}
    assert names(real_result, "not_relied_upon") == {"oda", "biyikli"}
    assert len(real_result.citations) == 10
    assert Counter(name_key(c.display_name) for c in real_result.citations)["liu"] == 1
    assert len({c.canonical_key for c in real_result.citations}) == 10
    assert [c for c in real_result.citations if name_key(c.display_name) == "liu"][0].type == "npl"


def test_original_rejection_links_and_claim_unions(real_result):
    docs = {c.citation_id: c for c in real_result.citations}
    for rid, expected in EXPECTED.items():
        edges = [e for e in real_result.rejection_citations if e.rejection_id == rid]
        assert {
            name_key(docs[e.citation_id].display_name) for e in edges if e.role == "relied_upon"
        } == expected
        assert {
            name_key(docs[e.citation_id].display_name)
            for e in edges
            if e.role == "supporting_evidence"
        } == ({"wei"} if rid in {"R4", "R5"} else set())
    assert not any(e.rejection_id == "R6" for e in real_result.rejection_citations)
    for author, rids, claims in [
        ("liu", set(EXPECTED), list(range(1, 15)) + [17, 18, 19]),
        ("bakke", {"R2"}, [5, 6]),
        ("huang", {"R3"}, [7, 9]),
        ("motamedi", {"R5"}, [12, 13, 14]),
    ]:
        cid = next(c.citation_id for c in docs.values() if name_key(c.display_name) == author)
        edges = [e for e in real_result.rejection_citations if e.citation_id == cid]
        assert {e.rejection_id for e in edges} == rids
        assert sorted({n for e in edges for n in e.claim_numbers}) == claims


def test_original_occurrence_and_definition_offsets_and_pages(real_result):
    document = real_result.documents[1]
    for evidence in [c.evidence for c in real_result.citations] + [
        e.evidence for e in real_result.rejection_citations
    ]:
        assert document.text[evidence.start : evidence.end] == evidence.text
        assert evidence.page_numbers == [
            p.number for p in document.pages if p.start < evidence.end and p.end > evidence.start
        ]
    liu = next(c for c in real_result.citations if name_key(c.display_name) == "liu")
    assert liu.evidence.page_numbers == [3, 4]
    assert "Application/Control" not in liu.title
    assert "Application/Control" in liu.evidence.text
    aliases = [
        e
        for e in real_result.rejection_citations
        if e.citation_id == liu.citation_id and e.rejection_id != "R1"
    ]
    assert all(len(e.evidence.text) < 50 for e in aliases)
    assert AnalysisResult.model_validate_json(real_result.model_dump_json()) == real_result


def test_ui_unique_cards_graph_nodes_and_roles(real_result):
    model = build_review_model(real_result.model_dump())
    cards = [i for i in model["items"] if i["kind"] == "citation"]
    assert len(cards) == 10
    assert len([i for i in cards if i["citation_role"] == "relied_upon"]) == 7
    liu = [i for i in cards if name_key(i["title"]) == "liu"]
    assert len(liu) == 1 and set(liu[0]["rejection_ids"]) == set(EXPECTED)
    assert len([n for n in real_result.graph.nodes if n.kind == "citation"]) == 8
    assert (
        len(
            [
                e
                for e in real_result.graph.edges
                if e.relation == "cites" and e.citation_role == "relied_upon"
            ]
        )
        == 17
    )
    assert (
        len([e for e in real_result.graph.edges if e.citation_role == "supporting_evidence"]) == 2
    )
    assert not any(e.citation_role == "not_relied_upon" for e in real_result.graph.edges)


def analyze_text(oa, settings):
    return analyze(
        from_text("Claims\n1. A sensor.\n2. The sensor of claim 1.", "p.txt", "patent"),
        from_text(oa, "oa.txt", "office_action"),
        settings,
    )


@pytest.mark.parametrize("spelling", ["Liu et al.", "Liu et al", "LIU ET AL.", "Liu, et al."])
def test_author_punctuation_case_deduplication(settings, spelling):
    oa = (
        "Claim 1 is rejected under 35 USC 103 over Liu et al. (Sensor deposition, Journal, 2020, pp. 1-9).\n"
        f"Claim 2 is rejected under 35 USC 103 over {spelling} (Sensor deposition, Journal, 2020, pp. 1-9)."
    )
    result = analyze_text(oa, settings)
    assert len(result.citations) == 1 and len(result.rejection_citations) == 2


@pytest.mark.parametrize("number", ["US 2004/0188693", "US20040188693", "US 2004/0188693 A1"])
def test_publication_variations_share_key(settings, number):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (US 2004/0188693 A1).\n"
        f"Claim 2 is rejected under 35 USC 103 over Smith ({number}).",
        settings,
    )
    assert len(result.citations) == 1
    assert result.citations[0].canonical_key == "publication:US20040188693"


def test_distinct_explicit_kinds_remain_distinct(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (US 2004/0188693 A1) in view of Smith (US 2004/0188693 A2).",
        settings,
    )
    assert len(result.citations) == 2


def test_doi_identity_precedes_author_and_title(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (A sensor paper, Journal, 2020, pp. 1-9; https://doi.org/10.1234/ABC).\n"
        "Claim 2 is rejected under 35 USC 103 over SMITH (Sensor paper, Journal, 2020, pp. 1-9; DOI:10.1234/abc).",
        settings,
    )
    assert len(result.citations) == 1
    assert result.citations[0].canonical_key == "doi:10.1234/abc"


def test_same_author_different_papers_and_ambiguous_alias_not_merged(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (A sensor paper, Journal, 2020, pp. 1-9) "
        "in view of Smith (A coating paper, Journal, 2020, pp. 11-19).\n"
        "Claim 2 is rejected under 35 USC 103 over Smith (Smith).",
        settings,
    )
    assert len(result.citations) == 3
    assert result.rejections[1].cited_references[0].type == "unknown"


def test_duplicate_mentions_one_card_distinct_sources(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (US 2004/0188693 A1) and Smith (US20040188693).",
        settings,
    )
    assert len(result.citations) == len(result.rejections[0].cited_references) == 1
    assert len(result.rejection_citations) == 2
    model = build_review_model(result.model_dump())
    assert len([i for i in model["items"] if i["kind"] == "citation"]) == 1
    assert len({a["id"] for a in model["annotations"]}) == len(model["annotations"])


def test_same_document_can_have_different_roles_per_rejection(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Smith (US 2004/0188693).\n"
        "Claim 2 is rejected under 35 USC 103 over Jones (US 2005/0188693). "
        "Smith (US 2004/0188693) is presented as evidence of sensor properties.",
        settings,
    )
    smith = next(c for c in result.citations if name_key(c.display_name) == "smith")
    assert set(smith.citation_roles) == {"relied_upon", "supporting_evidence"}
    assert len([e for e in result.rejection_citations if e.citation_id == smith.citation_id]) == 2


def test_bare_author_mention_never_creates_new_citation(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 112. Liu discusses methods. Wei has another opinion.",
        settings,
    )
    assert result.citations == []


def test_prior_definition_does_not_override_current_reliance_role(settings):
    result = analyze_text(
        "Claim 1 is rejected under 35 USC 103 over Jones (US 2005/0188693). "
        "Smith (US 2004/0188693) is presented as evidence of sensor properties.\n"
        "Claim 2 is rejected under 35 USC 103 over Smith as applied to claim 1 above.",
        settings,
    )
    smith = next(c for c in result.citations if name_key(c.display_name) == "smith")
    assert {
        e.rejection_id: e.role
        for e in result.rejection_citations
        if e.citation_id == smith.citation_id
    } == {"R1": "supporting_evidence", "R2": "relied_upon"}
