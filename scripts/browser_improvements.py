"""Explicit local review, rejection-scoped caching and existing navigation in Edge."""

import json
from pathlib import Path

from browser_evidence_comparison import upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/improvements"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        pdf = upload(
            page,
            ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf",
            ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf",
        )
        pdf.locator("#scope").select_option("R1")
        pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
        original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
        selection = pdf.locator("#workspace").evaluate("() => JSON.stringify(state)")
        expect(pdf.locator(".improvement-detail")).to_have_count(0)
        pdf.get_by_role("button", name="개선 방안 보기", exact=True).click()
        expect(pdf.locator(".improvement-detail")).to_contain_text(
            "검토용 개선 방안", timeout=30000
        )
        expect(pdf.locator(".improvement-detail")).to_contain_text("112")
        expect(pdf.locator(".improvement-detail")).to_contain_text("외부 AI 호출 없음")
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(state)") == selection
        first = pdf.locator(".improvement-detail").text_content()
        pdf.locator("#scope").select_option("R2")
        expect(pdf.locator(".improvement-detail")).to_have_count(0)
        pdf.get_by_role("button", name="개선 방안 보기", exact=True).click()
        expect(pdf.locator(".improvement-detail")).to_contain_text("103", timeout=30000)
        expect(pdf.locator(".improvement-detail")).to_contain_text("선행문헌 원문 미확보")
        assert pdf.locator(".improvement-detail").text_content() != first
        pdf.locator("#scope").select_option("R1")
        expect(pdf.locator(".improvement-detail")).to_have_text(first)
        pdf.locator(".improvement-detail").evaluate("node => node.open = true")
        pdf.locator(".improvement-detail").evaluate("node => node.scrollIntoView({block: 'start'})")
        paragraph = pdf.locator(".improvement-detail .readable-text").first
        assert paragraph.evaluate("node => node.getBoundingClientRect().width") > 250
        page.screenshot(path=str(OUT / "us-improvement.png"), full_page=True)
        sidebar = page.get_by_test_id("stSidebar")
        sidebar.get_by_text("청구항 분석", exact=True).click()
        page.get_by_text("Claim 1 상세 보기", exact=True).click()
        card = page.locator(".st-key-claim-row-1")
        card.get_by_role("button", name="개선 방안 보기", exact=True).click()
        expect(card).to_contain_text("검토용 개선 방안", timeout=30000)
        expect(card).to_contain_text("112")
        expect(card).to_contain_text("103")
        card.get_by_role("button", name="PDF에서 보기", exact=True).click()
        expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-1")
        expect(pdf.locator("#page-image")).to_be_visible()
        sidebar.get_by_text("문서 업로드", exact=True).click()
        page.get_by_text("한국 특허", exact=True).click()
        expect(page.get_by_text("의견제출통지서 XML", exact=True)).to_be_visible()
        data = ROOT / "korean_prototype/data/kr_1020190000844"
        inputs = page.locator('input[type="file"]')
        inputs.nth(0).set_input_files(data / "KR20190025857A.pdf")
        expect(
            page.get_by_role("button", name="Remove KR20190025857A.pdf", exact=True)
        ).to_be_visible()
        inputs.nth(1).set_input_files(data / "office_action_20190409.xml")
        expect(
            page.get_by_role("button", name="Remove office_action_20190409.xml", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="분석 시작", exact=True).click()
        expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
        pdf.get_by_role("button", name="청구항 1 · 직접 지적", exact=True).click()
        expect(pdf.locator(".improvement-detail")).to_have_count(0)
        pdf.get_by_role("button", name="개선 방안 보기", exact=True).click()
        expect(pdf.locator(".improvement-detail")).to_contain_text("제29조제2항", timeout=30000)
        expect(pdf.locator(".improvement-detail")).to_contain_text("명세서 근거가 없어")
        expect(pdf.locator("#summary strong")).to_have_text(["1", "0", "0", "3"])
        pdf.locator(".improvement-detail").evaluate("node => node.scrollIntoView({block: 'start'})")
        page.screenshot(path=str(OUT / "kr-improvement.png"), full_page=True)
        pdf.locator("#rejection-links button").click()
        expect(pdf.locator("#text-page")).to_contain_text("제29조제2항")
        expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-1")
        assert not errors, errors
        (OUT / "browser.json").write_text(
            json.dumps(
                {
                    "result": "PASS",
                    "external_llm": False,
                    "checks": [
                        "explicit click",
                        "R1/R2 isolation",
                        "cache reuse",
                        "data/state unchanged",
                        "Claim Analysis",
                        "PDF navigation",
                        "US/KR cache reset",
                        "KR missing evidence",
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS: explicit local generation, R1/R2 caching, US/KR isolation, unchanged analysis/navigation",
            flush=True,
        )
        browser.close()


if __name__ == "__main__":
    main()
