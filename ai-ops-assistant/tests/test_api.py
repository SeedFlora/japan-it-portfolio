from fastapi.testclient import TestClient

from ai_ops.api import create_app
from ai_ops.service import OpsAssistant


def test_api_and_grounded_answer():
    with TestClient(create_app(OpsAssistant())) as client:
        health = client.get("/health").json()
        assert health["documents"] == 6
        assert health["provider"] == "offline"
        response = client.post("/api/answer", json={"query": "backup restore", "language": "en"})
        assert response.status_code == 200
        answer = response.json()
        assert answer["mode"] == "offline_extractive"
        assert answer["evidence"]
        for evidence in answer["evidence"]:
            document = client.get("/api/documents/" + evidence["document_id"]).json()
            lines = document["text"].splitlines()
            assert evidence["quote"] == "\n".join(lines[evidence["line_start"] - 1 : evidence["line_end"]])
        assert len(client.get("/api/documents").json()) == 6


def test_api_rejects_bad_input_and_unknown_document():
    with TestClient(create_app(OpsAssistant())) as client:
        for body in ({"query": " "}, {"query": "backup", "language": "xx"},
                     {"query": "backup", "limit": 50}, {"query": "backup", "provider": "other"}):
            assert client.post("/api/answer", json=body).status_code == 422
        assert client.get("/api/documents/unknown_en").status_code == 404


def test_web_demo_and_openapi():
    with TestClient(create_app(OpsAssistant())) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "textContent=evidence.quote" in page.text  # source is rendered as text, not HTML
        assert "fictional" in page.text
        assert "/api/answer" in client.get("/openapi.json").json()["paths"]

