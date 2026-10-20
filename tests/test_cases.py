from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from backend import store
from backend.main import app, get_settings

pytestmark = pytest.mark.postgres


@pytest.fixture
def client(settings):
    try:
        store.connect().close()
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL unreachable; run docker compose up -d")
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


KR = Path(__file__).resolve().parents[1] / "korean_prototype/data/kr_1020190000844"


def test_case_lifecycle_with_pdfs(client):
    created = client.post(
        "/cases",
        data={"title": "전자쿠폰 사건"},
        files={
            "patent": (
                "KR20190025857A.pdf",
                (KR / "KR20190025857A.pdf").read_bytes(),
                "application/pdf",
            ),
            "office_action": (
                "office_action_20190409.xml",
                (KR / "office_action_20190409.xml").read_bytes(),
                "application/xml",
            ),
        },
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    try:
        listed = next(c for c in client.get("/cases").json() if c["id"] == case_id)
        assert listed["title"] == "전자쿠폰 사건" and listed["status"] == "open"
        assert listed["jurisdiction"] == "KR" and listed["direct_count"] == 1

        detail = client.get(f"/cases/{case_id}").json()
        assert [row["claim_number"] for row in detail["claim_rows"]] == [1]
        claim = next(a for a in detail["review"]["annotations"] if a["claim_number"] == 1)
        assert claim["boxes"], "coordinates are resolved when the case is saved"

        patent = next(d for d in detail["result"]["documents"] if d["kind"] == "patent")
        base = f"/cases/{case_id}/files/{patent['document_id']}"
        assert client.get(base).content.startswith(b"%PDF")
        page = client.get(base + "/pages/1")
        assert page.headers["content-type"] == "image/png" and page.content[:4] == b"\x89PNG"
        assert client.get(base + "/pages/3/search", params={"q": "전자쿠폰"}).json()
        assert client.get(base + "/pages/99").status_code == 422

        updated = client.patch(
            f"/cases/{case_id}", json={"status": "in_progress", "deadline": "2026-12-01"}
        ).json()
        assert updated["status"] == "in_progress" and updated["deadline"] == "2026-12-01"
        assert client.patch(f"/cases/{case_id}", json={"status": "bogus"}).status_code == 422
        cleared = client.patch(f"/cases/{case_id}", json={"deadline": None}).json()
        assert cleared["deadline"] is None and cleared["status"] == "in_progress"
        kept = client.patch(f"/cases/{case_id}", json={"status": None}).json()
        assert kept["status"] == "in_progress"
    finally:
        assert client.delete(f"/cases/{case_id}").status_code == 204
    assert client.get(f"/cases/{case_id}").status_code == 404


def test_cases_first_then_selection_record_then_draft(client, monkeypatch):
    from unittest.mock import Mock

    from backend.config import Settings
    from backend.improvements.opinion import HEADINGS, OpinionDraft, OpinionSection
    from backend.precedents import repository

    created = client.post(
        "/cases",
        files={
            "patent": ("KR20190025857A.pdf", (KR / "KR20190025857A.pdf").read_bytes()),
            "office_action": (
                "office_action_20190409.xml",
                (KR / "office_action_20190409.xml").read_bytes(),
            ),
        },
    )
    case_id = created.json()["id"]
    try:
        detail = client.get(f"/cases/{case_id}").json()
        claim = detail["result"]["patent"]["claims"][0]["text"]
        # 1) cases are offered before any choice
        cases = client.get(
            "/precedents/similar",
            params={"statute": "특허법 제29조제2항", "q": claim, "exclude": "1020190000844"},
        ).json()
        assert cases
        # 2) the attorney's choice is validated and saved as a new version each time
        choice = {
            "claim_number": 1,
            "rejection_id": "R1",
            "precedent_ids": [cases[0]["case_id"]],
            "direction": "반박",
            "emphasize": "발행 형식 결정 구성",
            "confirmed_by": "김변리사",
        }
        bad = client.post(f"/cases/{case_id}/selections", json={**choice, "claim_number": 9})
        assert bad.status_code == 422
        first = client.post(f"/cases/{case_id}/selections", json=choice).json()
        second = client.post(
            f"/cases/{case_id}/selections", json={**choice, "direction": "보류"}
        ).json()
        assert (first["version"], second["version"]) == (1, 2)
        assert second["record"]["direction"] == "보류" and second["confirmed_by"] == "김변리사"
        listed = client.get(f"/cases/{case_id}/selections").json()
        assert [s["version"] for s in listed] == [2, 1]
        # 3) the draft is written from a confirmed version; 보류 writes nothing
        held = client.post(f"/cases/{case_id}/drafts", json={"selection_id": second["id"]})
        assert held.status_code == 422
        from backend.improvements.models import ImprovementRequest
        from backend.improvements.retrieval import retrieved_context
        from backend.schemas import AnalysisResult

        result = AnalysisResult.model_validate(detail["result"])
        ctx, *_ = retrieved_context(
            ImprovementRequest(analysis=result, claim_number=1, rejection_id="R1"),
            [("selected_claim", claim)],
        )
        oa = next(s for s in ctx["sources"] if s["kind"] == "office_action")
        quote = oa["evidence"]["text"][:30]
        draft = OpinionDraft(
            amended_claim=None,
            sections=[
                OpinionSection(
                    heading=h,
                    paragraphs=[
                        {
                            "text": f"{h} 문단.",
                            "evidence_ids": [oa["evidence_id"]],
                            "grounding": [{"evidence_id": oa["evidence_id"], "quote": quote}],
                        }
                    ],
                )
                for h in HEADINGS
            ],
            cautions=[],
        )
        fake = Mock()
        fake.complete.return_value = draft
        monkeypatch.setattr("backend.improvements.opinion.get_provider", lambda *_: fake)
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            llm_provider="local",
            improvement_provider="local_ollama",
            local_llm_model="qwen3:14b",
        )
        made = client.post(f"/cases/{case_id}/drafts", json={"selection_id": first["id"]})
        assert made.status_code == 201, made.text
        record = made.json()
        assert record["selection_id"] == first["id"] and record["model"] == "qwen3:14b"
        context = fake.complete.call_args.args[0]
        assert context["attorney_selection"]["direction"] == "반박"
        assert context["reference_cases"][0]["case_id"] == cases[0]["case_id"]
        assert client.get(f"/cases/{case_id}/drafts").json()[0]["id"] == record["id"]
        assert repository.get(cases[0]["case_id"])
    finally:
        client.delete(f"/cases/{case_id}")


def test_korean_demo_case(client):
    case_id = client.post("/cases/demo").json()["id"]
    try:
        detail = client.get(f"/cases/{case_id}").json()
        assert detail["case"]["jurisdiction"] == "KR"
        assert detail["terms"] and detail["relationship"]["nodes"]
    finally:
        client.delete(f"/cases/{case_id}")


def test_database_down_is_a_clear_503(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none?connect_timeout=2")
    response = client.get("/cases")
    assert response.status_code == 503 and "docker compose" in response.json()["detail"]
