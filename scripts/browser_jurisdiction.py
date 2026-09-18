"""Same-screen US/KR integration checks; --baseline captures pre-integration US UI."""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/jurisdiction"
SCREENS = ["PDF 검토", "청구항 분석", "관계 지도", "근거 비교"]


def capture(page, prefix):
    snapshots = {}
    for index, name in enumerate(SCREENS):
        page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
        expect(page.get_by_role("heading", name=name, exact=True)).to_be_visible()
        if name == "PDF 검토":
            expect(
                page.frame_locator('iframe[title*="patent_pdf_review"]').locator("#document")
            ).to_be_visible()
        elif name == "관계 지도":
            expect(
                page.frame_locator('iframe[title*="patent_relationship_map"]').locator("body")
            ).to_contain_text("청구항" if prefix == "kr" else "Claim")
        elif name == "근거 비교":
            expect(page.locator(".st-key-comparison-claim")).to_be_visible()
        page.wait_for_timeout(1200)
        snapshots[name] = {
            "sidebar": page.get_by_test_id("stSidebar").inner_text(),
            "headings": page.get_by_role("heading").all_text_contents(),
            "buttons": page.get_by_role("button").all_text_contents(),
            "metrics": page.get_by_test_id("stMetric").all_text_contents(),
            "cards": page.locator('[class*="st-key-comparison-"]').evaluate_all(
                "els => els.map(e => {const r=e.getBoundingClientRect(); return [e.className,r.x,r.y,r.width,r.height];})"
            ),
        }
        page.screenshot(path=str(OUT / f"{prefix}-{index}.png"), full_page=True)
    return snapshots


def check_korean(page):
    data = ROOT / "korean_prototype/data/kr_1020190000844"
    page.get_by_test_id("stSidebar").get_by_text("문서 업로드", exact=True).click()
    page.get_by_text("한국 특허", exact=True).click()
    expect(page.get_by_text("의견제출통지서 XML / PDF", exact=True)).to_be_visible()
    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(data / "KR20190025857A.pdf")
    expect(page.get_by_text("KR20190025857A.pdf", exact=True)).to_be_visible()
    inputs.nth(1).set_input_files(data / "office_action_20190409.xml")
    expect(
        page.get_by_role("button", name="Remove office_action_20190409.xml", exact=True)
    ).to_be_visible()
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=60000)
    pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(pdf.locator("#page-image")).to_be_visible(timeout=30000)
    expect(pdf.locator("#page-number")).to_have_value("3")
    expect(pdf.locator(".review-card.expanded")).to_have_count(0)
    expect(pdf.locator("#summary strong")).to_have_text(["1", "0", "0", "3"])
    expect(pdf.locator('#legend-filters button[data-filter="citation"]')).to_have_text("인용문헌만")
    expect(pdf.locator("#summary")).to_contain_text("특허 가능")
    original = pdf.locator("#summary").evaluate("() => JSON.stringify(model)")
    pdf.get_by_role("button", name="청구항 1 · 직접 지적", exact=True).click()
    expect(pdf.locator(".card-body .check-item").first).to_contain_text("청구항 1:")
    expect(pdf.locator(".card-body .check-item").first).to_contain_text("의견제출통지서 근거")
    assert pdf.locator(".card-body .evidence").first.text_content() == pdf.locator(
        "#summary"
    ).evaluate("() => model.items.find(i=>i.id==='claim-1').status_evidence.text")
    expect(pdf.locator('.annotation.selected[data-item-id="claim-1"]').first).to_be_visible()
    pdf.locator("#rejection-links button").click()
    expect(pdf.locator("#page-status")).to_contain_text("텍스트 입력 문서")
    expect(pdf.locator("#text-page")).to_contain_text("특허법 제29조제2항")
    expect(pdf.locator('.review-card.expanded[data-review-id="claim-1"]')).to_have_count(1)
    expect(pdf.locator('.review-card[data-review-id="rejection-R1"]')).to_have_count(0)
    expect(pdf.locator('#text-page [data-item-id="rejection-R1"]').first).to_be_visible()
    pdf.get_by_role("button", name="청구항 원문 보기", exact=True).click()
    expect(pdf.locator("#page-image")).to_be_visible()
    expect(pdf.locator("#page-number")).to_have_value("3")
    pdf.locator('#point-filters button[data-filter="citation"]').click()
    expect(pdf.locator(".review-card")).to_have_count(3)
    pdf.locator('.review-card[data-review-id="citation-C1"] .card-select').click()
    expect(pdf.locator("#text-page")).to_contain_text("10-2015-0096573")
    expect(pdf.locator("#summary strong")).to_have_text(["1", "0", "0", "3"])
    pdf.locator('#point-filters button[data-filter="all"]').click()
    pdf.get_by_role("button", name="청구항 1 · 직접 지적", exact=True).click()
    assert pdf.locator("#summary").evaluate("() => JSON.stringify(model)") == original

    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    expect(page.get_by_test_id("stMetricValue")).to_have_text(["1", "1", "1", "0", "0"])
    expect(page.locator(".claim-statutes")).to_contain_text("특허법 제29조제2항")
    page.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator('.review-card.expanded[data-review-id="claim-1"]')).to_have_count(1)
    expect(pdf.locator("#page-number")).to_have_value("3")

    page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
    graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
    expect(graph.locator('.node[data-node-id="R1"]')).to_be_visible()
    expect(graph.locator('.node[data-node-id^="C"]:not([data-node-id^="CL"])')).to_have_count(3)
    graph.get_by_role("combobox", name="지도 청구항 찾기").select_option("CL1")
    expect(graph.locator('.node[data-node-id="OA"]')).to_contain_text("의견제출통지서")
    expect(graph.locator("#map-detail")).to_contain_text("특허법 제29조제2항")
    graph.get_by_role("button", name="근거 비교", exact=True).click()
    expect(page.locator(".comparison-rejection")).to_contain_text("특허법 제29조제2항")
    expect(page.locator(".st-key-comparison-oa h3")).to_have_text("거절이유")
    expect(page.locator(".comparison-summary-ground")).to_contain_text("의견제출통지서 요약")
    expect(
        page.locator(".st-key-comparison-citations summary:not(.readable-toggle > summary)")
    ).to_have_count(3)
    page.get_by_role("button", name="의견제출통지서에서 보기", exact=True).click()
    expect(pdf.locator("#text-page")).to_contain_text("특허법 제29조제2항")
    expect(pdf.locator('.review-card.expanded[data-review-id="claim-1"]')).to_have_count(1)
    capture(page, "kr")

    page.get_by_test_id("stSidebar").get_by_text("문서 업로드", exact=True).click()
    expect(page.get_by_role("radio", name="한국 특허", exact=True)).to_be_checked()
    page.get_by_text("미국 특허", exact=True).click()
    page.get_by_test_id("stSidebar").get_by_text("PDF 검토", exact=True).click()
    expect(
        page.get_by_text("먼저 Patent와 Office Action을 업로드하여 분석을 시작하세요.", exact=True)
    ).to_be_visible()
    page.get_by_test_id("stSidebar").get_by_text("문서 업로드", exact=True).click()
    page.get_by_role("button", name="예제 분석 · 가상 문서", exact=True).click()
    expect(pdf.locator("#summary strong")).to_have_text(["5", "3", "0", "3"])
    assert not pdf.locator("#summary").evaluate("() => model.analysis_id.startsWith('kr-')")
    print(
        "KR: real upload, PDF boxes, XML text evidence, claim retention, citations, all four existing screens, US/KR/US isolation passed"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = "--baseline" in sys.argv
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        page.get_by_role("button", name="예제 분석 · 가상 문서", exact=True).click()
        expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(
            timeout=60000
        )
        snapshots = capture(page, "us-before" if baseline else "us-after")
        files = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (ROOT / "frontend").rglob("*")
            if path.is_file()
            and path.suffix in {".css", ".js", ".html", ".py"}
            and path.name != "app.py"
        }
        record = {"screens": snapshots, "components": files}
        if baseline:
            (OUT / "baseline.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            previous = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
            assert previous["screens"] == record["screens"], "US screen structure changed"
            # Label code now varies by jurisdiction; styles and geometry still must not change.
            for name, digest in previous["components"].items():
                if name.endswith(".css") or name.endswith("annotation_geometry.js"):
                    assert files[name] == digest, f"US style/geometry changed: {name}"
            for index in range(4):
                assert (
                    ImageChops.difference(
                        Image.open(OUT / f"us-before-{index}.png"),
                        Image.open(OUT / f"us-after-{index}.png"),
                    ).getbbox()
                    is None
                ), f"US screenshot changed: {SCREENS[index]}"
            print("US: four screen snapshots/pixels and existing CSS/geometry hashes unchanged")
            check_korean(page)
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    main()
