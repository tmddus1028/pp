"""Actual pair: show seven relied citations, retain hidden roles in the model."""

from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_summary(pdf):
    expect(pdf.locator("#summary > button")).to_have_count(4)
    for text in ["직접 지적 17", "종속 영향 / Objection 2", "허용 0", "인용 문헌 7"]:
        expect(pdf.locator("#summary").get_by_role("button", name=text, exact=True)).to_be_visible()
    expect(pdf.locator("#other-literature")).to_have_count(0)
    expect(pdf.locator('#point-filters [data-filter="supporting_evidence"]')).to_have_count(0)
    expect(pdf.locator('#point-filters [data-filter="not_relied_upon"]')).to_have_count(0)
    for name in ["Wei", "Oda", "Biyikli"]:
        expect(pdf.locator(".card-title").filter(has_text=name)).to_have_count(0)


def filter_only(pdf, target, count):
    """A list filter must preserve selection, scope, evidence, page and overlays."""
    snapshot = """() => JSON.stringify({
        selected:state.selected, expanded:state.expanded, scope:state.scope,
        active:state.active_rejection, evidence:state.viewer_evidence,
        document:state.document, page:state.page,
        overlays:document.getElementById('overlays').innerHTML
    })"""
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    before = pdf.locator("#workspace").evaluate(snapshot)
    target.click()
    expect(pdf.locator(".review-card")).to_have_count(count)
    assert pdf.locator("#workspace").evaluate(snapshot) == before
    check_summary(pdf)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1450, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:8501", wait_until="networkidle")
    inputs = page.locator('input[type="file"]')
    inputs.nth(0).set_input_files(ROOT / "tests/fixtures/claim_sections/pp_ex3.pdf")
    inputs.nth(1).set_input_files(ROOT / "tests/fixtures/oa_status/pp_vd3.pdf")
    page.get_by_role("button", name="분석 시작", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=120000)
    pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
    expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
    check_summary(pdf)
    expect(pdf.locator('#point-filters [data-filter="all"]')).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(pdf.locator(".review-card")).to_have_count(27)
    expect(pdf.locator(".review-card.expanded")).to_have_count(0)
    original = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
    assert pdf.locator("#workspace").evaluate("""() => {
        const hidden=model.items.filter(i=>i.kind==='citation'&&i.citation_role!=='relied_upon');
        return hidden.length===3&&hidden.some(i=>i.title==='Wei'&&i.citation_role==='supporting_evidence')
            &&hidden.filter(i=>i.citation_role==='not_relied_upon').length===2
            &&hidden.every(i=>i.occurrences.length>0);
    }""")
    expect(pdf.locator("#summary .citation")).to_have_attribute(
        "title", "심사관이 실제 거절 논리에 사용한 선행기술"
    )
    page.screenshot(path=str(ROOT / "data/outputs/citation-ui-all.png"), full_page=True)
    liu = pdf.get_by_role("button", name="Liu et al · 인용 문헌", exact=True)
    expect(liu).to_have_count(1)
    liu.click()
    card = pdf.locator(".review-card.expanded")
    cid = card.get_attribute("data-review-id")
    expect(card.locator(".citation-rejection-badges .badge")).to_have_count(5)
    for rid in ["R1", "R2", "R3", "R4", "R5"]:
        expect(
            card.locator(f'.citation-rejection-badges [data-rejection-id="{rid}"]')
        ).to_have_count(1)
    occurrence = card.locator('.citation-occurrence[data-rejection-id="R2"]')
    occurrence.locator("summary").click()
    occurrence.get_by_role("button", name="R2 인용 원문 보기", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("5")
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", cid)
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    expect(pdf.locator("#scope")).to_have_value("all")
    check_summary(pdf)
    filter_only(pdf, pdf.locator('#point-filters [data-filter="citation"]'), 7)
    filter_only(pdf, pdf.locator('#point-filters [data-filter="all"]'), 27)
    page.screenshot(path=str(ROOT / "data/outputs/citation-registry-liu-r2.png"), full_page=True)
    pdf.locator("#scope").select_option("all")
    filter_only(pdf, pdf.locator('#point-filters [data-filter="citation"]'), 7)
    expect(pdf.locator(".card-title")).to_have_text(
        [
            name + "거절 근거"
            for name in [
                "Liu et al",
                "Donmez et al",
                "Bakke et al",
                "Huang et al",
                "Yao et al",
                "Nakayama et al",
                "Motamedi",
            ]
        ]
    )
    pdf.get_by_role("button", name="Liu et al · 인용 문헌", exact=True).click()
    expect(pdf.locator(".review-card.expanded")).to_have_count(0)
    expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
    pdf.locator("#review-list").evaluate("node => {node.scrollTop=0}")
    page.screenshot(path=str(ROOT / "data/outputs/citation-registry-seven.png"), full_page=True)
    pdf.get_by_role("button", name="Motamedi · 인용 문헌", exact=True).click()
    card = pdf.locator(".review-card.expanded")
    expect(card.locator(".citation-rejection-badges .badge")).to_have_count(1)
    expect(card.locator(".citation-rejection-badges")).to_have_text("R5")
    for n in [12, 13, 14]:
        expect(card.get_by_role("button", name=f"Claim {n}", exact=True)).to_be_visible()
    filter_only(pdf, pdf.locator('#point-filters [data-filter="all"]'), 27)
    pdf.get_by_role("button", name="Claim 12 · 직접 지적", exact=True).click()
    expect(pdf.locator(".card-body")).to_contain_text("관련 인용문헌 · 5개")
    expect(pdf.locator(".card-body").get_by_role("button", name="Wei", exact=True)).to_have_count(0)
    # Hidden citation annotations are suppressed on their source page too.
    for hidden in pdf.locator("#workspace").evaluate("""() => model.items
        .filter(i=>i.kind==='citation'&&i.citation_role!=='relied_upon')
        .map(i=>({id:i.id,document:i.evidence.document_id,page:i.evidence.page_numbers[0]}))"""):
        pdf.locator("#document").select_option(hidden["document"])
        pdf.locator("#page-number").fill(str(hidden["page"]))
        pdf.locator("#page-number").press("Enter")
        expect(pdf.locator("#loading")).to_be_hidden(timeout=15000)
        expect(pdf.locator(f'.annotation[data-item-id="{hidden["id"]}"]')).to_have_count(0)
    check_summary(pdf)
    pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-1")
    pdf.locator("#rejection-links").get_by_role("button", name="R1 · 35 USC 103").click()
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-1")
    filter_only(pdf, pdf.locator('#point-filters [data-filter="citation"]'), 7)
    filter_only(pdf, pdf.locator('#point-filters [data-filter="all"]'), 27)
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-1")
    expect(pdf.locator(".current-evidence")).to_have_attribute("data-rejection-id", "R1")
    pdf.get_by_role("button", name="청구항 원문 보기", exact=True).click()
    expect(pdf.locator(".review-card.expanded")).to_have_attribute("data-review-id", "claim-1")
    check_summary(pdf)
    filter_only(pdf, pdf.locator('#point-filters [data-filter="citation"]'), 7)
    page.get_by_test_id("stSidebar").get_by_text("청구항 분석", exact=True).click()
    expect(page.locator(".claim-summary")).to_have_count(20)
    page.get_by_test_id("stSidebar").get_by_text("PDF 검토", exact=True).click()
    expect(pdf.locator('#point-filters [data-filter="all"]')).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(pdf.locator(".review-card")).to_have_count(27)
    expect(pdf.locator(".review-card.expanded")).to_have_count(0)
    check_summary(pdf)
    assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == original
    assert not errors, errors
    print(
        "PASS: 17/2/0/7; seven relied cards; hidden Wei/Oda/Biyikli retained in model; "
        "initial/reentry all; Claim and citation selection; R2 p.5; unchanged model."
    )
    browser.close()
