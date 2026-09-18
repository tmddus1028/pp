"""Visual and responsive checks; no changed functional test expectations."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/visual_reskin"
WIDTHS = [1920, 1440, 1280, 1024]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        for country, short in [("미국 특허", "us"), ("한국 특허", "kr")]:
            page.get_by_text(country, exact=True).click()
            expect(page.get_by_role("radio", name=country, exact=True)).to_be_checked()
            label = "의견제출통지서 XML / PDF" if short == "kr" else "Office Action PDF"
            expect(page.get_by_text(label, exact=True)).to_be_visible()
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 1000})
                page.wait_for_timeout(250)
                cards = page.locator(".st-key-upload-card-patent,.st-key-upload-card-oa")
                expect(cards).to_have_count(2)
                boxes = cards.evaluate_all(
                    "ns=>ns.map(n=>({x:n.getBoundingClientRect().x,"
                    "right:n.getBoundingClientRect().right,width:n.clientWidth,scroll:n.scrollWidth}))"
                )
                assert all(
                    x["width"] > 280 and x["right"] <= width and x["scroll"] <= x["width"] + 1
                    for x in boxes
                ), boxes
                sidebar = page.get_by_test_id("stSidebar")
                # Streamlit's original 8px resize handle extends outside the
                # sidebar by design; inspect its content, not that hit target.
                assert page.get_by_test_id("stSidebarUserContent").evaluate(
                    "n=>n.scrollWidth<=n.clientWidth+1"
                )
                assert (
                    page.locator(".brand-name").evaluate("n=>n.getBoundingClientRect().right")
                    <= sidebar.bounding_box()["width"]
                )
                assert (
                    page.locator(".patent-hero-art").evaluate(
                        "n=>getComputedStyle(n).pointerEvents"
                    )
                    == "none"
                )
                expect(page.get_by_test_id("stException")).to_have_count(0)
                page.screenshot(path=str(OUT / f"upload-{short}-{width}.png"), full_page=True)
                checks.append(
                    {"screen": "upload", "jurisdiction": short, "width": width, "cards": boxes}
                )
            # Native text/file controls and optional reference accordion still work.
            if short == "kr":
                page.get_by_text("인용발명 원문 (선택)", exact=True).click()
                expect(page.get_by_text("인용발명 PDF", exact=True)).to_be_visible()
                page.get_by_text("인용발명 원문 (선택)", exact=True).click()
            page.get_by_text("텍스트 입력", exact=True).click()
            expect(page.get_by_role("radio", name="텍스트 입력", exact=True)).to_be_checked()
            expect(page.locator("textarea")).to_have_count(2)
            page.get_by_text("파일 업로드", exact=True).click()
            expect(page.get_by_role("radio", name="파일 업로드", exact=True)).to_be_checked()
            expect(page.get_by_text(label, exact=True)).to_be_visible()

        page.get_by_text("미국 특허", exact=True).click()
        page.get_by_role("button", name="예제 분석 · 가상 문서", exact=True).click()
        pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(pdf.locator("#summary strong")).to_have_text(["5", "3", "0", "3"], timeout=60000)
        original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
        pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
        for screen in ["PDF 검토", "청구항 분석", "관계 지도", "근거 비교"]:
            page.get_by_test_id("stSidebar").get_by_text(screen, exact=True).click()
            expect(page.get_by_role("heading", name=screen, exact=True)).to_be_visible()
            for width in WIDTHS:
                page.set_viewport_size({"width": width, "height": 1000})
                page.wait_for_timeout(250)
                expect(page.get_by_test_id("stException")).to_have_count(0)
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                page.get_by_test_id("stMain").evaluate("n => n.scrollTop = 0")
                page.screenshot(path=str(OUT / f"{screen}-{width}.png"), full_page=True)
                checks.append({"screen": screen, "width": width, "horizontal_overflow": False})
        page.get_by_test_id("stSidebar").get_by_text("PDF 검토", exact=True).click()
        expect(pdf.locator("#summary strong")).to_have_text(["5", "3", "0", "3"])
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        assert (
            pdf.locator("#workspace").evaluate(
                "n => getComputedStyle(n).getPropertyValue('--ivory').trim()"
            )
            == "#faf8f3"
        )
        page.get_by_test_id("stSidebar").get_by_role("button", name="⚙  설정", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        page.get_by_test_id("stSidebar").get_by_role("button", name="?  도움말", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        assert not errors, errors
        (OUT / "browser.json").write_text(
            json.dumps({"result": "PASS", "checks": checks}, ensure_ascii=False, indent=2),
            encoding="utf8",
        )
        browser.close()
        print(
            "PASS: 24 responsive captures; US/KR, native widgets, four screens, immutable model, dialogs."
        )


if __name__ == "__main__":
    main()
