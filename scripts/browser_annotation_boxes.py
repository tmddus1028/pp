"""Check source text boxes, source fidelity and existing PDF annotation geometry."""

import json
from pathlib import Path

import browser_jurisdiction
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/annotation_boxes"


def check_text_boxes(frame):
    return frame.locator("#text-page").evaluate(
        """root => {
        if (root.textContent !== currentPage.text) throw Error('Source text changed');
        const boxes = [...root.querySelectorAll('.text-highlight')].map(n => {
          const s = getComputedStyle(n), r = n.getBoundingClientRect();
          if (s.backgroundColor !== 'rgba(0, 0, 0, 0)') throw Error('Marker fill');
          if (s.borderTopStyle !== 'solid' || parseFloat(s.borderTopWidth) < 2)
            throw Error('Missing box border');
          if (n.getClientRects().length !== 1) throw Error('Fragmented inline strips');
          if (r.width < root.clientWidth - 66) throw Error('Collapsed text box');
          if (n.scrollWidth > n.clientWidth + 1) throw Error('Text overflow');
          return {id:n.dataset.itemId, role:role(itemById(n.dataset.itemId)),
                  color:s.borderTopColor, width:r.width, height:r.height};
        });
        if (!boxes.length) throw Error('No source annotations tested');
        return boxes;
        }"""
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_role("button", name="예제 분석 · 가상 문서", exact=True).click()
        frame = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(frame.locator("#text-page")).to_be_visible(timeout=60000)
        original = frame.locator("#workspace").evaluate("() => JSON.stringify(model)")
        for width in [1920, 1440, 1280, 1024]:
            page.set_viewport_size({"width": width, "height": 1000})
            page.wait_for_timeout(400)
            boxes = check_text_boxes(frame)
            colors = {box["role"]: box["color"] for box in boxes}
            assert len({colors[r] for r in ["direct_rejection", "dependency", "canceled"]}) == 3
            checks.append({"source": "us-text", "width": width, "boxes": boxes})
            page.screenshot(path=str(OUT / f"text-{width}.png"), full_page=True)

        # Both existing input handlers must still select the same source and card.
        for claim, action in [(4, "click"), (1, "Enter"), (9, " ")]:
            target = frame.locator(f'#text-page [data-item-id="claim-{claim}"]')
            if action == "click":
                target.click()
            else:
                target.press(action)
            expect(frame.locator(".review-card.active")).to_have_attribute(
                "data-review-id", f"claim-{claim}"
            )
            expect(
                frame.locator(f'#text-page .selected[data-item-id="claim-{claim}"]')
            ).to_have_count(1)
            check_text_boxes(frame)
        assert frame.locator("#workspace").evaluate("() => JSON.stringify(model)") == original

        page.set_viewport_size({"width": 1440, "height": 1000})
        browser_jurisdiction.OUT = OUT
        browser_jurisdiction.check_korean(page)

        # Return to the real KR pair for PDF and XML appearance checks at each width.
        page.get_by_test_id("stSidebar").get_by_text("문서 업로드", exact=True).click()
        page.get_by_text("한국 특허", exact=True).click()
        expect(page.get_by_text("의견제출통지서 XML / PDF", exact=True)).to_be_visible()
        data = ROOT / "korean_prototype/data/kr_1020190000844"
        files = page.locator('input[type="file"]')
        files.nth(0).set_input_files(data / "KR20190025857A.pdf")
        expect(
            page.get_by_role("button", name="Remove KR20190025857A.pdf", exact=True)
        ).to_be_visible()
        files.nth(1).set_input_files(data / "office_action_20190409.xml")
        expect(
            page.get_by_role("button", name="Remove office_action_20190409.xml", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="분석 시작", exact=True).click()
        expect(frame.locator("#page-image")).to_be_visible(timeout=60000)
        frame.get_by_role("button", name="청구항 1 · 직접 지적", exact=True).click()
        source_model = frame.locator("#workspace").evaluate("() => JSON.stringify(model)")
        for width in [1920, 1440, 1280, 1024]:
            page.set_viewport_size({"width": width, "height": 1000})
            if frame.locator("#text-page").is_visible():
                frame.get_by_role("button", name="청구항 원문 보기", exact=True).click()
            expect(frame.locator("#page-image")).to_be_visible()
            page.wait_for_timeout(400)
            regions = frame.locator(".annotation.region").evaluate_all(
                """ns => ns.map(n => {
                const s=getComputedStyle(n), box=JSON.parse(n.dataset.box);
                if(s.position!=='absolute'||s.borderTopStyle!=='solid'||parseFloat(s.borderTopWidth)<2)
                  throw Error('PDF region border lost');
                const source=annotations().filter(a=>a.item_id===n.dataset.itemId).flatMap(a=>a.boxes);
                if(!source.length) throw Error('Source boxes missing');
                if(!source.some(b=>b[0]>=box[0]&&b[1]>=box[1]&&b[2]<=box[2]&&b[3]<=box[3]))
                  throw Error('PDF region left source coordinates');
                return {item:n.dataset.itemId,box,border:s.borderTopWidth};
                })"""
            )
            assert regions
            page.screenshot(path=str(OUT / f"kr-pdf-{width}.png"), full_page=True)
            frame.locator("#rejection-links button").click()
            expect(frame.locator("#text-page")).to_be_visible()
            checks.append(
                {
                    "source": "kr-pdf-and-xml",
                    "width": width,
                    "pdf_regions": regions,
                    "xml_boxes": check_text_boxes(frame),
                }
            )
            expect(frame.locator(".review-card.active")).to_have_attribute(
                "data-review-id", "claim-1"
            )
            page.screenshot(path=str(OUT / f"kr-xml-{width}.png"), full_page=True)
        assert frame.locator("#workspace").evaluate("() => JSON.stringify(model)") == source_model
        assert not errors, errors
        browser.close()
    (OUT / "checks.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "PASS: 4 viewports, US text boxes, real KR PDF/XML, mouse/keyboard selection, source/model fidelity, US/KR navigation."
    )


if __name__ == "__main__":
    main()
