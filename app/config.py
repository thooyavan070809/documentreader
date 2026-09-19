"""Typed application configuration with safe credential readiness checks."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_FRAGMENTS = ("replace-with", "your-", "<", ">")


def _has_real_value(value: SecretStr | str | None) -> bool:
    raw = value.get_secret_value() if isinstance(value, SecretStr) else value or ""
    normalized = raw.strip().lower()
    return bool(normalized) and not any(
        fragment in normalized for fragment in _PLACEHOLDER_FRAGMENTS
    )


class Settings(BaseSettings):
    """Environment-backed settings used by both Streamlit and service modules."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: SecretStr = SecretStr("")

    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"

    qdrant_url: str = ""
    qdrant_api_key: SecretStr = SecretStr("")
    qdrant_collection: str = "enterprise_knowledge"

    embedding_model: str = "BAAI/bge-base-en-v1.5"
    embedding_device: str = "cpu"

    metadata_database_url: str = "sqlite:///./data/app.db"
    upload_root: Path = Path("./data/uploads")

    max_upload_mb: int = Field(default=50, ge=1, le=500)
    chunk_size_tokens: int = Field(default=700, ge=100, le=4096)
    chunk_overlap_tokens: int = Field(default=100, ge=0, le=2048)
    dense_candidate_limit: int = Field(default=20, ge=1, le=200)
    sparse_candidate_limit: int = Field(default=20, ge=1, le=200)
    final_context_limit: int = Field(default=8, ge=1, le=50)
    min_retrieval_score: float = Field(default=0.35, ge=0.0, le=1.0)
    log_level: str = "INFO"

    @field_validator("qdrant_url")
    @classmethod
    def normalize_qdrant_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("chunk_overlap_tokens")
    @classmethod
    def validate_overlap(cls, value: int, info: Any) -> int:
        chunk_size = info.data.get("chunk_size_tokens", 700)
        if value >= chunk_size:
            raise ValueError("CHUNK_OVERLAP_TOKENS must be smaller than CHUNK_SIZE_TOKENS")
        return value

    @property
    def groq_configured(self) -> bool:
        return _has_real_value(self.groq_api_key)

    @property
    def qdrant_configured(self) -> bool:
        return (
            _has_real_value(self.qdrant_url)
            and self.qdrant_url.startswith(("https://", "http://"))
            and _has_real_value(self.qdrant_api_key)
        )

    @property
    def shared_deployment_secret_configured(self) -> bool:
        return _has_real_value(self.app_secret_key)

    def safe_summary(self) -> dict[str, str | int | bool]:
        """Return non-secret values suitable for logs or the settings page."""
        return {
            "environment": self.app_env,
            "groq_configured": self.groq_configured,
            "groq_model": self.groq_model,
            "qdrant_configured": self.qdrant_configured,
            "qdrant_collection": self.qdrant_collection,
            "embedding_model": self.embedding_model,
            "embedding_device": self.embedding_device,
            "max_upload_mb": self.max_upload_mb,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
