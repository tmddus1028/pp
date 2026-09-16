"""Upload the original heading-free patent; OA is a synthetic transport fixture."""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1366, "height": 950})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf")
    inputs.nth(1).set_input_files(
        {
            "name": "synthetic_oa.txt",
            "mimeType": "text/plain",
            "buffer": b"Claims 1-20 are rejected under 35 U.S.C. 103 over Smith.",
        }
    )
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=120000)
    pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
    numbers = pdf.locator("#overlays").evaluate(
        "() => model.items.filter(i=>i.kind==='claim').map(i=>i.claim_number)"
    )
    assert numbers == list(range(1, 21)), numbers
    for number, expected_page in [(1, "17"), (19, "18"), (20, "18")]:
        pdf.get_by_role("button", name=f"Claim {number} · 직접 지적", exact=True).click()
        expect(pdf.locator("#page-number")).to_have_value(expected_page)
        expect(pdf.locator(".review-card.expanded")).to_have_attribute(
            "data-review-id", f"claim-{number}"
        )
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    page.screenshot(path=str(ROOT / "data/outputs/claim-section-pp-ex3.png"), full_page=True)
    assert not errors, errors
    print("PASS: original pp_ex3 upload; Claims 1-20; Claim 1 -> p.17, Claims 19/20 -> p.18.")
    browser.close()
