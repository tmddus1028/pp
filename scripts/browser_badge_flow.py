"""All-or-none badge regression on the real patent's page 41."""

from pathlib import Path

from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]


def badge_snapshot(frame):
    return frame.locator("#paper").evaluate(
        """paper => {
          const page=paper.getBoundingClientRect();
          return [...paper.querySelectorAll('.claim-number-badge')].map(b => {
            const rect=b.getBoundingClientRect(), style=getComputedStyle(b);
            const box=JSON.parse(b.dataset.box);
            return {number:Number(b.textContent),hidden:b.hidden||style.display==='none'||style.visibility==='hidden',
              x:rect.left-page.left,y:rect.top-page.top,width:rect.width,height:rect.height,
              pageWidth:page.width,pageHeight:page.height,anchorX:box[0]*paper.clientWidth,
              anchorY:box[1]*paper.clientHeight,placement:b.dataset.placement};
          });
        }"""
    )


def check_all_badges(frame):
    expect(frame.locator(".claim-number-badge")).to_have_count(19)
    badges = badge_snapshot(frame)
    assert sorted(b["number"] for b in badges) == list(range(1, 20))
    assert not any(b["hidden"] for b in badges)
    assert len({(b["width"], b["height"]) for b in badges}) == 1
    for badge in badges:
        assert badge["x"] >= 0 and badge["y"] >= 0, badge
        assert badge["x"] + badge["width"] <= badge["pageWidth"] + 1, badge
        assert badge["y"] + badge["height"] <= badge["pageHeight"] + 1, badge
        assert abs(badge["y"] - max(1, badge["anchorY"] - 3)) < 1.1, badge
        assert abs(badge["x"] - badge["anchorX"]) <= badge["width"] + 6, badge
    expect(frame.locator(".claim-badge-layer")).to_have_css("z-index", "10")
    return badges


def check_claim_badges(page, frame):
    expect(frame.locator("#page-number")).to_have_value("41")
    original = frame.locator("#overlays").evaluate("() => JSON.stringify(model.annotations)")
    frame.get_by_role("button", name="너비 맞춤", exact=True).click()
    normal = check_all_badges(frame)
    assert all(b["placement"] != "inside" for b in normal), normal
    # At normal desktop fit width, no badge covers any known source text box.
    assert frame.locator("#paper").evaluate(
        """paper => {
          const p=paper.getBoundingClientRect();
          const source=model.annotations.filter(a=>a.document_id===state.document&&a.page===41).flatMap(a=>a.boxes);
          return [...paper.querySelectorAll('.claim-number-badge')].every(b=>{
            const r=b.getBoundingClientRect();
            return !source.some(s=>r.left-p.left<s[2]*paper.clientWidth-.5&&r.right-p.left>s[0]*paper.clientWidth+.5&&
              r.top-p.top<s[3]*paper.clientHeight-.5&&r.bottom-p.top>s[1]*paper.clientHeight+.5);
          });
        }"""
    )
    frame.get_by_role("button", name="Claim 14 · 직접 지적", exact=True).click()
    expect(frame.locator('.annotation.region.selected[data-item-id="claim-14"]')).to_have_count(1)
    expect(frame.locator('.claim-number-badge.selected[data-item-id="claim-14"]')).to_have_count(1)
    expect(frame.locator('.annotation.region.selected[data-item-id="claim-14"]')).to_have_css(
        "filter", "none"
    )
    page.screenshot(path=str(ROOT / "data/outputs/pdf-review-badges-page41.png"), full_page=True)
    for button in ["확대", "확대", "축소", "페이지 맞춤", "너비 맞춤"]:
        frame.get_by_role("button", name=button, exact=True).click()
        check_all_badges(frame)
    # Scroll moves page, borders, and badges together without recalculating Evidence.
    before = badge_snapshot(frame)
    frame.locator("#pdf-scroll").evaluate(
        "scroll => scroll.scrollTo({top:scroll.scrollHeight,left:30,behavior:'instant'})"
    )
    after = check_all_badges(frame)
    assert [(b["x"], b["y"]) for b in before] == [(b["x"], b["y"]) for b in after]
    frame.locator('.annotation.region[data-item-id="claim-19"]').click()
    expect(frame.locator(".review-card.active")).to_have_attribute("data-review-id", "claim-19")
    # Exercise the minimum zoom, then restore fit width. Badges must never disappear.
    for _ in range(4):
        frame.get_by_role("button", name="축소", exact=True).click()
    small = check_all_badges(frame)
    assert any(b["placement"] == "inside" for b in small)
    frame.get_by_role("button", name="너비 맞춤", exact=True).click()
    check_all_badges(frame)
    assert (
        frame.locator("#overlays").evaluate("() => JSON.stringify(model.annotations)") == original
    )
    print(
        "Badges passed: all 19 Claims on page 41, both columns, fit/zoom/scroll, no text overlap at fit width, and unchanged source boxes."
    )
