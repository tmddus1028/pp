import psycopg
import pytest
from conftest import make_pdf
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


def test_case_lifecycle_with_pdfs(client):
    created = client.post(
        "/cases",
        data={"title": "센서 사건"},
        files={
            "patent": (
                "patent.pdf",
                make_pdf(
                    [
                        "Claims\n1. A sensor system comprising a processor.\n2. The system of claim 1."
                    ]
                ),
                "application/pdf",
            ),
            "office_action": (
                "oa.pdf",
                make_pdf(["Claim 1 is rejected under 35 USC 103 over Smith."]),
                "application/pdf",
            ),
        },
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["id"]
    try:
        listed = next(c for c in client.get("/cases").json() if c["id"] == case_id)
        assert listed["title"] == "센서 사건" and listed["status"] == "open"
        assert listed["direct_count"] == 1

        detail = client.get(f"/cases/{case_id}").json()
        assert [row["claim_number"] for row in detail["claim_rows"]] == [1, 2]
        claim = next(a for a in detail["review"]["annotations"] if a["claim_number"] == 1)
        assert claim["boxes"], "coordinates are resolved when the case is saved"

        patent = next(d for d in detail["result"]["documents"] if d["kind"] == "patent")
        base = f"/cases/{case_id}/files/{patent['document_id']}"
        assert client.get(base).content.startswith(b"%PDF")
        page = client.get(base + "/pages/1")
        assert page.headers["content-type"] == "image/png" and page.content[:4] == b"\x89PNG"
        assert client.get(base + "/pages/1/search", params={"q": "sensor"}).json()
        assert client.get(base + "/pages/9").status_code == 422

        compared = client.get(f"/cases/{case_id}/comparison", params={"claim": 2}).json()
        assert compared["status"] == "종속 영향"

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


def test_demo_cases_for_both_jurisdictions(client):
    for jurisdiction in ("US", "KR"):
        case_id = client.post("/cases/demo", params={"jurisdiction": jurisdiction}).json()["id"]
        try:
            detail = client.get(f"/cases/{case_id}").json()
            assert detail["case"]["jurisdiction"] == jurisdiction
            assert bool(detail["terms"]) == (jurisdiction == "KR")
            assert detail["relationship"]["nodes"]
        finally:
            client.delete(f"/cases/{case_id}")


def test_database_down_is_a_clear_503(client, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none?connect_timeout=2")
    response = client.get("/cases")
    assert response.status_code == 503 and "docker compose" in response.json()["detail"]
