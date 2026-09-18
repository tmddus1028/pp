"""Real Korean goldens and failure boundaries, independent of US parsers."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.improvements.context import build_context
from backend.improvements.models import ImprovementRequest
from backend.jurisdictions.korean import analyze_korean
from backend.main import app
from frontend.review_model import build_review_model
from korean_prototype.kr_review.ingestion import read_document
from korean_prototype.kr_review.models import ReviewError
from korean_prototype.kr_review.oa import canonical_publication, statute
from korean_prototype.kr_review.parsers import extract_claims
from korean_prototype.kr_review.service import analyze
from korean_prototype.kr_review.status import extract_statuses
from korean_prototype.kr_review.versions import select_version

ROOT = Path(__file__).resolve().parents[1]
GOLDENS = sorted((ROOT / "data/fixtures/korean").glob("*.json"))


@pytest.mark.parametrize("truth_file", GOLDENS, ids=lambda p: p.stem)
@pytest.mark.parametrize("format", ["xml", "pdf"])
def test_real_goldens(truth_file, format):
    truth = json.loads(truth_file.read_text(encoding="utf8"))
    for f in truth["files"]:
        assert hashlib.sha256((ROOT / f["path"]).read_bytes()).hexdigest() == f["sha256"]
    pat = next(ROOT / f["path"] for f in truth["files"] if f["role"] == "patent")
    oa = next(
        ROOT / f["path"]
        for f in truth["files"]
        if f["role"] == "office_action" and f["path"].endswith("." + format)
    )
    r = analyze(pat.read_bytes(), pat.name, oa.read_bytes(), oa.name)
    assert r.application_number == truth["application_number"]
    assert [c.number for c in r.claims] == truth["claims"]
    assert {str(c.number): c.depends_on for c in r.claims} == truth["dependencies"]
    refs = {c.citation_id: c.publication_number or c.canonical_key for c in r.citations}
    assert [
        {
            "statute_code": g.statute_code,
            "claims": g.claims,
            "citations": [refs[c] for c in g.citation_ids],
        }
        for g in r.rejections
    ] == truth["rejections"]
    assert r.direct_claims == truth["statuses"]["rejected"]
    assert {str(s.claim_number): s.status for s in r.claim_statuses} == {
        str(n): status for status, numbers in truth["statuses"].items() for n in numbers
    }
    assert {str(c.number): c.evidence.page_numbers[0] for c in r.claims} == truth["evidence"][
        "claim_body_start_page"
    ]
    if format == "pdf":
        assert [g.evidence.page_numbers[0] for g in r.rejections] == truth["evidence"][
            "rejection_start_pages"
        ]
    assert not any(s.status == "allowable" for s in r.claim_statuses)
    documents = {d.document_id: d for d in r.documents}
    for e in [
        *[c.evidence for c in r.claims],
        *[g.evidence for g in r.rejections],
        *[c.evidence for c in r.citations],
        *[link.evidence for link in r.evidence_links],
    ]:
        doc = documents[e.document_id]
        assert doc.text[e.start : e.end] == e.text
        assert e.page_numbers == [
            p.number for p in doc.pages if p.start < e.end and e.start < p.end
        ]
        if doc.kind == "office_action" and format == "xml":
            assert e.xml_path


@pytest.mark.parametrize(
    "heading", ["청구항 1.", "청구항 제1항.", "【청구항 1】", "[청구항 1]", "청구항1"]
)
def test_headings(heading):
    d = read_document(
        ("청구범위\n" + heading + "\n검출부를 포함하는 장치.").encode(), "p.txt", "patent"
    )
    assert extract_claims(d)[0].number == 1


def test_conservative_missing_title_and_dependency():
    prose = "일반 설명 문단입니다.\n" * 50
    text = (
        prose
        + "청구항 1\n센서를 포함하는 장치.\n청구항 2\n청구항 1에 있어서, 통신부를 포함하는 장치.\n청구항 3\n제1항 및 제2항에 있어서, 저장부를 포함하는 장치."
    )
    claims = extract_claims(read_document(text.encode(), "p.txt", "patent"))
    assert [c.depends_on for c in claims] == [[], [1], [1, 2]]
    with pytest.raises(ReviewError):
        extract_claims(read_document((prose + "1. 목록\n2. 다른 항목").encode(), "p.txt", "patent"))


@pytest.mark.parametrize(
    "value", ["특허법 제29조 제2항", "특허법 제29조제2항", "제29조제2항", "특허법 29조 2항"]
)
def test_statute(value):
    assert statute(value)[:2] == ("특허법 제29조제2항", "KR_PATENT_ACT_29_2")


@pytest.mark.parametrize(
    "value", ["KR10-2015-0096573", "KR 2015-0096573 A", "KR20150096573A", "10-2015-0096573"]
)
def test_canonical(value):
    assert canonical_publication(value) == "KR20150096573A"


def test_real_api_reference_context_partial_failure_and_source_navigation():
    data = ROOT / "korean_prototype/data/kr_1020190000844"
    pat = data / "KR20190025857A.pdf"
    oa = data / "office_action_20190409.xml"
    refs = [(p.name, p.read_bytes()) for p in data.glob("KR2015*.pdf")]
    r = analyze_korean(
        pat.read_bytes(),
        pat.name,
        oa.read_bytes(),
        oa.name,
        references=refs + [("broken.pdf", b"broken")],
    )
    assert len(r.documents) == 5
    assert any("사용 불가" in w for w in r.warnings)
    context, sources, _ = build_context(ImprovementRequest(analysis=r, claim_number=1))
    assert all(c["original_available"] for c in context["citations"])
    assert any(s.kind == "citation_original" for s in sources)
    assert any(s.kind == "specification" for s in sources)
    model = build_review_model(r.model_dump(mode="json"))
    assert len([i for i in model["items"] if i["kind"] == "citation"]) == 3
    assert all(i["source_links"] for i in model["items"] if i["kind"] == "citation")
    with TestClient(app) as client:
        response = client.post(
            "/analyze/files?jurisdiction=kr",
            files=[
                ("patent", (pat.name, pat.read_bytes())),
                ("office_action", (oa.name, oa.read_bytes())),
                *[("references", ref) for ref in refs],
            ],
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["documents"]) == 5


def test_status_labels_do_not_create_rejections():
    text = "청구범위\n" + "\n".join(f"청구항 {n}\n검출부를 포함하는 장치." for n in range(1, 8))
    claims = extract_claims(read_document(text.encode(), "claims.txt", "patent"))
    oa = read_document(
        (
            "특허 가능한 청구항 : 제1항\n보정이 필요한 청구항 : 제2항\n철회된 청구항 : 제3항\n삭제된 청구항 : 제4항\n보정된 청구항 : 제5항\n심사 대상 청구항 : 제6항"
        ).encode(),
        "oa.txt",
        "office_action",
    )
    states = extract_statuses(claims, [], oa)
    assert [s.status for s in states] == [
        "allowable",
        "objected",
        "withdrawn",
        "canceled",
        "amended",
        "pending",
        "unknown",
    ]
    assert all(s.raw_status for s in states[:-1])


def test_version_history_does_not_silently_select_a_date_candidate():
    old = (b"old", "old.txt")
    new = (b"new", "new.txt")
    oldhash = hashlib.sha256(old[0]).hexdigest()
    newhash = hashlib.sha256(new[0]).hexdigest()
    history = {
        "submissions": [
            {"sha256": oldhash, "submitted_at": "2018-01-01"},
            {"sha256": newhash, "submitted_at": "2019-02-01"},
        ]
    }
    selected, status = select_version(old, [new], history, "2019-04-09")
    assert (
        selected == old
        and status["candidate_sha256"] == newhash
        and status["status"] == "uncertain"
    )
    history["selected_sha256"] = newhash
    selected, status = select_version(old, [new], history, "2019-04-09")
    assert selected == new and status["selection_source"] == "user_supplied_history"
    with pytest.raises(ReviewError):
        select_version(old, [new], history, "2019-01-01")


def test_revision_uses_actual_reference_text_and_retains_analysis():
    from backend.improvements.retrieval import retrieved_context
    from backend.improvements.revision_models import RevisionRequest

    data = ROOT / "korean_prototype/data/kr_1020190000844"
    r = analyze_korean(
        (data / "KR20190025857A.pdf").read_bytes(),
        "patent.pdf",
        (data / "office_action_20190409.xml").read_bytes(),
        "oa.xml",
        references=[(p.name, p.read_bytes()) for p in data.glob("KR2015*.pdf")],
    )
    before = r.model_dump_json()
    text = r.patent.claims[0].text
    context, sources, _, _, _ = retrieved_context(
        RevisionRequest(analysis=r, claim_number=1, revised_text=text), [("E1", text)]
    )
    assert context["retrieval"]["reference_candidates"]
    assert any(
        s.kind == "citation_original" and s.provenance == "system_retrieved_evidence"
        for s in sources
    )
    assert all(c["original_evidence_ids"] for c in context["citations"])
    assert r.model_dump_json() == before


def test_ocr_candidate_heading_preserves_raw_and_requires_both_boundaries():
    from korean_prototype.kr_review.models import Document

    text = "총구봉유\n청구항 1\n" + ("센서와 통신부를 포함하는 장치. " * 12) + "\n발명의 솔평\n설명"
    d = Document(
        document_id="ocr-test",
        filename="test.pdf",
        kind="patent",
        text=text,
        metadata={"ocr_used": True},
    )
    c = extract_claims(d)[0]
    assert d.text == text and c.evidence.text == text[c.evidence.start : c.evidence.end]
    assert "발명의" not in c.text
    d.text = d.text.replace("발명의 솔평", "일반 문장")
    with pytest.raises(ReviewError):
        extract_claims(d)


def test_common_api_explicit_version_selection_and_invalid_history():
    data = ROOT / "korean_prototype/data/kr_1020190000844"
    patent = (data / "KR20190025857A.pdf").read_bytes()
    oa = (data / "office_action_20190409.xml").read_bytes()
    # Synthetic amended claim: exercises selection only, not a real filing history.
    amended = (
        "출원번호 10-2019-0000844\n청구범위\n청구항 1\n통신부를 포함하는 전자쿠폰 장치.".encode()
    )
    digest = hashlib.sha256(amended).hexdigest()
    history = {
        "submissions": [{"sha256": digest, "submitted_at": "2019-03-01"}],
        "selected_sha256": digest,
    }
    files = [
        ("patent", ("patent.pdf", patent)),
        ("office_action", ("oa.xml", oa)),
        ("amendments", ("amended.txt", amended)),
    ]
    with TestClient(app) as client:
        response = client.post(
            "/analyze/files?jurisdiction=kr",
            files=files,
            data={"version_history": json.dumps(history)},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["patent"]["claims"][0]["text"] == "통신부를 포함하는 전자쿠폰 장치."
        assert result["claim_version"]["status"] == "uncertain"
        for invalid in ["{", "[]"]:
            assert (
                client.post(
                    "/analyze/files?jurisdiction=kr", files=files, data={"version_history": invalid}
                ).status_code
                == 422
            )


def test_reference_number_mismatch_is_not_linked():
    data = ROOT / "korean_prototype/data/kr_1020190000844"
    mismatched = ROOT / "data/fixtures/korean/references/KR20070073517A.pdf"
    r = analyze_korean(
        (data / "KR20190025857A.pdf").read_bytes(),
        "patent.pdf",
        (data / "office_action_20190409.xml").read_bytes(),
        "oa.xml",
        references=[(mismatched.name, mismatched.read_bytes())],
    )
    assert all(c.source_document_id is None for c in r.citations)
    assert any("일치하지 않아 연결하지 않았습니다" in w for w in r.warnings)
