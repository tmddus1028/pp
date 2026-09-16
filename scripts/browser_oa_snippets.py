"""Actual Claim 7 examiner snippets; --baseline reports existing computed styles."""

import json
import sys
from pathlib import Path

from browser_evidence_comparison import choose, upload
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
    original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
    page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
    choose(page, "비교할 Claim", "Claim 7")
    oa = page.locator(".st-key-comparison-oa")
    expect(oa.locator(".comparison-rejection")).to_have_count(2)
    if "--baseline" in sys.argv:
        print(
            oa.locator(".comparison-source").evaluate_all("""nodes=>nodes.map(n=>({
            width:n.getBoundingClientRect().width,card:n.closest('.st-key-comparison-oa').getBoundingClientRect().width,
            whiteSpace:getComputedStyle(n).whiteSpace,wrap:getComputedStyle(n).overflowWrap,
            maxHeight:getComputedStyle(n).maxHeight,overflow:getComputedStyle(n).overflow,
            textSample:n.textContent.slice(0,180)
        }))""")
        )
    else:
        rejections = {r["rejection_id"]: r for r in json.loads(original)["rejections"]}
        assert oa.locator(".comparison-rejection").evaluate_all(
            "ns=>ns.map(n=>n.dataset.rejection)"
        ) == ["R1", "R3"]
        expect(oa.locator(".readable-toggle[open]")).to_have_count(0)
        refs = page.locator(".st-key-comparison-citations")
        expect(refs.locator("summary:not(.readable-toggle > summary)")).to_have_count(3)
        for name in ["Liu", "Donmez", "Huang"]:
            expect(
                refs.locator("summary:not(.readable-toggle > summary)").filter(has_text=name)
            ).to_have_count(1)
        other_regions = [
            "comparison-claim",
            "comparison-specification",
            "comparison-citations",
            "comparison-summary",
        ]
        other_html = {key: page.locator(".st-key-" + key).inner_html() for key in other_regions}
        measurements = []
        for width in [1440, 900, 390]:
            page.set_viewport_size({"width": width, "height": 1000})
            for index, rid in enumerate(["R1", "R3"]):
                snippet = oa.locator(".readable-panel").nth(index)
                source = snippet.locator(".comparison-source")
                assert source.text_content() == rejections[rid]["evidence"]["text"]
                expect(source).to_have_css("white-space", "normal")
                expect(source).to_have_css("overflow-wrap", "break-word")
                expect(source).to_have_css("word-break", "normal")
                expect(source).to_have_css("display", "block")
                expect(source).to_have_css("overflow-y", "visible")
                expect(source).to_have_css("max-height", "none")
                size = source.evaluate("""n => {
                    const span=n.querySelector('.readable-text-content'),text=span.firstChild;
                    const tops=[];
                    for(const m of [...text.textContent.matchAll(/\\S+/g)].slice(0,20)){
                        const range=document.createRange();range.setStart(text,m.index);range.setEnd(text,m.index+m[0].length);
                        tops.push(Math.round(range.getBoundingClientRect().top));
                    }
                    return {width:n.getBoundingClientRect().width,
                        card:n.closest('.st-key-comparison-oa').getBoundingClientRect().width,
                        height:n.getBoundingClientRect().height,line:parseFloat(getComputedStyle(n).lineHeight),
                        overflow:n.scrollWidth>n.clientWidth+1,first20WordLines:new Set(tops).size};
                }""")
                assert size["width"] > size["card"] - 36 and size["width"] > 230, size
                assert not size["overflow"] and size["first20WordLines"] <= 6, size
                assert size["height"] <= size["line"] * 5 + 27, size
                snippet.locator("summary").click()
                expect(snippet.locator(".readable-less")).to_be_visible()
                expect(snippet.locator(".readable-more")).to_be_hidden()
                assert source.text_content() == rejections[rid]["evidence"]["text"]
                assert source.evaluate("n => n.scrollHeight <= n.clientHeight+1")
                snippet.locator("summary").click()
                expect(snippet.locator(".readable-more")).to_be_visible()
                expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 7")
                measurements.append({"viewport": width, "rid": rid, **size})
            assert abs(oa.bounding_box()["width"] - refs.bounding_box()["width"]) < 2
            for key in other_regions:
                assert page.locator(".st-key-" + key).inner_html() == other_html[key]
            oa.screenshot(path=str(ROOT / f"data/outputs/examiner-snippets-{width}.png"))
        page.set_viewport_size({"width": 1440, "height": 1000})
        for rid in ["R1", "R3"]:
            choose(page, "비교할 지적 사유", rid + " · 35 U.S.C. 103")
            expect(oa.locator(".comparison-rejection")).to_have_count(1)
            expect(oa.locator(".comparison-rejection")).to_have_attribute("data-rejection", rid)
            oa.get_by_role("button", name="Office Action에서 보기", exact=True).click()
            expect(pdf.locator("#document")).to_have_value(
                rejections[rid]["evidence"]["document_id"]
            )
            expect(pdf.locator("#page-number")).to_have_value(
                str(rejections[rid]["evidence"]["page_numbers"][0])
            )
            expect(
                pdf.locator('.annotation.selected[data-item-id="rejection-' + rid + '"]').first
            ).to_be_visible(timeout=15000)
            expect(pdf.locator(".review-card.expanded")).to_have_attribute(
                "data-review-id", "claim-7"
            )
            page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
        page.get_by_role("button", name="PDF에서 보기", exact=True).click()
        expect(pdf.locator('.annotation.selected[data-item-id="claim-7"]').first).to_be_visible(
            timeout=15000
        )
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        print(json.dumps(measurements))
        print(
            "PASS: Claim 7 R1/R3 natural wrapping, five-line preview/expand, no nested scroll; untouched other cards/model and PDF links."
        )
    browser.close()
