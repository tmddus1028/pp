"""Optional browser check: uv run --no-project --with playwright python scripts/browser_smoke.py"""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1480, "height": 1120}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    page.get_by_role("button", name="예제 분석 · 가상 문서").click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=30000)
    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    expect(page.get_by_test_id("stMetricValue").first).to_have_text("9", timeout=30000)
    expect(page.locator(".claim-summary")).to_have_count(9)
    page.get_by_role("textbox", name="Claim 번호 검색").fill("4")
    page.get_by_role("textbox", name="Claim 번호 검색").press("Enter")
    expect(page.locator(".claim-summary")).to_have_count(1)
    row = page.locator(".st-key-claim-row-4")
    expect(row.locator(".claim-state")).to_have_text("추가 검토 · 종속 영향")
    expect(row).to_have_css("border-left-color", "rgb(214, 165, 46)")
    row.get_by_text("Claim 4 상세 보기", exact=True).click()
    page.screenshot(path=str(ROOT / "data/outputs/app-preview.png"), full_page=True)
    page.get_by_test_id("stCheckbox").first.locator("label").click()
    expect(page.get_by_role("checkbox").first).to_be_checked()
    page.get_by_text("문서 처리 정보 보기", exact=True).click()
    with page.expect_download() as downloaded:
        page.get_by_role("button", name="분석 JSON 다운로드").click()
    assert downloaded.value.suggested_filename.endswith(".json")
    row.get_by_role("button", name="PDF에서 보기", exact=True).click()
    frame = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(frame.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-4")
    assert not errors, errors
    browser.close()
    print(
        "Browser smoke passed: demo, Claim search, amber status, details, checklist, JSON download, text-source navigation."
    )
