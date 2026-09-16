"""Actual OA map detail presentation regression; --baseline reports old styles."""

import json
import sys
from pathlib import Path

from browser_evidence_comparison import upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    pdf = upload(
        page,
        ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf",
        ROOT / "tests/fixtures/oa_status/pp_vd3.pdf",
    )
    page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
    graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
    graph.locator("#claim-picker").select_option("CL7")
    expect(graph.locator(".detail-title")).to_have_text("Claim 7")
    original = graph.locator("#map-workspace").evaluate("() => JSON.stringify(model)")
    baseline = graph.locator("#map-detail").evaluate("""() => ({
        claim7: itemFor(nodeById('CL7')).rejection_ids,
        details: document.getElementById('map-detail').innerText,
        panelWidth: document.getElementById('map-detail').getBoundingClientRect().width,
        sources:[...document.querySelectorAll('#map-detail .source')].map(n=>({
            width:n.getBoundingClientRect().width,whiteSpace:getComputedStyle(n).whiteSpace,
            wrap:getComputedStyle(n).overflowWrap,overflow:getComputedStyle(n).overflowY
        }))
    })""")
    if "--baseline" in sys.argv:
        print(baseline)
    else:
        assert set(baseline["claim7"]) == {"R1", "R3"}
        detail = graph.locator("#map-detail")
        for name in ["Liu et al", "Donmez et al", "Huang et al"]:
            expect(detail.get_by_role("button", name=name, exact=True)).to_have_count(1)
        expect(detail).to_contain_text("관련 인용문헌 · 3개")
        expect(detail.locator(".rejection-source[open]")).to_have_count(0)
        before_state = graph.locator("#map").evaluate("() => JSON.stringify(state)")
        before_svg = graph.locator("#map").inner_html()
        originals = {r["rejection_id"]: r for r in json.loads(original)["rejections"]}
        measurements = []
        for viewport in [1440, 1920, 900, 390]:
            page.set_viewport_size({"width": viewport, "height": 1000})
            for rid in ["R1", "R3"]:
                entry = detail.locator(f'.rejection-source[data-rejection-id="{rid}"]')
                entry.locator("summary").click()
                source = entry.locator(".source")
                expect(source).to_have_text(originals[rid]["evidence"]["text"])
                assert source.text_content() == originals[rid]["evidence"]["text"]
                expect(source).to_have_css("white-space", "normal")
                expect(source).to_have_css("word-break", "normal")
                expect(source).to_have_css("overflow-wrap", "break-word")
                measure = source.evaluate("""n => ({
                    width:n.getBoundingClientRect().width,
                    panel:document.getElementById('map-detail').getBoundingClientRect().width,
                    graph:document.querySelector('.map-panel').getBoundingClientRect().width,
                    height:n.getBoundingClientRect().height,
                    line:parseFloat(getComputedStyle(n).lineHeight),
                    overflow:n.scrollWidth>n.clientWidth+1
                })""")
                assert measure["width"] >= measure["panel"] - 36, measure
                assert measure["width"] > 230 and not measure["overflow"], measure
                assert measure["height"] <= measure["line"] * 5 + 25, measure
                if viewport >= 1440:
                    assert measure["panel"] == 380 and measure["graph"] >= 660, measure
                toggle = entry.get_by_role("button", name="원문 더 보기", exact=True)
                toggle.click()
                expect(source).to_have_css("overflow-y", "visible")
                expect(source).to_have_css("max-height", "none")
                expect(source).to_have_text(originals[rid]["evidence"]["text"])
                entry.get_by_role("button", name="접기", exact=True).click()
                entry.locator("summary").click()
                measurements.append({"viewport": viewport, "rejection": rid, **measure})
            assert graph.locator("#map").evaluate("() => JSON.stringify(state)") == before_state
            assert graph.locator("#map").inner_html() == before_svg
            expect(graph.locator("#claim-picker")).to_have_value("CL7")
            if viewport in [1440, 390]:
                for rid in ["R1", "R3"]:
                    detail.locator(f'.rejection-source[data-rejection-id="{rid}"] summary').click()
                detail.evaluate("n => {n.scrollTop=0}")
                page.screenshot(
                    path=str(ROOT / f"data/outputs/map-detail-{viewport}.png"), full_page=True
                )
                for rid in ["R1", "R3"]:
                    detail.locator(f'.rejection-source[data-rejection-id="{rid}"] summary').click()
        page.set_viewport_size({"width": 1440, "height": 1000})
        detail.get_by_role("button", name="PDF에서 보기", exact=True).click()
        expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-7")
        expect(pdf.locator('.annotation.selected[data-item-id="claim-7"]').first).to_be_visible(
            timeout=15000
        )
        for rid in ["R1", "R3"]:
            page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
            graph.locator(f'.node[data-node-id="{rid}"]').click()
            detail.get_by_role("button", name="Office Action 근거 보기", exact=True).click()
            expect(pdf.locator("#page-number")).to_have_value(
                str(originals[rid]["evidence"]["page_numbers"][0])
            )
            expect(
                pdf.locator(f'.annotation.selected[data-item-id="rejection-{rid}"]').first
            ).to_be_visible(timeout=15000)
            expect(pdf.locator(".review-card.expanded")).to_have_attribute(
                "data-review-id", "claim-7"
            )
        page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
        graph.locator("#claim-picker").select_option("CL7")
        detail.get_by_role("button", name="Huang et al", exact=True).click()
        expect(detail.locator(".detail-title")).to_have_text("Huang et al")
        expect(detail.locator(".detail-text").first).to_have_css("white-space", "normal")
        assert graph.locator("#map-workspace").evaluate("() => JSON.stringify(model)") == original
        print(json.dumps(measurements))
        print(
            "PASS: Claim 7/R1/R3 + Liu/Donmez/Huang; full-width preview/expand; unchanged graph/state/evidence; Claim/OA PDF navigation."
        )
    browser.close()
