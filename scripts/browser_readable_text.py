"""Shared typography regression across all four pages and required viewport widths."""

import json
from pathlib import Path

from browser_evidence_comparison import upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SENTENCE = (
    "Claims 1-4, 6, 8, 17-19 are rejected under 35 U.S.C. 103 as being "
    "unpatentable over Liu et al. in view of Donmez et al."
)
MEASURE = """(nodes, sentence) => {
    for(const node of nodes)for(let p=node.parentElement;p;p=p.parentElement)
        if(p.tagName==='DETAILS')p.open=true;
    return nodes.filter(n=>n.getBoundingClientRect().width>0).map(n=>{
    const s=getComputedStyle(n), width=n.getBoundingClientRect().width;
    const parent=n.parentElement.getBoundingClientRect().width;
    const cases=[];
    for(const text of [sentence,sentence.split(' ').join('\\n')]){
        const probe=n.cloneNode(false);probe.classList.remove('preview');
        const content=document.createElement('span');content.className='readable-text-content';
        content.textContent=text;probe.append(content);n.after(probe);
        const range=document.createRange();range.selectNodeContents(content);
        const rects=[...range.getClientRects()].filter(r=>r.width>0);
        const lines=new Set(rects.map(r=>Math.round(r.top))).size;
        cases.push({lines,overflow:probe.scrollWidth>probe.clientWidth+1});probe.remove();
    }
    return {width,parent,whiteSpace:s.whiteSpace,wordBreak:s.wordBreak,wrap:s.overflowWrap,
        line:s.lineHeight,font:s.fontSize,display:s.display,cases};
});}"""


def inspect(page, region, selector, name, results):
    for viewport in [1920, 1440, 1280, 1024]:
        page.set_viewport_size({"width": viewport, "height": 1000})
        # Allow Streamlit's iframe resize messages and responsive layout to settle.
        page.wait_for_timeout(250)
        nodes = region.locator(selector)
        nodes.first.wait_for(state="attached")
        rows = nodes.evaluate_all(MEASURE, SENTENCE)
        if not rows:
            # A responsive iframe can be replaced while its source finishes rendering.
            expect(nodes.first).to_be_visible()
            rows = nodes.evaluate_all(MEASURE, SENTENCE)
        assert rows, name
        for row in rows:
            assert row["whiteSpace"] == "normal" and row["wordBreak"] == "normal", (name, row)
            assert row["wrap"] == "break-word" and row["display"] == "block", (name, row)
            assert abs(float(row["line"][:-2]) / float(row["font"][:-2]) - 1.6) < 0.01
            assert row["width"] >= row["parent"] * 0.8 and row["width"] >= 200, (name, row)
            assert all(case["lines"] <= 6 and not case["overflow"] for case in row["cases"]), (
                name,
                row,
            )
        results.append(
            {
                "screen": name,
                "viewport": viewport,
                "sources": len(rows),
                "min_width": min(r["width"] for r in rows),
                "max_lines": max(c["lines"] for r in rows for c in r["cases"]),
            }
        )


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors, results = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    pdf = upload(
        page,
        ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf",
        ROOT / "tests/fixtures/oa_status/pp_vd3.pdf",
    )
    original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
    pdf.get_by_role("button", name="Claim 7 · 직접 지적", exact=True).click()
    card = pdf.locator(".review-card.expanded")
    card.locator("details").evaluate_all("ns=>ns.forEach(n=>n.open=true)")
    inspect(page, card, ".evidence.readable-text", "PDF Review Claim/OA", results)
    pdf.get_by_role("button", name="Liu et al", exact=True).click()
    card.locator("details").evaluate_all("ns=>ns.forEach(n=>n.open=true)")
    inspect(page, card, ".evidence.readable-text", "PDF Review citation", results)
    page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
    graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
    graph.locator("#claim-picker").select_option("CL7")
    graph.locator("#map-detail details").evaluate_all("ns=>ns.forEach(n=>n.open=true)")
    graph_original = graph.locator("#map").evaluate("() => JSON.stringify(model)")
    inspect(page, graph, "#map-detail .source.readable-text", "Relationship Claim/OA", results)
    assert graph.locator("#map").evaluate("() => JSON.stringify(model)") == graph_original
    graph.locator("#map-detail").get_by_role("button", name="Huang et al", exact=True).click()
    expect(graph.locator(".detail-title")).to_have_text("Huang et al")
    inspect(
        page,
        graph,
        "#map-detail>.source-card .source.readable-text",
        "Relationship citation",
        results,
    )
    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    row = page.locator(".st-key-claim-row-7")
    row.locator("summary").filter(has_text="Claim 7 상세 보기").click()
    expect(row.locator(".claim-evidence").first).to_be_visible()
    # Streamlit accordions only: a fully visible source deliberately hides its own toggle.
    for toggle in row.locator('[data-testid="stExpander"] > details > summary').all():
        if not toggle.evaluate("n=>n.closest('details').open"):
            toggle.click()
    inspect(page, row, ".claim-evidence.readable-text", "Claim Analysis sources", results)
    assert page.locator(
        '.st-key-claim-metrics [data-testid="stMetricValue"]'
    ).all_text_contents() == ["20", "6", "17", "2", "0"]
    row.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-7")
    pdf.get_by_role("button", name="근거 비교", exact=True).click()
    expect(page.get_by_role("heading", name="근거 비교", exact=True)).to_be_visible()
    expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 7")
    comparison = page.locator(".st-key-evidence-comparison")
    expect(comparison.locator(".comparison-source").first).to_be_visible()
    comparison.locator("details").evaluate_all("ns=>ns.forEach(n=>n.open=true)")
    inspect(
        page,
        comparison,
        ".comparison-source.readable-text, .comparison-summary-text.readable-text",
        "Evidence Comparison all sources",
        results,
    )
    # Whole evidence strings, including newlines, remain identical to the model.
    model = json.loads(original)
    expected = {i["evidence"]["text"] for i in model["items"]}
    expected.update(r["evidence"]["text"] for r in model["rejections"])
    expected.update(
        ref["evidence"]["text"] for r in model["rejections"] for ref in r["cited_references"]
    )
    for source in comparison.locator(".comparison-source.readable-text").all():
        text = source.text_content()
        assert text in expected
    page.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-7")
    assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
    assert not errors, errors
    (ROOT / "data/outputs/readable-text-validation.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(json.dumps(results))
    print(
        "PASS: shared CSS across four pages at 1920/1440/1280/1024; natural wrapping of spaces and OCR newlines; data and selection unchanged."
    )
    browser.close()
