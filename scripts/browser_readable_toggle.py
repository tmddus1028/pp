"""Check shared source previews, hidden accordions, spacing and responsive controls."""

from pathlib import Path

from browser_evidence_comparison import upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_short_and_long(panel, toggle):
    text = panel.locator(".readable-text-content")
    original = text.text_content()
    short = "A method according to claim 1."
    long = short * 160
    text.evaluate("(node, value) => node.textContent = value", short)
    expect(toggle).to_be_hidden()
    text.evaluate("(node, value) => node.textContent = value", long)
    expect(toggle).to_be_visible()
    control = (
        toggle.locator("summary") if toggle.evaluate("n => n.tagName") == "DETAILS" else toggle
    )
    control.click()
    assert text.evaluate("n => n.clientHeight >= n.scrollHeight - 1")
    # A fully visible short source must not retain 'Less' from the expanded state.
    text.evaluate("(node, value) => node.textContent = value", short)
    expect(toggle).to_be_hidden()
    assert text.text_content() == short
    text.evaluate("(node, value) => node.textContent = value", original)


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
        page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
        row = page.locator(".st-key-claim-row-1")
        row.get_by_text("Claim 1 상세 보기", exact=True).click()
        claim_source = row.locator(".readable-panel").first
        claim_toggle = claim_source.locator(".readable-toggle")
        expect(claim_toggle).to_be_hidden()
        check_short_and_long(claim_source, claim_toggle)
        # Opening another previously invisible accordion also triggers measurement.
        row2 = page.locator(".st-key-claim-row-2")
        row2.get_by_text("Claim 2 상세 보기", exact=True).click()
        expect(row2.locator(".readable-panel").first.locator(".readable-toggle")).to_be_hidden()

        page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
        graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
        graph.locator("#claim-picker").select_option("CL1")
        model_before = graph.locator("#map").evaluate("() => JSON.stringify(model)")
        map_source = graph.locator("#map-detail .source-card").first
        map_toggle = map_source.locator(".source-toggle")
        expect(map_source).to_be_visible()
        check_short_and_long(map_source, map_toggle)
        assert graph.locator("#map").evaluate("() => JSON.stringify(model)") == model_before
        assert not errors, errors
        browser.close()
        print(
            "PASS: Claim Analysis, Comparison and Map hide redundant toggles; "
            "long text expands/collapses; hidden accordions and resize update; no overlap."
        )


if __name__ == "__main__":
    main()
