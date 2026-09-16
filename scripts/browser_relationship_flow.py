"""Relationship-map checks reused by the full real-PDF browser regression."""

from pathlib import Path

from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]


def check_relationship_flow(page, pdf):
    pdf.get_by_role("button", name="Claim 14 · 직접 지적", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("41")
    pdf.get_by_role("button", name="상위 Claim 1", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("40")
    expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-1")
    pdf.get_by_role("button", name="Claim 14 · 직접 지적", exact=True).click()
    pdf.get_by_role("button", name="종속 Claim 15", exact=True).click()
    expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-15")
    pdf.get_by_role("button", name="Claim 14 · 직접 지적", exact=True).click()
    pdf.get_by_role("button", name="Lombardi et al", exact=True).click()
    expect(pdf.locator(".review-card.active")).to_contain_text("Patent · 특허 문헌")
    expect(pdf.locator(".review-card.active")).to_contain_text("WO2009/013126 A1")
    expect(pdf.locator(".review-card.active")).to_contain_text(
        "관련 Claim · 같은 거절에 연결된 청구항"
    )
    expect(
        pdf.locator(".review-card.active").get_by_role("button", name="Claim 19", exact=True)
    ).to_be_visible()
    pdf.get_by_role("button", name="전체 관계 지도 보기", exact=True).click()
    expect(page.get_by_role("heading", name="관계 지도", exact=True)).to_be_visible(timeout=15000)
    graph = page.frame_locator('iframe[title*="patent_relationship_map"]')
    expect(graph.locator(".node.citation")).to_have_count(5)
    expect(graph.locator(".node")).to_have_count(
        9
    )  # Root, 2 rejections, primary Claim 1, 5 citations.
    expect(graph.locator(".edge.depends_on")).to_have_count(0)
    expect(graph.locator("#map-detail")).to_contain_text("Lombardi")
    graph.get_by_role("combobox", name="지도 Claim 찾기").select_option("CL14")
    expect(graph.locator('.node.selected[data-node-id="CL14"]')).to_be_visible()
    expect(graph.locator('.node[data-node-id="CL1"]')).to_be_visible()
    expect(graph.locator('.node[data-node-id="CL15"]')).to_be_visible()
    expect(graph.locator(".edge.depends_on")).to_have_count(2)
    expect(graph.locator("#map-detail")).to_contain_text("35 USC 112")
    expect(graph.locator("#map-detail")).to_contain_text("35 USC 103(a)")
    expect(graph.locator("#map-detail")).to_contain_text("관련 인용문헌 · 5개")
    graph.locator('.node[data-node-id="CL14"]').hover()
    touching = graph.locator(".edge.highlight").evaluate_all(
        "nodes => nodes.every(n => n.dataset.source === 'CL14' || n.dataset.target === 'CL14')"
    )
    assert touching, "Hover should highlight only incident edges."
    expect(graph.locator(".node.citation.dimmed")).to_have_count(5)
    graph.get_by_role("heading", name="원문을 연결하는 관계").hover()
    expect(graph.locator(".node.citation.dimmed")).to_have_count(0)
    page.screenshot(path=str(ROOT / "data/outputs/relationship-map-claim14.png"), full_page=True)
    graph.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(timeout=15000)
    expect(pdf.locator("#page-number")).to_have_value("41")
    expect(pdf.locator('.annotation.region.selected[data-item-id="claim-14"]')).to_have_count(1)
    expect(pdf.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-14")
    pdf.get_by_role("button", name="전체 관계 지도 보기", exact=True).click()
    expect(graph.locator('.node.selected[data-node-id="CL14"]')).to_be_visible(timeout=15000)
    graph.get_by_role("button", name="인용 문헌", exact=True).click()
    expect(graph.locator(".node.citation")).to_have_count(5)
    expect(graph.locator('.node[data-node-id^="CL"]')).to_have_count(0)
    graph.get_by_role("checkbox", name="인용문헌 표시", exact=True).uncheck()
    expect(graph.locator(".node.citation")).to_have_count(0)
    graph.get_by_role("checkbox", name="인용문헌 표시", exact=True).check()
    graph.locator(".node.citation").filter(has_text="Greco").click()
    expect(graph.locator("#map-detail")).to_contain_text("NPL · 비특허 문헌")
    expect(graph.locator("#map-detail")).to_contain_text("Molecular and Cellular Endocrinology")
    expect(graph.locator("#map-detail")).to_contain_text("2010")
    expect(
        graph.locator("#map-detail").get_by_role("button", name="Claim 19", exact=True)
    ).to_be_visible()
    page.screenshot(path=str(ROOT / "data/outputs/relationship-map-citation.png"), full_page=True)
    graph.get_by_role("button", name="Office Action 근거 보기", exact=True).click()
    expect(pdf.locator(".review-card.active")).to_contain_text("Greco", timeout=15000)
    expect(pdf.locator(".annotation.citation.selected").first).to_be_visible(timeout=15000)
    expect(pdf.locator("#document")).to_contain_text("Office Action")
    pdf.get_by_role("button", name="전체 관계 지도 보기", exact=True).click()
    graph.get_by_role("button", name="기본 보기", exact=True).click()
    expect(graph.locator(".node")).to_have_count(9)
    graph.get_by_role("button", name="거절 사유", exact=True).click()
    expect(graph.locator(".node")).to_have_count(3)
    graph.get_by_role("button", name="Claim", exact=True).click()
    graph.get_by_role("button", name="R2 · 청구항 19개 펼치기", exact=True).click()
    expect(graph.locator('.node[data-node-id^="CL"]')).to_have_count(19)
    graph.get_by_role("button", name="R2 · 청구항 19개 접기", exact=True).click()
    expect(graph.locator('.node[data-node-id^="CL"]')).to_have_count(1)
    graph.get_by_role("button", name="종속 관계", exact=True).click()
    graph.get_by_role("combobox", name="지도 Claim 찾기").select_option("CL14")
    expect(graph.locator('.node[data-node-id^="CL"]')).to_have_count(3)
    graph.get_by_role("checkbox", name="종속관계 표시", exact=True).uncheck()
    expect(graph.locator(".edge.depends_on")).to_have_count(0)
    graph.get_by_role("combobox", name="지도 거절 범위").select_option("R1")
    graph.get_by_role("combobox", name="지도 Claim 찾기").select_option("CL2")
    expect(graph.locator('.node.impacted[data-node-id="CL2"]')).to_be_visible()
    graph.get_by_role("checkbox", name="직접 지적만", exact=True).check()
    expect(graph.locator('.node[data-node-id="CL2"]')).to_have_count(0)
    graph.get_by_role("checkbox", name="직접 지적만", exact=True).uncheck()
    expect(graph.locator('.node.impacted[data-node-id="CL2"]')).to_be_visible()
    graph.get_by_role("button", name="PDF에서 보기", exact=True).click()
    expect(pdf.get_by_role("combobox", name="거절 사유 필터")).to_have_value("R1", timeout=15000)
    expect(pdf.locator('.annotation.dependency.selected[data-item-id="claim-2"]')).to_have_count(1)
    # Restore the original full-PDF regression's starting state.
    pdf.get_by_role("combobox", name="거절 사유 필터").select_option("all")
    pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
    expect(pdf.locator("#page-number")).to_have_value("40")
    print(
        "Relationship map passed: real Claim 1/14/15, 5 citations, collapse, hover/focus, every filter, and scoped PDF round trips."
    )
