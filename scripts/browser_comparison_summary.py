"""Actual 17/708,932 summary layout; --baseline records pre-fix computed widths."""

import json
import sys
from pathlib import Path

from browser_evidence_comparison import choose, upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = (
    "Claims 1-4, 6, 8, 17-19 are rejected under 35 U.S.C. 103 "
    "as being unpatentable over Liu et al. in view of Donmez et al."
)


def widths(node):
    return node.evaluate("""node => {
        const chain=[];
        for(let n=node;n&&chain.length<7;n=n.parentElement){
            const s=getComputedStyle(n);
            const rules=[];
            for(const sheet of document.styleSheets){
                try{for(const r of sheet.cssRules){
                    if(r.selectorText&&n.matches(r.selectorText)&&r.style.width)
                        rules.push(r.cssText);
                }}catch(_error){}
            }
            chain.push({tag:n.tagName, test:n.dataset.testid, cls:n.className,
                width:n.getBoundingClientRect().width, cssWidth:s.width,
                display:s.display, flex:s.flex, minWidth:s.minWidth, maxWidth:s.maxWidth,
                whiteSpace:s.whiteSpace, wordBreak:s.wordBreak, overflowWrap:s.overflowWrap,
                position:s.position, float:s.cssFloat, grid:s.gridTemplateColumns, widthRules:rules});
        }
        return chain;
    }""")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1450, "height": 1000})
    pdf = upload(
        page,
        ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf",
        ROOT / "tests/fixtures/oa_status/pp_vd3.pdf",
    )
    original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
    page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
    choose(page, "비교할 Claim", "Claim 1")
    choose(page, "비교할 지적 사유", "R1 · 35 U.S.C. 103")
    summary = page.locator(".st-key-comparison-summary")
    expect(summary).to_be_visible()
    if "--baseline" in sys.argv:
        nodes = summary.locator('[data-testid="stText"] > span')
        print(json.dumps([widths(n) for n in nodes.all()], ensure_ascii=False, indent=2))
        summary.screenshot(path=str(ROOT / "data/outputs/comparison-summary-before.png"))
    else:
        ground = summary.locator('.comparison-summary-ground[data-rejection="R1"]')
        expect(ground.locator(".comparison-summary-chip")).to_have_text(
            ["1", "2", "3", "4", "6", "8", "17", "18", "19"]
        )
        expect(ground.locator(".comparison-summary-reference")).to_have_text(
            ["Liu et al", "Donmez et al"]
        )
        rejection = next(r for r in json.loads(original)["rejections"] if r["rejection_id"] == "R1")
        text = ground.locator(":scope > .comparison-summary-text")
        expect(text).to_have_text(rejection["reason_summary"])
        ground.locator("summary").click()
        raw = ground.locator("details .comparison-summary-text")
        expect(raw).to_have_text(rejection["evidence"]["text"])
        measurements = []
        for width in [1450, 900, 640, 390]:
            page.set_viewport_size({"width": width, "height": 1000})
            text.scroll_into_view_if_needed()
            expect(text).to_have_css("white-space", "normal")
            expect(text).to_have_css("word-break", "normal")
            expect(text).to_have_css("overflow-wrap", "break-word")
            expect(text).to_have_css("font-size", "12px")
            sizes = text.evaluate(
                """(node, sentence) => {
                const ground=node.parentElement, box=node.getBoundingClientRect();
                const probe=node.cloneNode(false);probe.textContent=sentence;
                // Exercise the same styles using the requested regression sentence,
                // without changing the application model or original evidence.
                ground.append(probe);
                const range=document.createRange();range.selectNodeContents(probe);
                const lines=new Set([...range.getClientRects()].map(r=>Math.round(r.y))).size;
                probe.remove();
                return {width:box.width, parent:ground.getBoundingClientRect().width,
                    card:ground.closest('.st-key-comparison-summary').getBoundingClientRect().width,
                    scroll:node.scrollWidth, client:node.clientWidth, sentenceLines:lines};
            }""",
                SENTENCE,
            )
            assert sizes["width"] >= 0.95 * sizes["parent"], sizes
            assert sizes["width"] >= 0.8 * sizes["card"], sizes
            assert sizes["width"] > 200, sizes
            assert sizes["scroll"] <= sizes["client"] + 1, sizes
            assert sizes["sentenceLines"] <= (3 if width == 1450 else 7), sizes
            assert raw.evaluate("n => n.scrollWidth <= n.clientWidth + 1")
            measurements.append({"viewport": width, **sizes})
            if width in (1450, 390):
                ground.locator("summary").click()
                summary.screenshot(path=str(ROOT / f"data/outputs/comparison-summary-{width}.png"))
                ground.locator("summary").click()
        page.set_viewport_size({"width": 1450, "height": 1000})
        page.get_by_role("button", name="Office Action에서 보기", exact=True).click()
        expect(pdf.locator("#document")).to_have_value(rejection["evidence"]["document_id"])
        expect(pdf.locator("#page-number")).to_have_value(
            str(rejection["evidence"]["page_numbers"][0])
        )
        expect(
            pdf.locator('.annotation.selected[data-item-id="rejection-R1"]').first
        ).to_be_visible(timeout=15000)
        page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
        expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 1")
        page.get_by_role("button", name="PDF에서 보기", exact=True).click()
        expect(pdf.locator('.annotation.selected[data-item-id="claim-1"]').first).to_be_visible(
            timeout=15000
        )
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        print(json.dumps(measurements, ensure_ascii=False))
        print(
            "PASS: full-width natural wrapping, Claims/Liu/Donmez, original text, OA/Claim PDF links, unchanged model."
        )
    browser.close()
