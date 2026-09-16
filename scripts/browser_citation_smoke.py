"""Optional: uv run --no-project --with playwright python scripts/browser_citation_smoke.py"""

from pathlib import Path

from browser_accordion_flow import check_accordion
from browser_claim_analysis_flow import check_claim_analysis
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    uploads = page.locator('input[type="file"]')
    uploads.nth(0).set_input_files(
        ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf"
    )
    uploads.nth(1).set_input_files(
        ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf"
    )
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=30000)
    frame = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(frame.locator("#page-image")).to_be_visible(timeout=30000)
    check_accordion(page, frame, claim_page="2")
    check_claim_analysis(page, frame, claim_page="2", ocr=False)
    assert not errors, errors
    browser.close()
    print(
        "Browser passed: real patent page upload, 5 unique citations, NPL source click, Claim click."
    )
