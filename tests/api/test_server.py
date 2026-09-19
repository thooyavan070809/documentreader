"""HTTP contract tests for the Vercel FastAPI entrypoint."""

from fastapi.testclient import TestClient

from server import PUBLIC_UPLOAD_LIMIT_BYTES, app

client = TestClient(app)


def test_public_frontend_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Enterprise Knowledge" in response.text
    assert "Upload source documents" in response.text
    assert "Ask with confidence" in response.text


def test_health_never_returns_secret_values() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "status",
        "groq_configured",
        "qdrant_configured",
        "embedding_model",
    }


def test_public_upload_limit_is_enforced_before_ingestion() -> None:
    response = client.post(
        "/api/documents",
        files={
            "file": (
                "oversized.txt",
                b"x" * (PUBLIC_UPLOAD_LIMIT_BYTES + 1),
                "text/plain",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Public web uploads are limited to 4 MB."
