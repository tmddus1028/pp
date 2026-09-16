"""Same-session document replacement, all-page citation policy, dialogs/downloads."""

import json
from pathlib import Path

from browser_evidence_comparison import upload
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        pdf = upload(
            page,
            ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf",
            ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf",
        )
        sidebar = page.get_by_test_id("stSidebar")
        pdf.locator("#scope").select_option("R1")
        pdf.locator('#point-filters [data-filter="dependency"]').click()
        pdf.locator('[data-review-id="claim-5"] .card-select').click()
        pdf.locator("#search").fill("compound")
        pdf.locator("#search").press("Enter")
        expect(pdf.locator("#loading")).to_be_hidden(timeout=20000)
        sidebar.get_by_text("청구항 분석", exact=True).click()
        page.get_by_role("textbox", name="Claim 번호 검색").fill("14")
        page.get_by_role("textbox", name="Claim 번호 검색").press("Enter")
        sidebar.get_by_text("관계 지도", exact=True).click()
        graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
        graph.locator("#claim-picker").select_option("CL14")
        graph.locator("#scope").select_option("R2")
        sidebar.get_by_text("근거 비교", exact=True).click()
        sidebar.get_by_text("문서 업로드", exact=True).click()
        uploads = page.locator('input[type="file"]')
        uploads.nth(0).set_input_files(ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf")
        uploads.nth(1).set_input_files(ROOT / "tests/fixtures/oa_status/pp_vd3.pdf")
        page.get_by_role("button", name="분석 시작", exact=True).click()
        expect(pdf.locator("#page-image")).to_be_visible(timeout=120000)
        assert pdf.locator("#workspace").evaluate(
            """() => state.scope==='all' && state.filter==='all' && state.selected===null && state.expanded===null && state.viewer_evidence===null && state.active_rejection===null && !state.search"""
        )
        expect(pdf.locator("#summary .direct_rejection strong")).to_have_text("17")
        expect(pdf.locator("#summary .dependency strong")).to_have_text("2")
        expect(pdf.locator("#summary .citation strong")).to_have_text("7")
        original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
        with page.expect_download() as download:
            page.get_by_text("문서 처리 안내 및 분석 결과", exact=True).click()
            page.get_by_role("button", name="분석 JSON 다운로드").click()
        data = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert len(data["citations"]) == 10
        sidebar.get_by_role("button", name="⚙ 설정").click()
        expect(page.get_by_role("dialog")).to_contain_text("LOCAL")
        page.get_by_role("dialog").get_by_role("button", name="Close").click()
        sidebar.get_by_role("button", name="? 도움말").click()
        expect(page.get_by_role("dialog")).to_contain_text("종속항")
        page.get_by_role("dialog").get_by_role("button", name="Close").click()
        sidebar.get_by_text("청구항 분석", exact=True).click()
        expect(page.get_by_role("textbox", name="Claim 번호 검색")).to_have_value("")
        expect(page.locator(".claim-summary")).to_have_count(20)
        row = page.locator(".st-key-claim-row-12")
        row.locator("summary").filter(has_text="Claim 12 상세 보기").click()
        assert not any("Wei" in s for s in row.locator("summary").all_text_contents())
        sidebar.get_by_text("관계 지도", exact=True).click()
        assert graph.locator("#map").evaluate(
            "() => state.selected===null && state.scope==='all' && state.filter==='all'"
        )
        graph.locator("#claim-picker").select_option("CL12")
        hidden = [
            c["citation_id"] for c in data["citations"] if c["citation_role"] != "relied_upon"
        ]
        for cid in hidden:
            expect(graph.locator(f'.node[data-node-id="{cid}"]')).to_have_count(0)
        expect(
            graph.locator("#map-detail").get_by_role("button", name="Wei", exact=True)
        ).to_have_count(0)
        sidebar.get_by_text("근거 비교", exact=True).click()
        expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 12")
        citation_headers = page.locator(
            '.st-key-comparison-citations [data-testid="stExpander"] > details > summary'
        )
        expect(citation_headers).to_have_count(5)
        assert not any("Wei" in s for s in citation_headers.all_text_contents())
        assert "Wei" not in page.locator(".comparison-summary-reference").all_text_contents()
        sidebar.get_by_text("PDF 검토", exact=True).click()
        assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
        assert not errors, errors
        browser.close()
        print(
            "PASS: same-session new documents reset state; 17/2/0/7; all-page hidden roles; dialogs and JSON download; immutable model."
        )


if __name__ == "__main__":
    main()
