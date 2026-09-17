"""Exercise the real downloaded files in the unchanged integrated UI."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/downloads/kr_review_package"
OUT = DATA / "validation"


def main():
    cases = json.loads((OUT / "paired_cases.json").read_text(encoding="utf-8"))
    observations = []
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="msedge", headless=True)
        for case in cases:
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:8501", wait_until="networkidle")
            page.get_by_text("한국 특허", exact=True).click()
            expect(page.get_by_text("의견제출통지서 XML", exact=True)).to_be_visible()
            patent, oa = DATA / case["patent_file"], DATA / case["oa_xml"]
            inputs = page.locator('input[type="file"]')
            inputs.nth(0).set_input_files(patent)
            expect(
                page.get_by_role("button", name="Remove " + patent.name, exact=True)
            ).to_be_visible()
            inputs.nth(1).set_input_files(oa)
            expect(page.get_by_role("button", name="Remove " + oa.name, exact=True)).to_be_visible()
            page.get_by_role("button", name="분석 시작", exact=True).click()
            if case["http_status"] != 200:
                expect(page.get_by_test_id("stAlert")).to_contain_text(case["error"], timeout=30000)
                assert page.locator('iframe[title*="patent_pdf_review"]').count() == 0
                page.screenshot(
                    path=str(OUT / (case["application"] + "_error.png")), full_page=True
                )
            else:
                expect(page.get_by_role("heading", name="PDF 검토", exact=True)).to_be_visible(
                    timeout=60000
                )
                pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
                expect(pdf.locator("#page-image")).to_be_visible(timeout=30000)
                expect(pdf.locator("#summary strong")).to_have_text(
                    [
                        str(len(case["direct"])),
                        "0",
                        "0",
                        str(len(case["citations"])),
                    ]
                )
                pdf.get_by_role("button", name="청구항 1 · 직접 지적", exact=True).click()
                pdf.locator("#rejection-links button").first.click()
                expect(pdf.locator("#text-page")).to_contain_text(case["statutes"][0])
                expect(
                    pdf.locator('.review-card.expanded[data-review-id="claim-1"]')
                ).to_have_count(1)
                page.screenshot(path=str(OUT / (case["application"] + "_oa.png")), full_page=True)
                for name, suffix in [
                    ("청구항 분석", "claims"),
                    ("관계 지도", "graph"),
                    ("근거 비교", "comparison"),
                ]:
                    page.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
                    expect(page.get_by_role("heading", name=name, exact=True)).to_be_visible()
                    if suffix == "graph":
                        frame = page.frame_locator('iframe[title*="patent_relationship_map"]')
                        expect(frame.locator('.node[data-node-id="R1"]')).to_be_visible()
                    elif suffix == "comparison":
                        expect(page.locator(".comparison-rejection")).to_contain_text(
                            case["statutes"][0]
                        )
                    else:
                        expect(page.get_by_test_id("stMetricValue").first).to_have_text(
                            str(case["claim_count"])
                        )
                    page.screenshot(
                        path=str(OUT / (case["application"] + "_" + suffix + ".png")),
                        full_page=True,
                    )
            assert not errors, errors
            observations.append(
                {
                    "application": case["application"],
                    "browser_flow": "PASS",
                    "analysis_quality": case["status"],
                    "page_errors": errors,
                }
            )
            print(
                case["application"], "browser flow verified; analysis:", case["status"], flush=True
            )
            page.close()
        browser.close()
    (OUT / "browser_checks.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
