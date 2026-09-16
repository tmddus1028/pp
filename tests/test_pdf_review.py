import hashlib
from copy import deepcopy
from io import BytesIO

import pytest
from conftest import ROOT
from pypdf import PdfReader, PdfWriter

from backend.errors import OCRDependencyError
from backend.ingestion.adapters import LocalAdapter, from_text
from backend.ingestion.ocr import resolve_tesseract
from backend.ingestion.ocr_worker import word_boxes
from backend.service import analyze
from frontend.pdf_adapter import attach_coordinates, render_page, search_boxes
from frontend.review_model import build_review_model

FIXTURES = ROOT / "tests/fixtures/pdf_review"


def pdf_result(settings, patent="patent.pdf", oa="office_action_support.pdf"):
    adapter = LocalAdapter(settings)
    inputs = [(FIXTURES / name).read_bytes() for name in [patent, oa]]
    documents = [
        adapter.read(data, name, kind)
        for data, name, kind in zip(inputs, [patent, oa], ["patent", "office_action"])
    ]
    return analyze(*documents, settings).model_dump(mode="json"), dict(
        zip([d.document_id for d in documents], inputs)
    )


def test_annotations_preserve_analysis_and_original_pdf(settings):
    result, assets = pdf_result(settings)
    before = deepcopy(result)
    hashes = {key: hashlib.sha256(data).hexdigest() for key, data in assets.items()}
    model = attach_coordinates(build_review_model(result), result, assets)
    assert result == before
    assert hashes == {key: hashlib.sha256(data).hexdigest() for key, data in assets.items()}
    assert {a["type"] for a in model["annotations"]} >= {
        "direct_rejection",
        "dependency",
        "specification",
    }
    for annotation in model["annotations"]:
        assert annotation["boxes"], annotation
        for x1, y1, x2, y2 in annotation["boxes"]:
            assert 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1
        assert annotation["match_coverage"] >= 0.85
        assert annotation["location_method"] == "text_layer"


def test_explicit_specification_and_figure_only(settings):
    result, _ = pdf_result(settings)
    model = build_review_model(result)
    support = [i for i in model["items"] if i["kind"] == "specification"]
    assert {i["title"] for i in support} == {"Paragraph [0018]", "Figure 1"}
    assert all(i["evidence"]["page_numbers"] == [1] for i in support)
    assert {i["id"] for i in support} <= set(model["items"][0]["support_ids"])
    result["rejections"][0]["evidence"]["text"] = "No explicit location references."
    assert not [i for i in build_review_model(result)["items"] if i["kind"] == "specification"]


def test_direct_priority_and_dependency_membership_use_existing_impacts(settings):
    result, _ = pdf_result(settings)
    model = build_review_model(result)
    claims = {i["claim_number"]: i for i in model["items"] if i["kind"] == "claim"}
    assert claims[1]["direct"] == ["R1"]
    assert claims[3]["indirect"] == ["R1"]
    assert claims[3]["depends_on"] == [2]
    assert not claims[4]["direct"] and not claims[4]["indirect"]
    claim1 = next(a for a in model["annotations"] if a["item_id"] == "claim-1")
    assert claim1["linked_rejection_id"] == "R1"
    assert claim1["statute"] == "35 USC 112(b)"


def test_real_patent_cross_page_coordinates_and_five_citations(settings):
    adapter = LocalAdapter(settings)
    data = (ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf").read_bytes()
    oa = (FIXTURES / "office_action_reconstructed.pdf").read_bytes()
    patent = adapter.read(data, "patent.pdf", "patent")
    action = adapter.read(oa, "oa.pdf", "office_action")
    result = analyze(patent, action, settings).model_dump(mode="json")
    model = attach_coordinates(
        build_review_model(result), result, {patent.document_id: data, action.document_id: oa}
    )
    assert len([i for i in model["items"] if i["kind"] == "citation"]) == 5
    claim1 = [a for a in model["annotations"] if a["item_id"] == "claim-1"]
    assert [a["page"] for a in claim1] == [1, 2]
    assert all(a["boxes"] and a["match_coverage"] == 1 for a in claim1)
    assert all(a["linked_rejection_ids"] == ["R1", "R2"] for a in claim1)
    assert "35 USC 112" in claim1[0]["statute"] and "35 USC 103(a)" in claim1[0]["statute"]
    assert all(i["direct"] for i in model["items"] if i["kind"] == "claim")
    claims = {i["claim_number"]: i for i in model["items"] if i["kind"] == "claim"}
    assert "R1" in claims[2]["indirect"] and "R2" in claims[2]["direct"]
    assert all(a["boxes"] for a in model["annotations"] if a["type"] == "citation")


def test_unmatched_evidence_falls_back_to_page_without_fabricated_bbox(settings):
    result, assets = pdf_result(settings)
    patent = result["documents"][0]
    patent["pages"][1]["text"] = "z" * len(patent["pages"][1]["text"])
    model = attach_coordinates(build_review_model(result), result, assets)
    claim = next(a for a in model["annotations"] if a["item_id"] == "claim-1")
    assert claim["boxes"] == [] and claim["bbox"] is None
    assert claim["location_method"] == "page_only"


def test_text_input_review_has_no_fake_pdf(settings):
    result = analyze(
        from_text("Claims\n1. A device.", "patent.txt", "patent"),
        from_text("Claim 1 is rejected under 35 USC 112.", "oa.txt", "office_action"),
        settings,
    )
    model = attach_coordinates(
        build_review_model(result.model_dump(mode="json")), result.model_dump(mode="json"), {}
    )
    assert all(a["location_method"] == "text" and not a["boxes"] for a in model["annotations"])


def test_rotated_cropped_pdf_coordinates_and_rendering(settings):
    reader = PdfReader(FIXTURES / "patent.pdf")
    writer = PdfWriter()
    page = reader.pages[1]
    page.cropbox.lower_left = (20, 20)
    page.cropbox.upper_right = (590, 770)
    page.rotate(90)
    writer.add_page(page)
    stream = BytesIO()
    writer.write(stream)
    data = stream.getvalue()
    patent = LocalAdapter(settings).read(data, "rotated.pdf", "patent")
    result = analyze(
        patent,
        from_text("Claim 1 is rejected under 35 USC 112.", "oa.txt", "office_action"),
        settings,
    ).model_dump(mode="json")
    model = attach_coordinates(build_review_model(result), result, {patent.document_id: data})
    assert next(a for a in model["annotations"] if a["item_id"] == "claim-1")["boxes"]
    image = render_page(data, 1)
    assert image["width"] == 750 and image["height"] == 570
    assert image["image"].startswith("data:image/png;base64,")


def test_search_returns_real_boxes_and_no_match_is_empty(settings):
    data = (FIXTURES / "patent.pdf").read_bytes()
    document = LocalAdapter(settings).read(data, "patent.pdf", "patent")
    assert search_boxes(data, 2, document.pages[1].text, "sensor measures temperature")
    assert search_boxes(data, 2, document.pages[1].text, "invented phrase") == []


@pytest.mark.ocr_integration
def test_real_ocr_metadata_drives_scanned_pdf_annotations(settings):
    try:
        resolve_tesseract()
    except OCRDependencyError as exc:
        pytest.skip(str(exc))
    result, assets = pdf_result(settings, "patent_scan.pdf", "office_action_scan.pdf")
    assert [(r["statute"], r["claims"]) for r in result["rejections"]] == [("35 USC 112(b)", [1])]
    raw_before = [deepcopy(d["metadata"]["ocr_raw_text"]) for d in result["documents"]]
    model = attach_coordinates(build_review_model(result), result, assets)
    for document in result["documents"]:
        assert document["metadata"]["ocr_words"]
    claim1 = next(a for a in model["annotations"] if a["item_id"] == "claim-1")
    assert claim1["boxes"] and claim1["location_method"] == "ocr"
    assert claim1["type"] == "direct_rejection"
    claim3 = next(a for a in model["annotations"] if a["item_id"] == "claim-3")
    assert claim3["boxes"] and claim3["type"] == "dependency"
    assert raw_before == [d["metadata"]["ocr_raw_text"] for d in result["documents"]]


def test_ocr_word_coordinate_conversion_retains_tokens():
    data = {
        "text": ["", "35", "U.S.C.", "§"],
        "width": [0, 10, 30, 7],
        "height": [0, 20, 20, 20],
        "left": [0, 10, 30, 65],
        "top": [0, 20, 20, 20],
        "block_num": [0, 1, 1, 1],
        "line_num": [0, 1, 1, 1],
        "conf": [-1, 99, 98, 95],
    }
    words = word_boxes(data, 100, 200)
    assert [w["text"] for w in words] == ["35", "U.S.C.", "§"]
    assert words[0]["bbox"] == [0.1, 0.1, 0.2, 0.2]
