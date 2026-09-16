"""Real Edge upload of both original malformed-PDF regression fixtures."""

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
    for index, name in enumerate(["pp_ex2.pdf", "pp_vd2.pdf"]):
        inputs.nth(index).set_input_files(ROOT / "tests/fixtures/pdf_fallback" / name)
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=180000)
    pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
    summary = pdf.locator("#overlays").evaluate("""() => ({
        pages:model.documents.map(d=>d.pages.length),
        claims:model.items.filter(i=>i.kind==='claim').map(i=>i.claim_number),
        statutes:model.rejections.map(r=>r.statute),
        citations:model.items.filter(i=>i.kind==='citation').length
    })""")
    assert summary == {
        "pages": [47, 13],
        "claims": list(range(1, 21)),
        "statutes": ["35 USC 103(a)"] * 3,
        "citations": 5,
    }, summary
    pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("46")
    evidence = pdf.locator('details[data-rejection-id="R1"]')
    if evidence.get_attribute("open") is None:
        evidence.locator("summary").click()
    evidence.get_by_role("button", name="OA p. 5에서 보기", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("5")
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-1")
    expect(pdf.locator(".current-evidence")).to_contain_text("Office Action p. 5")
    page.screenshot(path=str(ROOT / "data/outputs/pdf-fallback-pp-pair.png"), full_page=True)
    assert not errors, errors
    print(
        "PASS: original pp_ex2/pp_vd2 upload, 47/13 pages, Claims 1-20, 3 section-103 grounds, 5 citations, Claim 1 -> original OA p.5."
    )
    browser.close()
