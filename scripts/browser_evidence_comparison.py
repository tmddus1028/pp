"""uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_evidence_comparison.py [--full]"""

import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/pdf_review"


def choose(page, label, value):
    field = page.get_by_role("combobox", name=label, exact=True)
    if field.input_value() == value:
        return
    # Streamlit can replace the option list after responsive layout reruns.
    for attempt in range(3):
        field.click()
        field.fill(value)
        try:
            page.get_by_role("option", name=value, exact=True).click(timeout=3000)
            break
        except PlaywrightTimeoutError:
            if attempt == 2:
                raise
            field.press("Escape")
    expect(page.get_by_role("combobox", name=label, exact=True)).to_have_value(value)
    if label == "비교할 Claim":
        expect(page.locator(".comparison-overview strong")).to_have_text(value)


def check_comparison(page, pdf, claim_page="41"):
    pdf.get_by_role("combobox", name="거절 사유 필터").select_option("all")
    # Explicit PDF annotation selection opens the card even if it was already selected.
    header = pdf.get_by_role("button", name="Claim 14 · 직접 지적", exact=True)
    if header.get_attribute("aria-expanded") != "true":
        header.click()
    else:
        pdf.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value(claim_page)
    original = pdf.locator("#overlays").evaluate("""() => ({
        claim: itemById('claim-14').evidence.text,
        oa: model.rejections.map(r=>({id:r.rejection_id,text:r.evidence.text})),
        document: model.documents.find(d=>d.kind==='office_action').id,
        annotations: JSON.stringify(model.annotations)
    })""")
    pdf.get_by_role("button", name="근거 비교", exact=True).click()
    expect(page.get_by_role("heading", name="근거 비교", exact=True)).to_be_visible(timeout=15000)
    expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 14")
    expect(page.locator('iframe[title*="patent_pdf_review"]')).to_have_count(0)
    expect(page.locator(".st-key-comparison-claim .comparison-source")).to_have_text(
        original["claim"]
    )
    expect(page.locator(".st-key-comparison-claim")).to_contain_text("상위 Claim: Claim 1")
    expect(page.locator(".st-key-comparison-claim")).to_contain_text("직접 종속 Claim: Claim 15")
    expect(page.locator(".comparison-rejection")).to_have_count(2)
    for rejection in original["oa"]:
        expect(
            page.locator(".st-key-comparison-oa .comparison-source").filter(
                has_text=rejection["text"][:60]
            )
        ).to_have_text(rejection["text"])
    expect(page.get_by_text("현재 자동 연결된 명세서 근거가 없습니다.", exact=True)).to_be_visible()
    refs = page.locator(".st-key-comparison-citations")
    expect(refs.locator("summary:not(.readable-toggle > summary)")).to_have_count(5)
    for label in ["Lombardi", "Bendiera", "Hout", "Greco", "Lipska"]:
        expect(
            refs.locator("summary:not(.readable-toggle > summary)").filter(has_text=label)
        ).to_have_count(1)
    refs.locator("summary:not(.readable-toggle > summary)").filter(has_text="Greco").click()
    expect(refs.get_by_text("type: npl", exact=True).first).to_be_visible()
    expect(refs.get_by_text("Year: 2010", exact=True)).to_be_visible()
    expect(
        refs.get_by_text("Publication / journal: Molecular and Cellular Endocrinology", exact=True)
    ).to_be_visible()
    expect(
        refs.locator(".comparison-source.citation")
        .filter(has_text="Molecular and Cellular Endocrinology")
        .first
    ).to_be_visible()
    refs.locator("summary:not(.readable-toggle > summary)").filter(has_text="Greco").click()
    # Desktop grid and the complete text are separate from the PDF viewer.
    a, b = [page.locator(".st-key-comparison-" + key).bounding_box() for key in ["claim", "oa"]]
    c, d = [
        page.locator(".st-key-comparison-" + key).bounding_box()
        for key in ["specification", "citations"]
    ]
    assert abs(a["y"] - b["y"]) < 3 and b["x"] > a["x"] + a["width"]
    assert abs(c["y"] - d["y"]) < 3 and c["y"] > a["y"] + a["height"]
    page.get_by_role("heading", name="근거 비교", exact=True).scroll_into_view_if_needed()
    page.set_viewport_size({"width": 1366, "height": 1200})
    page.screenshot(path=str(ROOT / "data/outputs/evidence-comparison-claim14.png"), full_page=True)
    page.set_viewport_size({"width": 1366, "height": 768})

    choose(page, "비교할 지적 사유", "R1 · 35 U.S.C. 112")
    expect(page.locator(".comparison-rejection")).to_have_count(1)
    expect(page.locator('.comparison-focus [data-focus="112"]')).to_be_visible()
    expect(page.locator('.comparison-focus [data-focus="103"]')).to_have_count(0)
    expect(refs.locator("summary:not(.readable-toggle > summary)")).to_have_count(0)
    choose(page, "비교할 지적 사유", "R2 · 35 U.S.C. 103(a)")
    expect(page.locator('.comparison-focus [data-focus="103"]')).to_be_visible()
    expect(page.locator('.comparison-focus [data-focus="112"]')).to_have_count(0)
    expect(refs.locator("summary:not(.readable-toggle > summary)")).to_have_count(5)
    page.get_by_role("button", name="Office Action에서 보기", exact=True).click()
    expect(pdf.locator("#document")).to_have_value(original["document"], timeout=15000)
    expect(pdf.locator("#page-number")).to_have_value("2")
    expect(pdf.locator('.annotation.selected[data-item-id="rejection-R2"]').first).to_be_visible(
        timeout=15000
    )
    page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
    expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 14")
    expect(page.get_by_role("combobox", name="비교할 지적 사유")).to_have_value(
        "R2 · 35 U.S.C. 103(a)"
    )
    page.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value(claim_page)
    expect(pdf.locator('.annotation.selected[data-item-id="claim-14"]')).to_be_visible(
        timeout=15000
    )
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-14")
    pdf.get_by_role("button", name="근거 비교", exact=True).click()
    choose(page, "비교할 Claim", "Claim 2")
    expect(page.get_by_role("combobox", name="비교할 지적 사유")).to_have_value("전체 연결 사유")
    expect(page.locator(".st-key-comparison-claim")).to_contain_text("직접 종속 Claim: 없음")
    choose(page, "비교할 지적 사유", "R1 · 35 U.S.C. 112")
    expect(page.locator(".comparison-overview .claim-state")).to_have_text("종속 영향")
    expect(page.locator(".comparison-rejection")).to_contain_text("직접 지적 아님")
    expect(page.locator(".st-key-comparison-claim .comparison-source")).to_have_css(
        "border-left-color", "rgb(214, 165, 46)"
    )
    expect(refs.locator("summary:not(.readable-toggle > summary)")).to_have_count(0)
    choose(page, "비교할 Claim", "Claim 14")
    page.get_by_test_id("stSidebar").get_by_text("관계 지도", exact=True).click()
    graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
    graph.get_by_role("combobox", name="지도 거절 범위").select_option("R1")
    graph.get_by_role("combobox", name="지도 Claim 찾기").select_option("CL14")
    graph.get_by_role("button", name="근거 비교", exact=True).click()
    expect(page.get_by_role("combobox", name="비교할 Claim")).to_have_value("Claim 14")
    expect(page.get_by_role("combobox", name="비교할 지적 사유")).to_have_value(
        "R1 · 35 U.S.C. 112"
    )
    choose(page, "비교할 지적 사유", "전체 연결 사유")
    expect(page.locator(".comparison-rejection")).to_have_count(2)
    expect(refs.locator("summary:not(.readable-toggle > summary)")).to_have_count(5)
    page.set_viewport_size({"width": 900, "height": 900})
    a, b = [page.locator(".st-key-comparison-" + key).bounding_box() for key in ["claim", "oa"]]
    assert b["y"] >= a["y"] + a["height"]
    assert abs(a["x"] - b["x"]) < 3
    page.screenshot(path=str(ROOT / "data/outputs/evidence-comparison-narrow.png"), full_page=True)
    page.set_viewport_size({"width": 1366, "height": 768})
    page.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.locator('.annotation.selected[data-item-id="claim-14"]')).to_be_visible(
        timeout=15000
    )
    assert (
        pdf.locator("#overlays").evaluate("() => JSON.stringify(model.annotations)")
        == original["annotations"]
    )
    print(
        "Comparison passed: actual Claim 14, two original OA grounds, all 5 Patent/NPL citations, scope emphasis, inherited Claim 2, empty specification, Claim/OA PDF links, map handoff, 2x2/stacked layout, unchanged annotations."
    )


def check_support_comparison(page, pdf):
    page.get_by_test_id("stSidebar").get_by_text("근거 비교", exact=True).click()
    choose(page, "비교할 Claim", "Claim 1")
    spec = page.locator(".st-key-comparison-specification")
    expect(spec.get_by_text("Paragraph [0018]", exact=True)).to_be_visible()
    expect(spec.get_by_text("Figure 1", exact=True)).to_be_visible()
    expect(spec).to_contain_text("명시적으로 언급")
    choose(page, "비교할 Claim", "Claim 4")
    expect(page.locator(".comparison-overview .claim-state")).to_have_text("추출된 지적 없음")
    expect(
        page.get_by_text("이 Claim에 연결된 심사관 지적이 없습니다.", exact=True)
    ).to_be_visible()
    expect(page.get_by_text("현재 자동 연결된 명세서 근거가 없습니다.", exact=True)).to_be_visible()
    choose(page, "비교할 Claim", "Claim 1")
    spec.get_by_role("button", name="명세서 PDF에서 보기").first.click()
    expect(pdf.locator("#page-number")).to_have_value("1")
    expect(pdf.locator(".annotation.specification.selected").first).to_be_visible(timeout=15000)
    print(
        "Specification comparison passed: existing explicit paragraph/figure only, unaddressed Claim empty state, source PDF link."
    )


def upload(page, patent, oa):
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(patent)
    inputs.nth(1).set_input_files(oa)
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=180000)
    pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
    return pdf


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        full = "--full" in sys.argv
        patent = ROOT / (
            "data/raw/us20150283132a1/US20150283132A1.pdf"
            if full
            else "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf"
        )
        pdf = upload(page, patent, FIXTURES / "office_action_reconstructed.pdf")
        check_comparison(page, pdf, claim_page="41" if full else "2")
        support_page = browser.new_page(viewport={"width": 1366, "height": 768})
        support_page.on("pageerror", lambda error: errors.append(str(error)))
        support = upload(
            support_page, FIXTURES / "patent.pdf", FIXTURES / "office_action_support.pdf"
        )
        check_support_comparison(support_page, support)
        assert not errors, errors
        browser.close()
