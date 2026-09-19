"""Streamlit-cached application resources."""

from dataclasses import dataclass

import streamlit as st

from app.config import Settings, get_settings
from app.dependencies import (
    get_chat_service,
    get_database,
    get_ingestion_service,
    get_qdrant_gateway,
)
from app.health import HealthService
from ingestion.pipeline import IngestionService
from rag.service import GroundedChatService
from storage.metadata import Database
from storage.qdrant import QdrantGateway


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    database: Database
    qdrant: QdrantGateway

    def health_service(self) -> HealthService:
        return HealthService(
            settings=self.settings,
            database=self.database,
            qdrant=self.qdrant,
        )

    def ingestion_service(self) -> IngestionService:
        return get_ingestion_service()

    def chat_service(self) -> GroundedChatService:
        return get_chat_service()


@st.cache_resource(show_spinner=False)
def get_runtime() -> Runtime:
    return Runtime(
        settings=get_settings(),
        database=get_database(),
        qdrant=get_qdrant_gateway(),
    )
