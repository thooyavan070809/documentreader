"""Shared test fixtures."""

import pytest

from app.config import Settings
from storage.metadata import Database


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        app_secret_key="test-only-secret",
        groq_api_key="",
        qdrant_url="",
        qdrant_api_key="",
        metadata_database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_root=tmp_path / "uploads",
    )


@pytest.fixture
def database(test_settings: Settings) -> Database:
    db = Database(test_settings.metadata_database_url)
    db.initialize()
    yield db
    db.dispose()
