"""Separate actual PDF status checks from the user's reconstructed 4/6/10 case."""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def upload(page, patent, oa):
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(patent)
    inputs.nth(1).set_input_files(oa)
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=120000)
    pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
    return pdf


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1450, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    pdf = upload(
        page,
        ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf",
        ROOT / "tests/fixtures/oa_status/pp_vd3.pdf",
    )
    expect(pdf.get_by_role("button", name="직접 지적 17", exact=True)).to_be_visible()
    expect(pdf.get_by_role("button", name="종속 영향 / Objection 2", exact=True)).to_be_visible()
    expect(pdf.get_by_role("button", name="허용 0", exact=True)).to_be_visible()
    expect(pdf.locator("#rejection-links")).not_to_contain_text("unknown")
    pdf.get_by_role("button", name="Claim 15 · Objection · 추가 검토", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("17")
    expect(pdf.locator('#overlays .direct_rejection[data-item-id="claim-15"]')).to_have_count(0)
    expect(pdf.locator('#overlays .dependency[data-item-id="claim-15"]')).not_to_have_count(0)
    detail = pdf.locator('details[data-rejection-id="R6"]')
    if detail.get_attribute("open") is None:
        detail.locator("summary").click()
    detail.get_by_role("button", name="OA p. 10에서 보기", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("10")
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-15")
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    page.screenshot(path=str(ROOT / "data/outputs/oa-status-actual.png"), full_page=True)
    pdf.get_by_role("button", name="Claim 20 · 취소됨", exact=True).click()
    expect(pdf.locator(".review-card.expanded .card-body")).to_contain_text("cancelled")
    assert not errors, errors
    page.close()

    page = browser.new_page(viewport={"width": 1450, "height": 1000})
    page.on("pageerror", lambda error: errors.append(str(error)))
    # Actual patent layout, synthetic OA from the user's expected statuses.
    pdf = upload(
        page,
        ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf",
        ROOT / "tests/fixtures/oa_status/18731426_reconstructed.txt",
    )
    for label in ["직접 지적 4", "종속 영향 / Objection 6", "허용 10", "인용 문헌 2"]:
        expect(pdf.get_by_role("button", name=label, exact=True)).to_be_visible()
    pdf.get_by_role("button", name="Claim 15 · 허용", exact=True).click()
    expect(pdf.locator('#overlays .direct_rejection[data-item-id="claim-15"]')).to_have_count(0)
    expect(pdf.locator(".review-card.expanded .card-body")).to_contain_text(
        "Claims 11-20 are allowed"
    )
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    page.screenshot(path=str(ROOT / "data/outputs/oa-status-reconstructed.png"), full_page=True)
    assert not errors, errors
    print(
        "PASS actual 17/2/0 + canceled20; reconstructed 4/6/10 + Wu/Ando; no red Claim15/16; OA navigation retained."
    )
    browser.close()
