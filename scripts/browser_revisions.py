"""Isolated browser workflow with an explicitly MOCKED Ollama server; no real inference."""

import json
import os
import subprocess
import time
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/outputs/revisions"


def wait(url):
    for _ in range(90):
        try:
            if httpx.get(url, timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    raise RuntimeError("Test service failed to start: " + url)


def counts():
    return httpx.get("http://127.0.0.1:11435", timeout=3).json()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for port in (11435, 18000, 18501):
        import socket

        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"Test port already in use: {port}")
    env = {
        **os.environ,
        "LLM_PROVIDER": "local",
        "IMPROVEMENT_PROVIDER": "local_ollama",
        "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11435",
        "LOCAL_LLM_MODEL": "TEST-MOCK-NOT-A-REAL-MODEL",
        "LOCAL_EMBEDDING_MODEL": "",
        "API_BASE_URL": "http://127.0.0.1:18000",
    }
    python = str(ROOT / ".venv/Scripts/python.exe")
    processes, logs = [], []
    try:
        for name, args in [
            ("mock", ["scripts/revision_mock_server.py"]),
            (
                "api",
                ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "18000"],
            ),
            (
                "web",
                [
                    "-m",
                    "streamlit",
                    "run",
                    "frontend/app.py",
                    "--server.address",
                    "127.0.0.1",
                    "--server.port",
                    "18501",
                    "--server.headless",
                    "true",
                ],
            ),
        ]:
            log = (OUT / (name + ".log")).open("w", encoding="utf-8")
            logs.append(log)
            processes.append(
                subprocess.Popen(
                    [python, *args],
                    cwd=ROOT,
                    env=env,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            )
        for url in [
            "http://127.0.0.1:11435",
            "http://127.0.0.1:18000/health",
            "http://127.0.0.1:18501/_stcore/health",
        ]:
            wait(url)
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto("http://127.0.0.1:18501", wait_until="networkidle")
            inputs = page.locator('input[type="file"]')
            for i, file in enumerate(
                [
                    ROOT / "tests/fixtures/patent_headers/us20150283132a1_pages_40_41.pdf",
                    ROOT / "tests/fixtures/pdf_review/office_action_reconstructed.pdf",
                ]
            ):
                inputs.nth(i).set_input_files(file)
                expect(
                    page.get_by_role("button", name="Remove " + file.name, exact=True)
                ).to_be_visible()
            page.get_by_role("button", name="분석 시작", exact=True).click()
            pdf = page.frame_locator('iframe[title*="patent_pdf_review"]')
            expect(pdf.locator("#page-image")).to_be_visible(timeout=90000)
            pdf.locator("#scope").select_option("R1")
            pdf.get_by_role("button", name="Claim 1 · 직접 지적", exact=True).click()
            before = pdf.locator("#workspace").evaluate("() => JSON.stringify(model)")
            state = pdf.locator("#workspace").evaluate("() => JSON.stringify(state)")
            original = pdf.locator("#workspace").evaluate("() => itemById('claim-1').evidence.text")
            pdf.get_by_role("button", name="개선 방안 보기", exact=True).click()
            expect(pdf.get_by_role("button", name="AI 개선안 생성", exact=True)).to_be_visible()
            assert counts() == {"improvement": 0, "revision": 0}
            pdf.get_by_role("button", name="AI 개선안 생성", exact=True).click()
            expect(pdf.locator(".improvement-detail")).to_contain_text(
                "TEST MOCK ONLY", timeout=30000
            )
            assert counts()["improvement"] == 1
            pdf.get_by_role("button", name="AI 개선안 생성", exact=True).click()
            page.wait_for_timeout(500)
            assert counts()["improvement"] == 1
            for index in (1, 2, 3):
                text = original + f"; revision review test condition {index}."
                pdf.get_by_role("textbox", name="수정 Claim", exact=True).fill(text)
                pdf.get_by_role("button", name="수정본 검증", exact=True).click()
                expect(pdf.locator(".revision-result")).to_have_count(index, timeout=30000)
            assert counts()["revision"] == 3
            pdf.get_by_role("button", name="수정본 검증", exact=True).click()
            page.wait_for_timeout(500)
            assert counts()["revision"] == 3
            assert pdf.locator("#workspace").evaluate("() => JSON.stringify(model)") == before
            assert pdf.locator("#workspace").evaluate("() => JSON.stringify(state)") == state
            expect(pdf.locator(".revision-result").first).to_contain_text("신규사항 가능성")
            for width in (1920, 1440, 1280, 1024):
                page.set_viewport_size({"width": width, "height": 1000})
                paragraph = pdf.locator(".revision-result .readable-text").first
                expect(paragraph).to_be_visible()
                assert paragraph.evaluate("n => n.getBoundingClientRect().width") > 200
            page.set_viewport_size({"width": 1440, "height": 1000})
            pdf.locator(".revision-result").first.evaluate("n => n.scrollIntoView({block:'start'})")
            page.screenshot(path=str(OUT / "mock-revision.png"), full_page=True)
            pdf.locator("#scope").select_option("R2")
            pdf.get_by_role("button", name="개선 방안 보기", exact=True).click()
            expect(pdf.locator(".revision-result")).to_have_count(0)
            expect(pdf.get_by_role("textbox", name="수정 Claim", exact=True)).to_have_value("")
            pdf.locator("#scope").select_option("R1")
            expect(pdf.locator(".revision-result")).to_have_count(3)
            sidebar = page.get_by_test_id("stSidebar")
            sidebar.get_by_text("청구항 분석", exact=True).click()
            page.get_by_text("Claim 1 상세 보기", exact=True).click()
            row = page.locator(".st-key-claim-row-1")
            row.get_by_role("button", name="개선 방안 보기", exact=True).click()
            row.get_by_role("textbox", name="수정 Claim", exact=True).fill(
                original + "; user revision."
            )
            row.get_by_role("button", name="수정본 검증", exact=True).click()
            expect(row.locator(".revision-result")).to_have_count(1, timeout=30000)
            row.get_by_role("button", name="PDF에서 보기", exact=True).click()
            expect(pdf.locator(".review-card.active")).to_have_attribute(
                "data-review-id", "claim-1"
            )
            sidebar.get_by_text("문서 업로드", exact=True).click()
            page.get_by_text("한국 특허", exact=True).click()
            expect(page.get_by_text("의견제출통지서 XML / PDF", exact=True)).to_be_visible()
            data = ROOT / "korean_prototype/data/kr_1020190000844"
            for i, name in enumerate(["KR20190025857A.pdf", "office_action_20190409.xml"]):
                page.locator('input[type="file"]').nth(i).set_input_files(data / name)
                expect(
                    page.get_by_role("button", name="Remove " + name, exact=True)
                ).to_be_visible()
            page.get_by_text("인용발명 원문 (선택)", exact=True).click()
            page.locator('input[type="file"]').nth(2).set_input_files(
                list(data.glob("KR2015*.pdf"))
            )
            page.get_by_role("button", name="분석 시작", exact=True).click()
            expect(pdf.locator("#page-image")).to_be_visible(timeout=60000)
            pdf.get_by_role("button", name="청구항 1 · 직접 지적", exact=True).click()
            pdf.get_by_role("button", name="개선 방안 보기", exact=True).click()
            expect(pdf.get_by_role("textbox", name="수정 Claim", exact=True)).to_have_value("")
            expect(pdf.locator(".revision-result")).to_have_count(0)
            assert pdf.locator("#workspace").evaluate(
                "() => model.items.filter(i=>i.kind==='citation').every(i=>i.source_links.length>0)"
            )
            pdf.get_by_role("button", name="AI 개선안 생성", exact=True).click()
            expect(pdf.locator(".improvement-detail")).to_contain_text(
                "TEST MOCK ONLY", timeout=30000
            )
            claim = pdf.locator("#workspace").evaluate("() => itemById('claim-1').evidence.text")
            pdf.get_by_role("textbox", name="수정 Claim", exact=True).fill(claim)
            pdf.get_by_role("button", name="수정본 검증", exact=True).click()
            expect(pdf.locator(".revision-result")).to_have_count(1, timeout=30000)
            expect(pdf.locator("#summary strong")).to_have_text(["1", "0", "0", "3"])
            # Explicit provider failure is isolated from the patent viewer and prior revisions.
            processes[0].terminate()
            processes[0].wait(timeout=10)
            pdf.get_by_role("textbox", name="수정 Claim", exact=True).fill(
                claim + "; additional condition."
            )
            pdf.get_by_role("button", name="수정본 검증", exact=True).click()
            expect(pdf.locator(".improvement-detail")).to_contain_text(
                "로컬 LLM에 연결할 수 없습니다", timeout=30000
            )
            expect(pdf.locator(".revision-result")).to_have_count(1)
            expect(pdf.locator("#page-image")).to_be_visible()
            assert not errors, errors
            (OUT / "browser.json").write_text(
                json.dumps(
                    {
                        "result": "PASS",
                        "real_llm": False,
                        "provider": "HTTP Ollama MOCK",
                        "checks": [
                            "no automatic calls",
                            "explicit generation",
                            "three revisions",
                            "cache",
                            "scope isolation",
                            "US/KR reset",
                            "Claim Analysis",
                            "PDF selection immutable",
                            "responsive width",
                            "provider failure retains analysis",
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            browser.close()
            print(
                "PASS: revision workflow in browser, HTTP Ollama MOCK only; no actual LLM inference.",
                flush=True,
            )
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
