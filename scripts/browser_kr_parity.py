"""Actual shared-app Korean PDF/reference navigation and scope checks."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/kr_parity/browser"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    truth = json.loads(
        (ROOT / "data/fixtures/korean/1020190000874.json").read_text(encoding="utf8")
    )
    pat = next(ROOT / f["path"] for f in truth["files"] if f["role"] == "patent")
    oa = next(
        ROOT / f["path"]
        for f in truth["files"]
        if f["role"] == "office_action" and f["path"].endswith(".pdf")
    )
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_text("한국 특허", exact=True).click()
        expect(page.get_by_text("의견제출통지서 XML / PDF", exact=True)).to_be_visible()
        for index, path in enumerate([pat, oa]):
            page.locator("input[type=file]").nth(index).set_input_files(path)
            expect(
                page.get_by_role("button", name="Remove " + path.name, exact=True)
            ).to_be_visible()
        page.get_by_text("인용발명 원문 (선택)", exact=True).click()
        page.locator("input[type=file]").nth(2).set_input_files(
            list((ROOT / "data/fixtures/korean/references").glob("KR*.pdf"))
        )
        page.get_by_role("button", name="분석 시작", exact=True).click()
        pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(pdf.locator("#page-image")).to_be_visible(timeout=90000)
        expect(pdf.locator("#summary strong")).to_have_text(["9", "0", "0", "2"])
        assert pdf.locator("#workspace").evaluate("() => model.documents.length") == 4
        pdf.locator("#scope").select_option("R1")
        expect(pdf.locator("#summary strong")).to_have_text(["3", "0", "0", "0"])
        pdf.locator('#point-filters button[data-filter="dependency"]').click()
        expect(pdf.locator("#summary strong")).to_have_text(["3", "0", "0", "0"])
        pdf.locator("#scope").select_option("R2")
        pdf.locator('#point-filters button[data-filter="all"]').click()
        pdf.get_by_role("button", name="청구항 7 · 직접 지적", exact=True).click()
        original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
        pdf.locator("#rejection-links button").last.click()
        expect(pdf.locator("#page-image")).to_be_visible()
        expect(pdf.locator('.review-card.expanded[data-review-id="claim-7"]')).to_have_count(1)
        pdf.locator('#point-filters button[data-filter="citation"]').click()
        expect(pdf.locator(".review-card")).to_have_count(2)
        pdf.locator(".review-card").first.locator(".card-select").click()
        pdf.get_by_role("button", name="인용발명 PDF 보기", exact=True).click()
        expect(pdf.locator("#document")).to_have_value(
            pdf.locator("#workspace").evaluate(
                "() => model.items.find(i=>i.id==='citation-C1').reference.source_document_id"
            )
        )
        expect(pdf.locator("#page-image")).to_be_visible(timeout=30000)
        expect(pdf.locator("#summary strong")).to_have_text(["9", "0", "0", "2"])
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        page.screenshot(path=str(OUT / "reference-navigation.png"), full_page=True)
        sidebar = page.get_by_test_id("stSidebar")
        for title in ["청구항 분석", "관계 지도", "근거 비교"]:
            sidebar.get_by_text(title, exact=True).click()
            expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()
            expect(page.get_by_test_id("stException")).to_have_count(0)
            if title == "근거 비교":
                page.locator(".st-key-comparison-citations details").first.locator(
                    "summary"
                ).first.click()
                expect(page.locator(".st-key-comparison-citations")).to_contain_text(
                    "시스템 검색 후보"
                )
            page.screenshot(path=str(OUT / (title + ".png")), full_page=True)
        # Opposite direction within this same session; old per-case state must disappear.
        for country in ["미국 특허", "한국 특허"]:
            sidebar.get_by_text("문서 업로드", exact=True).click()
            page.get_by_text(country, exact=True).click()
            page.get_by_role("button", name="예제 분석 · 가상 문서", exact=True).click()
            expect(pdf.locator("#scope")).to_have_value("all", timeout=30000)
            expect(pdf.locator(".revision-result")).to_have_count(0)
            assert (
                pdf.locator("#workspace").evaluate("() => Object.keys(revisionResults).length") == 0
            )
        assert not errors, errors
        (OUT / "checks.json").write_text(
            json.dumps(
                {
                    "result": "PASS",
                    "case": "1020190000874",
                    "checks": [
                        "OA PDF upload",
                        "reference PDFs",
                        "scope-summary",
                        "point-filter isolation",
                        "Claim7 retained on OA jump",
                        "reference PDF source",
                        "citation dedupe",
                        "four screens",
                        "KR-US-KR reset",
                    ],
                    "real_llm": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf8",
        )
        browser.close()
        print("PASS Korean shared-app PDF/reference workflow")


if __name__ == "__main__":
    main()
