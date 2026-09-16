import pytest
from conftest import make_pdf
from fastapi.testclient import TestClient

from backend.main import app, get_settings
from backend.schemas import AnalysisResult


@pytest.fixture
def client(settings):
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json()["provider"] == "local"


def test_text_end_to_end(client, patent_text, oa_text):
    response = client.post(
        "/analyze/text", json={"patent_text": patent_text, "office_action_text": oa_text}
    )
    assert response.status_code == 200, response.text
    result = AnalysisResult.model_validate(response.json())
    assert len(result.rejections) == 3
    assert result.impacts[0].dependency_impacted_claims == [4, 5]


def test_upload_pdf_end_to_end(client):
    response = client.post(
        "/analyze/files",
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
    assert response.status_code == 200, response.text
    assert response.json()["impacts"][0]["dependency_impacted_claims"] == [2]


def test_missing_claim_propagation(client):
    response = client.post(
        "/analyze/text",
        json={
            "patent_text": "Claims\n1. A sensor.",
            "office_action_text": "Claims 1 and 99 are rejected under 35 USC 103 over Smith.",
        },
    )
    result = response.json()
    assert result["impacts"][0]["missing_claims"] == [99]
    assert any(n["id"] == "CL99" and n["status"] == "missing" for n in result["graph"]["nodes"])


def test_invalid_requests(client, patent_text):
    assert (
        client.post("/analyze/text", json={"patent_text": "", "office_action_text": ""}).status_code
        == 422
    )
    assert (
        client.post(
            "/analyze/text", json={"patent_text": "No claims", "office_action_text": "OA"}
        ).status_code
        == 422
    )
    response = client.post(
        "/analyze/files",
        files={"patent": ("p.txt", patent_text), "office_action": ("oa.pdf", b"corrupt")},
    )
    assert response.status_code == 422


def test_provider_error_status(client, settings, patent_text, oa_text):
    settings.llm_provider = "openai"
    settings.openai_api_key = ""
    settings.openai_model = ""
    response = client.post(
        "/analyze/text", json={"patent_text": patent_text, "office_action_text": oa_text}
    )
    assert response.status_code == 502


def test_upload_limit(client, settings):
    settings.max_upload_mb = 1
    response = client.post(
        "/analyze/files",
        files={"patent": ("p.txt", b"x" * (1024 * 1024 + 1)), "office_action": ("oa.txt", b"OA")},
    )
    assert response.status_code == 413
