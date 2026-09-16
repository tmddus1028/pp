"""Claim list checks shared by the full PDF regression and the short fixture run."""

from pathlib import Path

from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]


def search_claim(page, value):
    field = page.get_by_role("textbox", name="Claim 번호 검색", exact=True)
    field.fill(value)
    field.press("Enter")


def check_claim_analysis(page, pdf, claim_page="41", ocr=True):
    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    expect(page.locator(".claim-summary")).to_have_count(19, timeout=30000)
    expect(page.get_by_test_id("stMetricValue")).to_have_text(["19", "2", "19", "0", "0"])
    expect(page.get_by_test_id("stMetricLabel")).to_have_text(
        [
            "전체 청구항",
            "거절/지적 사유",
            "직접 지적 Claim",
            "추가 검토 Claim",
            "허용 Claim",
        ]
    )
    info = (
        page.get_by_test_id("stExpander")
        .filter(has=page.locator("summary").filter(has_text="문서 처리 정보 보기"))
        .first
    )
    expect(info.locator("details").first).not_to_have_attribute("open", "")
    expect(page.locator(".analysis-complete")).to_have_text(
        "✓ 문서 분석 완료" + (" · OCR 사용됨" if ocr else "")
    )
    assert not page.get_by_test_id("stAlert").count()
    assert not page.locator('iframe[title*="graph"]').count()
    assert not page.locator('iframe[title*="relationship_map"]').count()
    assert page.locator(".claim-summary").first.bounding_box()["y"] < 440
    assert page.locator(".st-key-claim-row-1").bounding_box()["height"] < 165
    relations = page.locator(".st-key-claim-row-1 .claim-relations").bounding_box()
    disclosure = page.locator(".st-key-claim-row-1 summary").first.bounding_box()
    assert disclosure["y"] >= relations["y"] + relations["height"] + 4
    page.screenshot(path=str(ROOT / "data/outputs/claim-analysis-desktop.png"), full_page=False)
    expect(page.locator(".st-key-claim-row-1")).to_have_css("border-left-color", "rgb(224, 82, 82)")
    expect(page.get_by_text("분석 provider: local", exact=True)).not_to_be_visible()
    info.locator("summary").first.click()
    expect(page.get_by_text("분석 provider: local", exact=True)).to_be_visible()
    expect(page.get_by_text("PDF 화면 renderer: PDFium", exact=True)).to_be_visible()
    if ocr:
        expect(info.get_by_text("OCR 엔진: tesseract", exact=True)).to_be_visible()
        expect(info.get_by_text("OCR PDF renderer: pdfium", exact=True)).to_be_visible()
    with page.expect_download() as download:
        info.get_by_role("button", name="분석 JSON 다운로드").click()
    assert download.value.suggested_filename.endswith(".json")
    info.locator("summary").first.click()
    expect(page.get_by_text("분석 provider: local", exact=True)).not_to_be_visible()

    page.get_by_text("추가 검토", exact=True).click()
    expect(page.locator(".claim-summary")).to_have_count(0)
    expect(page.locator(".claim-empty")).to_be_visible()
    expect(page.get_by_role("radio", name="§112", exact=True)).to_have_count(0)
    expect(page.get_by_role("radio", name="§103", exact=True)).to_have_count(0)
    page.get_by_text("허용", exact=True).click()
    expect(page.locator(".claim-summary")).to_have_count(0)
    page.get_by_test_id("stRadio").filter(has_text="추가 검토").get_by_text(
        "직접 지적", exact=True
    ).click()
    expect(page.locator(".claim-summary")).to_have_count(19)
    page.get_by_text("전체", exact=True).click()
    search_claim(page, "1")
    expect(page.locator(".claim-summary")).to_have_count(1)
    expect(page.locator(".claim-summary")).to_have_attribute("data-claim", "1")
    search_claim(page, "14")
    expect(page.locator(".claim-summary")).to_have_count(1)
    row = page.locator(".st-key-claim-row-14")
    expect(row.locator(".claim-statutes")).to_have_text("35 U.S.C. 112 · 35 U.S.C. 103(a)")
    expect(row.locator(".claim-relations")).to_contain_text("상위 Claim · Claim 1")
    expect(row.locator(".claim-relations")).to_contain_text("직접 종속 Claim · 1개")
    row.locator("summary").filter(has_text="Claim 14 상세 보기").click()
    expect(row.get_by_text("Claim 원문", exact=True)).to_be_visible()
    expect(row.get_by_text("관련 specification", exact=True)).to_be_visible()
    for name in ["Lombardi", "Bendiera", "Hout", "Greco", "Lipska"]:
        expect(row.locator("summary").filter(has_text=name)).to_have_count(1)
    row.locator("summary").filter(has_text="Greco").click()
    expect(
        row.locator(".readable-text").filter(has_text="Molecular and Cellular Endocrinology").last
    ).to_be_visible()
    checkbox = row.get_by_role("checkbox").first
    if not checkbox.is_checked():
        row.get_by_test_id("stCheckbox").first.locator("label").click()
    expect(checkbox).to_be_checked()
    label = row.get_by_test_id("stCheckbox").first.locator("label").inner_text().strip()
    row.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value(claim_page, timeout=30000)
    expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-14")
    expect(pdf.locator('.annotation.selected[data-item-id="claim-14"]')).to_be_visible(
        timeout=15000
    )
    expect(pdf.get_by_role("checkbox", name=label, exact=True)).to_be_checked()
    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    expect(page.get_by_role("textbox", name="Claim 번호 검색")).to_have_value("14")
    expect(row.locator(".claim-current")).to_have_text("선택됨")
    row.locator("summary").filter(has_text="Claim 14 상세 보기").click()
    expect(row.get_by_role("checkbox").first).to_be_checked()
    row.locator("summary").filter(has_text="Claim 14 상세 보기").click()
    search_claim(page, "999")
    expect(page.locator(".claim-summary")).to_have_count(0)
    search_claim(page, "")
    expect(page.locator(".claim-summary")).to_have_count(19)
    page.screenshot(path=str(ROOT / "data/outputs/claim-analysis-desktop.png"), full_page=False)
    page.set_viewport_size({"width": 900, "height": 900})
    assert page.locator(".claim-summary").first.bounding_box()["y"] < 500
    assert page.locator(".st-key-claim-row-1").bounding_box()["width"] <= 900
    expect(
        page.locator(".st-key-claim-row-1").get_by_role("button", name="PDF에서 보기")
    ).to_be_visible()
    assert (
        page.locator(".st-key-claim-row-1")
        .get_by_role("button", name="PDF에서 보기")
        .bounding_box()["width"]
        >= 120
    )
    page.screenshot(path=str(ROOT / "data/outputs/claim-analysis-narrow.png"), full_page=False)
    page.set_viewport_size({"width": 1366, "height": 768})
    page.locator(".st-key-claim-row-4").get_by_role("button", name="PDF에서 보기").click()
    expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-4")
    print(
        "Claim analysis passed: 19 compact rows, hidden processing/debug, exact search, 4 status filters, 5 citations, checkbox/selection roundtrip, PDF page and narrow layout."
    )
