"""Review-scope summary regression: public patent + reconstructed 14/623,904 OA.

uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_review_scope.py
Requires the local API and Streamlit servers.
"""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_summary(pdf, direct, dependency):
    expect(pdf.locator("#summary .direct_rejection strong")).to_have_text(str(direct))
    expect(pdf.locator("#summary .dependency strong")).to_have_text(str(dependency))


def check_claims(pdf, numbers):
    cards = pdf.locator(".review-card")
    expect(cards).to_have_count(len(numbers))
    assert cards.evaluate_all("nodes => nodes.map(n => n.dataset.reviewId)") == [
        f"claim-{n}" for n in numbers
    ]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        uploads = page.locator('input[type="file"]')
        uploads.nth(0).set_input_files(ROOT / "data/raw/us20150283132a1/US20150283132A1.pdf")
        uploads.nth(1).set_input_files(
            ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf"
        )
        page.get_by_role("button", name="분석 시작", exact=True).click()
        pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(pdf.locator("#page-image")).to_be_visible(timeout=240000)
        original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
        scope = pdf.get_by_role("combobox", name="거절 사유 필터")
        check_summary(pdf, 19, 0)
        scope.select_option("R1")
        check_summary(pdf, 15, 4)
        for kind in ["direct_rejection", "citation", "all", "dependency"]:
            pdf.locator(f'#point-filters [data-filter="{kind}"]').click()
            check_summary(pdf, 15, 4)
        check_claims(pdf, [2, 5, 8, 11])
        pdf.locator('[data-review-id="claim-2"] .card-select').click()
        check_summary(pdf, 15, 4)
        expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-2")
        # Evidence navigation changes the PDF focus, not the summary's review scope.
        pdf.locator("#rejection-links button").filter(has_text="R2").click()
        expect(scope).to_have_value("R1")
        check_summary(pdf, 15, 4)
        check_claims(pdf, [2, 5, 8, 11])
        expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-2")
        scope.select_option("R2")
        check_summary(pdf, 19, 0)
        pdf.locator('#point-filters [data-filter="dependency"]').click()
        check_summary(pdf, 19, 0)
        check_claims(pdf, [])
        scope.select_option("all")
        check_summary(pdf, 19, 0)
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        assert not errors, errors
        browser.close()
        print(
            "PASS: ALL 19/0, R1 15/4 (2,5,8,11), R2 19/0; filters, selection, evidence isolation."
        )


if __name__ == "__main__":
    main()
