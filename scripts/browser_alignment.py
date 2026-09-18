"""Measure shared visual alignment without changing app state/event contracts."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

OUT = Path(__file__).resolve().parents[1] / "data/outputs/alignment"
VIEWPORTS = [(1920, 1080), (1440, 900), (1280, 800), (1024, 768)]
RECTS = "ns=>ns.map(n=>n.getBoundingClientRect().toJSON())"
BASELINES = """ns=>ns.map(n=>{
 const marker=document.createElement('span');
 marker.style.cssText='display:inline-block;width:0;height:0;vertical-align:baseline';
 n.append(marker);const y=marker.getBoundingClientRect().y;marker.remove();return y;
})"""


def matched(values, name):
    assert len(values) == 2 and abs(values[0] - values[1]) <= 1, (name, values)
    return {"result": "PASS", "values": values}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        for country, code in [("미국 특허", "us"), ("한국 특허", "kr")]:
            page.get_by_text(country, exact=True).click()
            label = "의견제출통지서 XML / PDF" if code == "kr" else "Office Action PDF"
            expect(page.get_by_text(label, exact=True)).to_be_visible()
            for width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(300)
                checks = {}
                for name, selector, property in [
                    ("number_top", ".patent-step", "top"),
                    ("icon_center", ".upload-icon-slot", "y"),
                    ("divider", ".patent-upload-heading", "bottom"),
                    ("card_top", ".st-key-upload-card-patent,.st-key-upload-card-oa", "top"),
                    ("card_bottom", ".st-key-upload-card-patent,.st-key-upload-card-oa", "bottom"),
                    ("upload_top", '[data-testid="stFileUploaderDropzone"]:visible', "top"),
                    ("upload_height", '[data-testid="stFileUploaderDropzone"]:visible', "height"),
                    (
                        "upload_button",
                        '[data-testid="stFileUploaderDropzone"]:visible button',
                        "top",
                    ),
                    (
                        "upload_helper",
                        '[data-testid="stFileUploaderDropzoneInstructions"]:visible',
                        "top",
                    ),
                    ("action_buttons", ".st-key-analyze button,.st-key-demo button", "top"),
                    ("radio_row", '.st-key-upload-options [role="radiogroup"]', "top"),
                ]:
                    checks[name] = matched(
                        [r[property] for r in page.locator(selector).evaluate_all(RECTS)], name
                    )
                for name, selector in [
                    ("title_baseline", ".upload-card-title"),
                    ("subtitle_baseline", ".upload-card-subtitle"),
                ]:
                    checks[name] = matched(page.locator(selector).evaluate_all(BASELINES), name)
                numbers = page.locator(".patent-step").evaluate_all(BASELINES)
                titles = page.locator(".upload-card-title").evaluate_all(BASELINES)
                assert all(abs(n - t) <= 1 for n, t in zip(numbers, titles)), (numbers, titles)
                checks["number_title_baseline"] = {
                    "result": "PASS",
                    "numbers": numbers,
                    "titles": titles,
                }
                for selector in [
                    ".upload-card-title",
                    ".upload-card-subtitle",
                    ".patent-upload-heading",
                ]:
                    assert page.locator(selector).evaluate_all(
                        "ns=>ns.every(n=>n.scrollWidth<=n.clientWidth+1&&n.scrollHeight<=n.clientHeight+1)"
                    ), selector
                lefts = [
                    page.locator(s).bounding_box()["x"]
                    for s in [
                        ".st-key-upload-hero",
                        ".st-key-upload-options",
                        ".st-key-upload-card-patent",
                        ".st-key-analyze",
                    ]
                ]
                assert max(lefts) - min(lefts) <= 1, lefts
                checks["left_gutter"] = {"result": "PASS", "values": lefts}
                assert page.get_by_test_id("stSidebarUserContent").evaluate(
                    "n=>n.scrollWidth<=n.clientWidth+1"
                )
                menu_x = (
                    page.get_by_test_id("stSidebar")
                    .locator('[data-testid="stRadioOption"] p')
                    .evaluate_all("ns=>ns.map(n=>n.getBoundingClientRect().x)")
                )
                assert max(menu_x) - min(menu_x) <= 1, menu_x
                page.get_by_test_id("stMain").evaluate("n=>n.scrollTop=0")
                page.screenshot(path=str(OUT / f"upload-{code}-{width}.png"), full_page=True)
                records.append(
                    {
                        "screen": "upload",
                        "country": code,
                        "viewport": [width, height],
                        "checks": checks,
                    }
                )
            if code == "kr":
                page.get_by_text("인용발명 원문 (선택)", exact=True).click()
                expect(page.get_by_text("인용발명 PDF", exact=True)).to_be_visible()
                cards = page.locator(
                    ".st-key-upload-card-patent,.st-key-upload-card-oa"
                ).evaluate_all(RECTS)
                matched([r["bottom"] for r in cards], "expanded_card_bottom")
                page.get_by_text("인용발명 원문 (선택)", exact=True).click()

        # Verify stacked headers too, without forcing a new breakpoint.
        page.set_viewport_size({"width": 600, "height": 900})
        page.wait_for_timeout(300)
        for s in [".patent-upload-heading", ".upload-card-title"]:
            assert page.locator(s).evaluate_all("ns=>ns.every(n=>n.scrollWidth<=n.clientWidth+1)")
        page.screenshot(path=str(OUT / "upload-kr-stacked.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.get_by_text("미국 특허", exact=True).click()
        page.get_by_role("button", name="예제 분석 · 가상 문서", exact=True).click()
        pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(pdf.locator("#summary strong")).to_have_text(["5", "3", "0", "3"], timeout=60000)
        for screen in ["PDF 검토", "청구항 분석", "관계 지도", "근거 비교"]:
            page.get_by_test_id("stSidebar").get_by_text(screen, exact=True).click()
            expect(page.get_by_role("heading", name=screen, exact=True)).to_be_visible()
            for width, height in VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_timeout(300)
                expect(page.get_by_test_id("stException")).to_have_count(0)
                page.get_by_test_id("stMain").evaluate("n=>n.scrollTop=0")
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                if screen == "근거 비교":
                    headers = page.locator(".comparison-card-heading").evaluate_all(RECTS)
                    assert len(headers) == 4
                    for first, second in [headers[:2], headers[2:]]:
                        matched([first["top"], second["top"]], "comparison_header_top")
                    cards = page.locator(
                        ".st-key-comparison-claim,.st-key-comparison-oa,"
                        ".st-key-comparison-specification,.st-key-comparison-citations"
                    ).evaluate_all(RECTS)
                    for first, second in [cards[:2], cards[2:]]:
                        matched([first["bottom"], second["bottom"]], "comparison_card_bottom")
                elif screen == "청구항 분석":
                    metrics = page.get_by_test_id("stMetricValue").evaluate_all(RECTS)
                    assert len(metrics) == 5
                    assert max(r["top"] for r in metrics) - min(r["top"] for r in metrics) <= 1
                elif screen == "PDF 검토":
                    controls = pdf.locator(".toolbar button,.toolbar input").evaluate_all(RECTS)
                    centers = [r["top"] + r["height"] / 2 for r in controls]
                    assert max(centers) - min(centers) <= 1, centers
                elif screen == "관계 지도":
                    graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
                    toolbar = graph.locator(".map-toolbar").bounding_box()
                    button = graph.locator(".map-toolbar button").bounding_box()
                    assert (
                        abs(
                            (toolbar["y"] + toolbar["height"] / 2)
                            - (button["y"] + button["height"] / 2)
                        )
                        <= 1
                    )
                page.screenshot(path=str(OUT / f"{screen}-{width}.png"), full_page=True)
                records.append({"screen": screen, "viewport": [width, height], "result": "PASS"})
        (OUT / "browser.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf8"
        )
        browser.close()
    print("PASS: upload baselines, dividers, cards, gutters; 24 viewport checks + stacked header.")


if __name__ == "__main__":
    main()
