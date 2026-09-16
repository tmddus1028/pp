"""Check actual comparison previews, spacing, and responsive overflow controls."""

from pathlib import Path

from browser_evidence_comparison import upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        fixtures = ROOT / "tests/fixtures/pdf_review"
        upload(page, fixtures / "patent.pdf", fixtures / "office_action_support.pdf")
        page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
        claim = page.locator(".st-key-comparison-claim .readable-panel:has(>.readable-toggle)")
        toggle = claim.locator(".readable-toggle")
        expect(claim).to_be_visible()
        expect(toggle).to_be_hidden()
        text = claim.locator(".readable-text-content")
        original = text.text_content()
        # Rendering-only probe: no model or analysis is changed.
        long_text = "A method according to claim 1 comprising a semiconductor layer. " * 60
        text.evaluate("(node, value) => node.textContent = value", long_text)
        expect(toggle).to_be_visible()
        toggle.locator("summary").click()
        expect(toggle).to_have_attribute("open", "")
        expect(toggle.locator(".readable-less")).to_be_visible()
        toggle.locator("summary").click()
        expect(toggle.locator(".readable-more")).to_be_visible()
        assert text.text_content() == long_text
        # A medium excerpt crosses the five-line limit only at the narrower viewport.
        medium = "A method according to claim 1 comprising a semiconductor layer. " * 7
        text.evaluate("(node, value) => node.textContent = value", medium)
        page.set_viewport_size({"width": 1920, "height": 1000})
        expect(toggle).to_be_hidden()
        page.set_viewport_size({"width": 1024, "height": 1000})
        expect(toggle).to_be_visible()
        text.evaluate("(node, value) => node.textContent = value", original)
        page.set_viewport_size({"width": 1440, "height": 1000})
        expect(toggle).to_be_hidden()
        spec = page.locator(".st-key-comparison-specification")
        panel = spec.locator(".readable-panel:has(>.readable-toggle)").first
        spec_text = panel.locator(".readable-text-content")
        spec_original = spec_text.text_content()
        spec_text.evaluate("(node, value) => node.textContent = value", long_text)
        summary = panel.locator("summary")
        expect(summary).to_be_visible()
        link = spec.get_by_role("button", name="명세서 PDF에서 보기").first
        summary.scroll_into_view_if_needed()
        assert (
            link.bounding_box()["y"]
            >= summary.bounding_box()["y"] + summary.bounding_box()["height"] + 4
        )
        spec_text.evaluate("(node, value) => node.textContent = value", spec_original)
        assert not errors, errors
        browser.close()
        print(
            "PASS: short text hides toggle; long text expands/collapses; resize updates; no overlap."
        )


if __name__ == "__main__":
    main()
