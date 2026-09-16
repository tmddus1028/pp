"""uv run --no-project --with playwright --python 3.11 python -X utf8 scripts/browser_pdf_review.py"""

import json
import re
import sys
from pathlib import Path

from browser_accordion_flow import check_accordion
from browser_badge_flow import check_claim_badges
from browser_claim_analysis_flow import check_claim_analysis
from browser_claim_evidence_flow import check_claim_evidence_flow
from browser_evidence_comparison import check_comparison, check_support_comparison
from browser_relationship_flow import check_relationship_flow
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/pdf_review"


def upload(page, patent, oa):
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(patent)
    inputs.nth(1).set_input_files(oa)
    page.get_by_role("button", name="분석 시작", exact=True).click()
    # The full public patent includes ten sparse pages requiring local OCR.
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=180000)
    frame = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(frame.locator("#page-image")).to_be_visible(timeout=60000)
    return frame


def check_claim_region(frame, number):
    region = frame.locator(f'.annotation.region[data-item-id="claim-{number}"]')
    expect(region).to_have_count(1)
    source = frame.locator("#overlays").evaluate(
        """(_, number) => annotations().filter(a => a.claim_number === number).flatMap(a => a.boxes)""",
        number,
    )
    assert len(source) > 3, (number, source)
    box = json.loads(region.get_attribute("data-box"))
    assert box == [
        min(b[0] for b in source),
        min(b[1] for b in source),
        max(b[2] for b in source),
        max(b[3] for b in source),
    ]
    assert box[2] - box[0] < 0.4, "The Claim border must stay in its original column."
    expect(region).to_have_css("border-top-width", "3px")
    expect(region).to_have_css("border-top-color", "rgb(217, 67, 67)")
    expect(region).to_have_css("background-color", "rgba(217, 67, 67, 0.05)")
    expect(region).to_have_css("mix-blend-mode", "normal")
    expect(frame.locator(".review-card.active")).to_have_attribute(
        "data-review-id", f"claim-{number}"
    )
    expect(frame.locator(".review-card.active .card-select")).to_be_in_viewport()
    print(f"Claim {number}: {len(source)} source boxes -> one column-bounded border {box}.")
    return region


def check_region_geometry(frame):
    frame.locator("#overlays").evaluate(
        """() => {
          const {claimRegions, groupAnnotations} = window.PatentAnnotationGeometry;
          const equal = (a, b) => {
            if (JSON.stringify(a) !== JSON.stringify(b)) throw Error(JSON.stringify({a, b}));
          };
          // One Claim wraps from the bottom of the left column to the right top.
          // Even a narrow gutter remains unboxed, and no unrelated Claim is included.
          const columns = [[.1,.7,.49,.75],[.494,.1,.9,.15]];
          equal(claimRegions(columns), columns);
          equal(claimRegions([[.1,.2,.3,.22],[.31,.24,.45,.26]], [[.1,.5,.45,.52]]),
            [[.1,.2,.45,.26]]);
          equal(claimRegions([[.1,.1,.9,.12],[.1,.12,.8,.14]]), [[.1,.1,.9,.14]]);
          equal(claimRegions([]), []);
          const original = JSON.stringify(model);
          const source = annotations();
          equal(groupAnnotations([...source, ...source]), groupAnnotations(source));
          drawOverlays([...source, ...source]);
          const keys = [...document.querySelectorAll('.annotation.region')]
            .map(n => n.dataset.itemId + n.dataset.box);
          if (new Set(keys).size !== keys.length) throw Error('Duplicate Claim borders');
          equal(JSON.stringify(model), original);
          drawPage();
        }"""
    )


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    errors = []
    if "--supplemental" not in sys.argv:
        page = browser.new_page(viewport={"width": 1366, "height": 768}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        frame = upload(
            page,
            ROOT / "data/raw/us20150283132a1/US20150283132A1.pdf",
            FIXTURES / "office_action_reconstructed.pdf",
        )
        expect(frame.locator("#page-number")).to_have_value("40")
        expect(frame.get_by_role("button", name="직접 지적 19", exact=True)).to_be_visible()
        expect(frame.get_by_role("button", name="인용 문헌 5", exact=True)).to_be_visible()
        expect(
            frame.locator('.annotation.direct_rejection[data-item-id="claim-1"]').first
        ).to_be_visible()
        page.screenshot(path=str(ROOT / "data/outputs/pdf-review-desktop.png"), full_page=True)
        print(
            "Phase A passed: real 41-page patent PDF, reconstructed OA PDF, review default, Claim 1 red overlay."
        )
        check_accordion(page, frame)
        check_claim_evidence_flow(page, frame)
        check_region_geometry(frame)
        check_claim_region(frame, 1)
        for number in [14, 18]:
            frame.get_by_role("button", name=f"Claim {number} · 직접 지적", exact=True).click()
            expect(frame.locator("#page-number")).to_have_value("41")
            expect(frame.locator("#loading")).to_be_hidden(timeout=15000)
            region = check_claim_region(frame, number)
            expect(region).to_have_css("filter", "none")
            page.screenshot(
                path=str(ROOT / f"data/outputs/pdf-review-claim-{number}-border.png"),
                full_page=True,
            )
        check_claim_badges(page, frame)
        normal = frame.locator('.annotation.region[data-item-id="claim-14"]')
        expect(normal).to_have_css("border-top-width", "2px")
        # Overlay -> card keeps the current PDF page, including Claim 1's continuation.
        normal.click()
        check_claim_region(frame, 14)
        expect(frame.locator(".review-card.active .card-meta")).to_contain_text("35 USC 112")
        expect(frame.locator(".review-card.active .card-meta")).to_contain_text("35 USC 103(a)")
        frame.locator('.annotation.region[data-item-id="claim-1"]').click()
        expect(frame.locator("#page-number")).to_have_value("41")
        region = check_claim_region(frame, 1)
        expect(region).to_have_css("filter", "none")
        page.screenshot(
            path=str(ROOT / "data/outputs/pdf-review-claim-1-border.png"), full_page=True
        )
        frame.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
        expect(frame.locator("#page-number")).to_have_value("40")
        print(
            "Claim regions passed: pages 40/41, Claims 1/14/18, columns, no duplicates, bidirectional selection."
        )
        check_relationship_flow(page, frame)
        frame.get_by_role("button", name="Claim 3 · 직접 지적", exact=True).click()
        expect(frame.locator("#page-number")).to_have_value("41")
        expect(frame.locator('.annotation.selected[data-item-id="claim-3"]').first).to_be_visible(
            timeout=15000
        )
        frame.locator('.annotation[data-item-id="claim-1"]').first.click()
        expect(frame.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-1")
        # Clicking the card navigates to the first of Claim 1's two source pages.
        frame.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
        expect(frame.locator("#page-number")).to_have_value("40")
        expect(frame.locator("#loading")).to_be_hidden(timeout=15000)
        original_width = frame.locator("#paper").bounding_box()["width"]
        frame.get_by_role("button", name="확대", exact=True).click()
        assert frame.locator("#paper").bounding_box()["width"] > original_width
        frame.get_by_role("button", name="페이지 맞춤", exact=True).click()
        frame.get_by_role("button", name="너비 맞춤", exact=True).click()
        frame.get_by_role("button", name="이전 페이지", exact=True).click()
        expect(frame.locator("#page-number")).to_have_value("39")
        frame.get_by_role("button", name="다음 페이지", exact=True).click()
        expect(frame.locator("#page-number")).to_have_value("40")
        frame.get_by_role("textbox", name="PDF 검색").fill("0721")
        frame.get_by_role("textbox", name="PDF 검색").press("Enter")
        expect(frame.locator(".search-hit").first).to_be_visible(timeout=15000)
        frame.get_by_role("button", name="인용 문헌 5", exact=True).click()
        expect(frame.locator(".review-card")).to_have_count(5)
        frame.get_by_role("button", name="Greco et al · 인용 문헌", exact=True).click()
        expect(frame.locator("#document")).to_contain_text("Office Action")
        expect(frame.locator(".annotation.citation.selected").first).to_be_visible(timeout=15000)
        expect(frame.locator(".review-card.active")).to_contain_text(
            "Molecular and Cellular Endocrinology"
        )
        frame.get_by_role("combobox", name="거절 사유 필터").select_option("R1")
        expect(frame.get_by_role("button", name="종속 영향 4", exact=True)).to_be_visible()
        frame.get_by_role("button", name="종속 영향 4", exact=True).click()
        expect(frame.locator('.annotation.dependency[data-item-id="claim-2"]').first).to_be_visible(
            timeout=15000
        )
        expect(frame.locator(".annotation.direct_rejection")).to_have_count(0)
        frame.get_by_role("button", name="Claim 2 · 종속 영향", exact=True).click()
        frame.get_by_role("checkbox").first.check()
        frame.get_by_role("button", name="Claim 5 · 종속 영향", exact=True).click()
        expect(frame.get_by_role("checkbox").first).to_be_checked()
        page.screenshot(path=str(ROOT / "data/outputs/pdf-review-dependency.png"), full_page=True)
        with page.expect_download() as downloaded:
            frame.get_by_role("link", name="원본 PDF 다운로드").click()
        assert (
            Path(downloaded.value.path()).read_bytes()
            == (ROOT / "data/raw/us20150283132a1/US20150283132A1.pdf").read_bytes()
        )
        check_claim_analysis(page, frame)
        print(
            "Phase B passed: bidirectional selection, page/zoom/search, 5 citations, correct R1 yellow filter, checklist, original download, Claim list."
        )
        check_comparison(page, frame)

    support_page = browser.new_page(viewport={"width": 1366, "height": 768})
    support_page.on("pageerror", lambda error: errors.append(str(error)))
    support = upload(support_page, FIXTURES / "patent.pdf", FIXTURES / "office_action_support.pdf")
    expect(support.locator('.annotation.dependency[data-item-id="claim-3"]').first).to_be_visible()
    support.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
    support.get_by_role("button", name="Paragraph [0018]", exact=True).click()
    expect(support.locator("#page-number")).to_have_value("1")
    expect(support.locator(".annotation.specification.selected").first).to_be_visible(timeout=15000)
    support.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
    support.get_by_role("button", name="Figure 1", exact=True).click()
    expect(support.locator(".review-card.active")).to_contain_text("Figure 1")
    check_support_comparison(support_page, support)
    support_page.set_viewport_size({"width": 900, "height": 900})
    expect(support.locator("#workspace")).to_have_css(
        "grid-template-columns", re.compile(r"^[0-9.]+px$")
    )
    viewer = support.locator(".viewer").bounding_box()
    panel = support.locator(".review-panel").bounding_box()
    assert panel["y"] > viewer["y"] + viewer["height"] - 5
    support_page.screenshot(path=str(ROOT / "data/outputs/pdf-review-narrow.png"), full_page=True)
    print("Phase C passed: explicit paragraph and drawing links, narrow stacked layout.")

    scan_page = browser.new_page(viewport={"width": 1366, "height": 768})
    scan_page.on("pageerror", lambda error: errors.append(str(error)))
    scanned = upload(scan_page, FIXTURES / "patent_scan.pdf", FIXTURES / "office_action_scan.pdf")
    expect(
        scanned.locator('.annotation.direct_rejection[data-item-id="claim-1"]').first
    ).to_be_visible()
    expect(scanned.locator('.annotation.dependency[data-item-id="claim-3"]').first).to_be_visible()
    scanned.get_by_role("button", name="Claim 3 · 종속 영향", exact=True).click()
    expect(scanned.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-3")
    expect(scanned.locator("#page-status")).to_contain_text("OCR 위치")
    scan_page.screenshot(path=str(ROOT / "data/outputs/pdf-review-ocr.png"), full_page=True)
    print(
        "OCR passed: image-only patent + OA, real Tesseract coordinates, Claim 1 red and Claim 3 yellow."
    )
    assert not errors, errors
    browser.close()
