"""Claim-preserving OA navigation in Edge; standalone uses R1 p.3 / R2 p.4."""

from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_claim_evidence_flow(page, pdf):
    pdf.get_by_role("combobox", name="거절 사유 필터").select_option("all")
    pdf.get_by_role("button", name="직접 지적 19", exact=True).click()
    header = pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True)
    if header.get_attribute("aria-expanded") != "true":
        header.click()
    else:
        pdf.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expected = pdf.locator("#overlays").evaluate(
        """() => ({
            original: JSON.stringify(model),
            patent: itemById('claim-1').evidence,
            rejections: model.rejections.map(r=>({id:r.rejection_id,evidence:r.evidence}))
        })"""
    )

    def cards():
        return pdf.locator("#review-list > .review-card").evaluate_all(
            "nodes => nodes.map(n=>n.dataset.reviewId)"
        )

    def claim_selected(number=1):
        expect(pdf.locator(".review-card.active")).to_have_attribute(
            "data-review-id", f"claim-{number}"
        )
        expect(pdf.locator(".review-card.expanded")).to_have_attribute(
            "data-review-id", f"claim-{number}"
        )
        expect(pdf.locator('[data-review-id^="rejection-"]')).to_have_count(0)

    def at_rejection(rejection):
        rid, evidence = rejection["id"], rejection["evidence"]
        expect(pdf.locator("#document")).to_have_value(evidence["document_id"])
        expect(pdf.locator("#page-number")).to_have_value(str(evidence["page_numbers"][0]))
        expect(
            pdf.locator(f'.annotation.selected[data-item-id="rejection-{rid}"]').first
        ).to_be_visible(timeout=15000)
        claim_selected()
        expect(pdf.locator(".current-evidence")).to_contain_text(rid)
        expect(pdf.locator(".current-evidence")).to_contain_text(
            f"Office Action p. {evidence['page_numbers'][0]}"
        )
        expect(pdf.locator(f'details[data-rejection-id="{rid}"]')).to_have_attribute("open", "")
        assert cards() == before
        assert pdf.locator("#overlays").evaluate(
            """(_, rid) => state.selected==='claim-1' && state.expanded==='claim-1'
                && state.viewer_evidence==='rejection-'+rid && state.active_rejection===rid""",
            rid,
        )

    # Repeat with a Claim-only filter and with the unchanged full list.
    for filter_id in ["direct_rejection", "all"]:
        pdf.locator(f'#legend-filters button[data-filter="{filter_id}"]').click()
        before = cards()
        if filter_id == "direct_rejection":
            assert before == [f"claim-{n}" for n in range(1, 20)]
        first, second = expected["rejections"][:2]
        detail = pdf.locator(f'details[data-rejection-id="{first["id"]}"]')
        if detail.get_attribute("open") is None:
            detail.locator("summary").click()
        detail.get_by_role(
            "button", name=f"OA p. {first['evidence']['page_numbers'][0]}에서 보기"
        ).click()
        at_rejection(first)
        pdf.locator(".current-evidence").get_by_role(
            "button", name=f"{second['id']} 근거 보기"
        ).click()
        at_rejection(second)
        # Clicking the OA region again must also keep Claim 1 and its accordion.
        pdf.locator(f'.annotation.selected[data-item-id="rejection-{second["id"]}"]').first.click()
        at_rejection(second)
        # Zoom causes a server round-trip; evidence and Claim state must both survive.
        pdf.get_by_role("button", name="확대", exact=True).click()
        at_rejection(second)
        if filter_id == "direct_rejection":
            page.screenshot(path=str(ROOT / "data/outputs/claim1-oa-evidence.png"), full_page=True)
        pdf.get_by_role("button", name="청구항 원문 보기", exact=True).click()
        expect(pdf.locator("#document")).to_have_value(expected["patent"]["document_id"])
        expect(pdf.locator("#page-number")).to_have_value(
            str(expected["patent"]["page_numbers"][0])
        )
        expect(pdf.locator('.annotation.selected[data-item-id="claim-1"]').first).to_be_visible(
            timeout=15000
        )
        claim_selected()
        expect(pdf.locator(".current-evidence")).to_have_count(0)
        assert cards() == before

    pdf.get_by_role("button", name="Claim 3 · 직접 지적", exact=True).click()
    claim_selected(3)
    expect(pdf.locator('.annotation.selected[data-item-id="claim-3"]').first).to_be_visible(
        timeout=15000
    )
    assert pdf.locator("#overlays").evaluate("() => state.active_rejection===null")
    assert pdf.locator("#overlays").evaluate("() => JSON.stringify(model)") == expected["original"]
    # Restore Claim 1 for existing geometry/accordion regressions.
    pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
    pdf.get_by_role("button", name="너비 맞춤", exact=True).click()
    print(
        "Claim evidence passed: R1/R2 source pages and highlights, unchanged lists/filters, "
        "Claim 1 selected and expanded, no rejection cards, nested active evidence, "
        "PDF return, explicit Claim 3 selection, unchanged analysis."
    )


if __name__ == "__main__":
    from pypdf import PdfReader, PdfWriter

    with TemporaryDirectory(prefix="patent-review-evidence-") as temp, sync_playwright() as p:
        # Reconstructed OA only: two blank covers reproduce the requested p.3 transition.
        writer = PdfWriter()
        for _ in range(2):
            writer.add_blank_page(width=612, height=792)
        for source in PdfReader(
            ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf"
        ).pages:
            writer.add_page(source)
        oa = Path(temp) / "office_action_reconstructed_p3.pdf"
        writer.write(oa)
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        inputs = page.locator('input[type="file"]')
        inputs.nth(0).set_input_files(
            ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf"
        )
        inputs.nth(1).set_input_files(oa)
        page.get_by_role("button", name="분석 시작", exact=True).click()
        pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
        expect(pdf.locator("#page-image")).to_be_visible(timeout=90000)
        check_claim_evidence_flow(page, pdf)
        assert not errors, errors
        browser.close()
