"""Text/JSON upload, empty-state navigation, and retained legacy graph smoke."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        sidebar = page.get_by_test_id("stSidebar")
        sidebar.get_by_text("PDF 검토", exact=True).click()
        expect(
            page.get_by_text("먼저 Patent와 Office Action을 업로드하여 분석을 시작하세요.")
        ).to_be_visible()
        page.get_by_role("button", name="문서 업로드로 이동").click()
        page.get_by_text("텍스트 입력", exact=True).click()
        page.get_by_role("textbox", name="01 · Patent / Claims").fill(
            "Claims\n1. A device comprising a sensor."
        )
        page.get_by_role("textbox", name="02 · Office Action").fill(
            "Claim 1 is rejected under 35 USC 112."
        )
        page.get_by_role("textbox", name="02 · Office Action").press("Tab")
        page.get_by_role("button", name="분석 시작", exact=True).click()
        pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(pdf.locator("#text-page")).to_be_visible(timeout=15000)
        expect(pdf.locator("#summary .direct_rejection strong")).to_have_text("1")
        sidebar.get_by_text("문서 업로드", exact=True).click()
        page.get_by_text("파일 업로드", exact=True).click()
        uploads = page.locator('input[type="file"]')
        for i, text in enumerate(
            [
                "Claims\n1. A sensor.\n2. The sensor of claim 1.",
                "Claim 1 is rejected under 35 USC 103 over Smith (US 2020/0123456 A1).",
            ]
        ):
            uploads.nth(i).set_input_files(
                {
                    "name": f"document{i}.json",
                    "mimeType": "application/json",
                    "buffer": json.dumps({"pages": [{"text": text}]}).encode(),
                }
            )
        page.get_by_role("button", name="분석 시작", exact=True).click()
        expect(pdf.locator("#summary .dependency strong")).to_have_text("1", timeout=15000)
        # Legacy component is not routed in the main app, but remains callable.
        graph = json.loads(
            (ROOT / "data/outputs/audit-20260916/final-golden/pair-3.json").read_text(
                encoding="utf-8"
            )
        )["graph"]
        isolated = browser.new_page()
        isolated.set_content(
            (ROOT / "frontend/graph_component/index.html").read_text(encoding="utf-8")
        )
        isolated.evaluate(
            "g => {window.captured=[];window.addEventListener('message',e=>{if(e.data.type==='streamlit:setComponentValue')captured.push(e.data.value)});render(g)}",
            graph,
        )
        expect(isolated.locator(".node")).to_have_count(len(graph["nodes"]))
        isolated.get_by_role("button", name="Claim 7 상세 보기", exact=True).press("Enter")
        isolated.wait_for_function("captured.includes(7)")
        browser.close()
        print(
            "PASS: empty page guard, TXT entry, JSON upload, text viewer, retained legacy graph rendering/keyboard."
        )


if __name__ == "__main__":
    main()
