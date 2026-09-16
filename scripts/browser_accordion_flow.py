"""Actual patent Claim 7/14 accordion regression, including ordinary reentry."""

from pathlib import Path

from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]


def check_accordion(page, pdf, claim_page="41"):
    def closed():
        expect(pdf.locator(".card-body")).to_have_count(0)
        expect(pdf.locator('.card-select[aria-expanded="true"]')).to_have_count(0)

    def opened(number):
        expect(pdf.locator(".card-body")).to_have_count(1)
        expect(pdf.locator(".review-card.expanded")).to_have_attribute(
            "data-review-id", f"claim-{number}"
        )
        expect(pdf.locator('.card-select[aria-expanded="true"]')).to_have_count(1)

    def click(number):
        pdf.get_by_role("button", name=f"Claim {number} · 직접 지적", exact=True).click()

    closed()
    expect(pdf.locator(".review-card.active")).to_have_count(0)
    expect(pdf.locator(".annotation.selected")).to_have_count(0)
    original = pdf.locator("#overlays").evaluate("() => JSON.stringify(model)")
    assert pdf.locator("#overlays").evaluate(
        "() => state.selected === null && state.expanded === null"
    )
    page.screenshot(path=str(ROOT / "data/outputs/review-accordion-initial.png"), full_page=True)
    # Filters must also work with a null selection and must not expand the first result.
    pdf.get_by_role("button", name="직접 지적 19", exact=True).click()
    closed()
    click(7)
    opened(7)
    expect(pdf.locator("#page-number")).to_have_value(claim_page)
    click(14)
    opened(14)
    expect(pdf.locator('.annotation.selected[data-item-id="claim-14"]')).to_be_visible(
        timeout=15000
    )
    expect(pdf.locator(".review-card.expanded .card-index")).to_have_text("14")
    expect(pdf.locator(".card-body")).to_contain_text("분석 설명")
    expect(pdf.locator(".card-body")).to_contain_text("Claim 원문")
    expect(pdf.locator(".card-body")).to_contain_text("Office Action 원문 근거")
    expect(pdf.locator(".card-body")).to_contain_text("종속 관계")
    expect(pdf.locator(".card-body")).to_contain_text("관련 인용문헌 · 5개")
    expect(pdf.locator(".card-body")).to_contain_text("관련 specification")
    expect(pdf.locator(".card-body")).to_contain_text("검토 체크리스트")
    pdf.get_by_role("checkbox").first.check()
    click(14)
    closed()
    expect(pdf.locator("#page-number")).to_have_value(claim_page)
    expect(pdf.locator('.annotation.selected[data-item-id="claim-14"]')).to_have_count(1)
    pdf.locator('.annotation[data-item-id="claim-14"]').click()
    opened(14)
    expect(pdf.get_by_role("checkbox").first).to_be_checked()
    pdf.locator('.annotation[data-item-id="claim-14"]').click()
    opened(14)  # PDF clicks select/open; only the card header toggles closed.
    header = pdf.get_by_role("button", name="Claim 14 · 직접 지적", exact=True)
    header.focus()
    header.press("Enter")
    closed()
    header.press("Space")
    opened(14)
    page.screenshot(path=str(ROOT / "data/outputs/review-accordion-claim14.png"), full_page=True)
    pdf.get_by_role("combobox", name="거절 사유 필터").select_option("R1")
    pdf.get_by_role("button", name="종속 영향 / Objection 4", exact=True).click()
    closed()
    expect(pdf.locator(".review-card.active")).to_have_count(0)
    pdf.get_by_role("combobox", name="거절 사유 필터").select_option("all")
    # List filtering preserves the existing selection/expansion.
    opened(14)
    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    expect(page.locator(".claim-summary")).to_have_count(19)
    page.get_by_test_id("stSidebar").get_by_text("PDF 검토", exact=True).click()
    expect(pdf.locator("#page-image")).to_be_visible(timeout=30000)
    closed()
    expect(pdf.locator(".review-card.active")).to_have_count(0)
    expect(pdf.locator(".annotation.selected")).to_have_count(0)
    assert pdf.locator("#overlays").evaluate(
        "() => state.selected === null && state.expanded === null"
    )
    # The map remains usable without a selected item, and returning stays collapsed.
    pdf.get_by_role("button", name="전체 관계 지도 보기", exact=True).click()
    expect(page.get_by_role("heading", name="관계 지도", exact=True)).to_be_visible(timeout=15000)
    page.get_by_test_id("stSidebar").get_by_text("PDF 검토", exact=True).click()
    expect(pdf.locator("#page-image")).to_be_visible(timeout=30000)
    closed()
    assert pdf.locator("#overlays").evaluate("() => JSON.stringify(model)") == original
    # Restore an explicit selection for the other browser flows.
    pdf.get_by_role("combobox", name="거절 사유 필터").select_option("all")
    click(1)
    opened(1)
    print(
        "Accordion passed: initially collapsed, only 7 then 14 open, re-click collapse, PDF/keyboard selection, checklist retained, filters and reentry collapsed, no-selection map navigation, unchanged model."
    )
