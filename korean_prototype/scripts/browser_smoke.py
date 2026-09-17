"""Live Edge smoke test of the separate Korean prototype on port 8502."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8502", wait_until="domcontentloaded")
        page.get_by_role("button", name="한국 사례 분석", exact=True).click()
        expect(page.get_by_test_id("stMetricValue")).to_have_count(4, timeout=60000)
        expect(page.get_by_test_id("stException")).to_have_count(0)
        assert page.get_by_test_id("stMetricValue").all_text_contents() == ["1", "1", "0", "3"]
        checks.append("Actual sample summary: claims=1, direct=1, dependency=0, citations=3")
        picker = page.get_by_role("combobox").first
        picker.click()
        page.get_by_role("option", name="청구항 1 · 직접 지적", exact=True).click()
        expect(page.get_by_text("적용 법조항: 특허법 제29조제2항", exact=True)).to_be_visible()
        page.get_by_text("R1 · 특허법 제29조제2항", exact=True).click()
        for pub in ["KR20150096573A", "KR20150090348A", "KR20150093093A"]:
            expect(
                page.get_by_role("tabpanel", name="청구항 검토").get_by_text(pub, exact=False)
            ).to_be_visible()
        checks.append("Claim 1, actual Korean rejection and all three linked references visible")
        widths = []
        for width in [1920, 1440, 1280, 1024]:
            page.set_viewport_size({"width": width, "height": 1000})
            text = (
                page.get_by_test_id("stText").filter(has_text="하나 이상의 행사와 매칭되고").first
            )
            expect(text).to_be_visible()
            values = text.evaluate("""node => {
                const s = getComputedStyle(node);
                return {width: node.getBoundingClientRect().width,
                    parent: node.parentElement.getBoundingClientRect().width,
                    wordBreak: s.wordBreak, overflowWrap: s.overflowWrap};
            }""")
            assert values["width"] > 400, values
            assert values["width"] >= values["parent"] * 0.85, values
            assert values["wordBreak"] == "normal", values
            widths.append({"viewport": width, **values})
        checks.append("Readable original text at 1920/1440/1280/1024px")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.get_by_role(
            "heading", name="Patent Review · 한국어 프로토타입", exact=True
        ).scroll_into_view_if_needed()
        page.screenshot(path=str(ARTIFACTS / "korean-claim-review.png"), full_page=True)
        # The first location button belongs to the claim; the second to the OA.
        page.get_by_role("button", name="원문 위치 선택", exact=True).nth(1).click()
        page.get_by_role("tab", name="원문 확인", exact=True).click()
        expect(
            page.get_by_text("XML 원문에는 PDF 페이지 번호가 없습니다.", exact=False)
        ).to_be_visible()
        expect(page.get_by_role("button", name="원본 파일 다운로드", exact=True)).to_be_visible()
        assert page.get_by_test_id("stMetricValue").all_text_contents() == ["1", "1", "0", "3"]
        page.get_by_role("tab", name="청구항 검토", exact=True).click()
        expect(page.get_by_text("청구항 1 · 직접 지적", exact=True).last).to_be_visible()
        page.get_by_role("button", name="원문 위치 선택", exact=True).first.click()
        page.get_by_role("tab", name="원문 확인", exact=True).click()
        expect(page.get_by_role("spinbutton", name="PDF 페이지", exact=True)).to_have_value("3")
        expect(page.get_by_test_id("stImage")).to_be_visible(timeout=30000)
        checks.append("OA XML navigation retains selected Claim; claim PDF opens page 3")
        page.screenshot(path=str(ARTIFACTS / "korean-pdf-page3.png"), full_page=True)
        page.get_by_role("button", name="한국 사례 분석", exact=True).click()
        page.get_by_role("tab", name="청구항 검토", exact=True).click()
        expect(
            page.get_by_text("청구항을 선택하면 원문과 연결된 거절 사유를 확인할 수 있습니다.")
        ).to_be_visible()
        expect(page.get_by_test_id("stException")).to_have_count(0)
        checks.append("New analysis resets claim/source selection")
        page.get_by_text("직접 문서 업로드", exact=True).click()
        data = ROOT / "data" / "kr_1020190000844"
        uploads = page.locator('input[type="file"]')
        expect(uploads).to_have_count(3)
        uploads.nth(0).set_input_files(
            {
                "name": "uploaded_patent.pdf",
                "mimeType": "application/pdf",
                "buffer": (data / "KR20190025857A.pdf").read_bytes(),
            }
        )
        uploads.nth(1).set_input_files(str(data / "office_action_20190409.xml"))
        uploads.nth(2).set_input_files(
            [
                str(data / f"{pub}.pdf")
                for pub in ["KR20150096573A", "KR20150090348A", "KR20150093093A"]
            ]
        )
        page.get_by_role("button", name="업로드 문서 분석", exact=True).click()
        processing = page.get_by_text("업로드한 문서를 분석하고 있습니다.", exact=True)
        expect(processing).to_be_visible(timeout=15000)
        expect(processing).to_be_hidden(timeout=60000)
        page.get_by_role("combobox", name="검토할 청구항", exact=True).click()
        page.get_by_role("option", name="청구항 1 · 직접 지적", exact=True).click()
        expect(page.get_by_text("uploaded_patent.pdf · p. 3", exact=True)).to_be_visible(
            timeout=30000
        )
        assert page.get_by_test_id("stMetricValue").all_text_contents() == ["1", "1", "0", "3"]
        expect(page.get_by_test_id("stException")).to_have_count(0)
        checks.append("Real browser file uploads preserve claim/rejection/citation results")
        assert not errors, errors
        browser.close()
    report = {"passed": checks, "widths": widths, "browser_errors": errors}
    (ARTIFACTS / "browser_checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
