from pydantic import SecretStr

from app.config import Settings


def test_placeholder_credentials_are_not_considered_configured() -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key=SecretStr("replace-with-your-groq-api-key"),
        qdrant_url="https://replace-with-your-cluster-url",
        qdrant_api_key=SecretStr("replace-with-your-qdrant-api-key"),
    )

    assert settings.groq_configured is False
    assert settings.qdrant_configured is False


def test_real_credentials_are_redacted_from_summary() -> None:
    settings = Settings(
        _env_file=None,
        groq_api_key=SecretStr("gsk_test_value"),
        qdrant_url="https://example.cloud.qdrant.io:6333/",
        qdrant_api_key=SecretStr("qdrant-test-value"),
    )

    summary = settings.safe_summary()

    assert settings.groq_configured is True
    assert settings.qdrant_configured is True
    assert settings.qdrant_url == "https://example.cloud.qdrant.io:6333"
    assert "gsk_test_value" not in str(summary)
    assert "qdrant-test-value" not in str(summary)
