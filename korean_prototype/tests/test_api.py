import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from kr_review.api import app
from kr_review.models import ReviewError
from kr_review.sample import DATA, sample_inputs

client = TestClient(app)


def test_health_and_openapi_are_separate_korean_api():
    assert client.get("/health").json()["jurisdiction"] == "KR"
    schema = client.get("/openapi.json").json()
    assert "/analyze" in schema["paths"]
    assert "/review" in schema["paths"]


def test_sample_hashes_and_real_multipart_match_demo():
    payload = sample_inputs()
    response = client.post("/demo/analyze")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["direct_claims"] == [1]
    assert result["dependency_claims"] == []
    assert [c["number"] for c in result["claims"]] == [1]
    assert len(result["rejections"]) == 1
    assert result["rejections"][0]["statute"] == "특허법 제29조제2항"
    assert {c["publication_number"] for c in result["citations"]} == {
        "KR20150096573A",
        "KR20150090348A",
        "KR20150093093A",
    }
    assert all(c["document_id"] for c in result["citations"])
    uploads = [
        ("patent", (payload["patent_filename"], payload["patent_data"], "application/pdf")),
        ("office_action", (payload["oa_filename"], payload["oa_data"], "application/xml")),
        *[("references", (name, data, "application/pdf")) for name, data in payload["references"]],
    ]
    uploaded = client.post("/analyze", files=uploads)
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json() == result
    docs = {d["document_id"]: d for d in result["documents"]}
    for item in result["claims"] + result["rejections"] + result["citations"]:
        e = item["evidence"]
        d = docs[e["document_id"]]
        assert d["text"][e["start"] : e["end"]] == e["text"]
        if d["kind"] == "office_action":
            assert e["page_numbers"] == []
            assert e["xml_path"]


def test_bad_and_missing_uploads_are_user_errors():
    assert client.post("/analyze").status_code == 422
    payload = sample_inputs()
    for data in (b"", b"not xml"):
        response = client.post(
            "/analyze",
            files={
                "patent": (payload["patent_filename"], payload["patent_data"]),
                "office_action": ("bad.xml", data),
            },
        )
        assert response.status_code == 422


def test_sample_tampering_is_detected(tmp_path, monkeypatch):
    from kr_review import sample

    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {"filename": "modified.pdf", "sha256": hashlib.sha256(b"original").hexdigest()}
                ]
            }
        )
    )
    (tmp_path / "modified.pdf").write_bytes(b"modified")
    monkeypatch.setattr(sample, "DATA", tmp_path)
    with pytest.raises(ReviewError, match="해시"):
        sample.sample_inputs()


def test_sample_contains_publication_not_later_grant():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 5
    assert not any("KR102136729B1" in f["filename"] for f in manifest["files"])


def test_review_endpoint_returns_clear_configuration_error(monkeypatch, tmp_path):
    from kr_review import review

    # Explicitly no external calls, regardless of developer environment settings.
    monkeypatch.setattr(review, "ENV_PATH", tmp_path / "missing.env")
    for name in ("ENDPOINT", "API_KEY", "DEPLOYMENT"):
        monkeypatch.delenv("KR_AZURE_OPENAI_" + name, raising=False)
    from tests.test_ui import analysis_result

    response = client.post(
        "/review", json={"analysis": analysis_result().model_dump(), "claim_number": 1}
    )
    assert response.status_code == 422
    assert "KR_AZURE_OPENAI" in response.json()["detail"]
