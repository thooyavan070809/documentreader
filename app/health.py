"""Readiness checks that never reveal credential values."""

from __future__ import annotations

from app.config import Settings
from domain.health import HealthCheck, HealthStatus
from storage.metadata import Database
from storage.qdrant import QdrantGateway


class HealthService:
    def __init__(
        self,
        *,
        settings: Settings,
        database: Database,
        qdrant: QdrantGateway,
    ) -> None:
        self.settings = settings
        self.database = database
        self.qdrant = qdrant

    def run(self, *, check_qdrant_live: bool = False) -> list[HealthCheck]:
        checks = [self._database_check(), self._groq_check()]
        checks.append(self._qdrant_check(live=check_qdrant_live))
        return checks

    def _database_check(self) -> HealthCheck:
        try:
            self.database.ping()
        except Exception as exc:
            return HealthCheck("Metadata database", HealthStatus.ERROR, type(exc).__name__)
        return HealthCheck("Metadata database", HealthStatus.READY, "SQLite is reachable")

    def _groq_check(self) -> HealthCheck:
        if not self.settings.groq_configured:
            return HealthCheck(
                "Groq",
                HealthStatus.PENDING,
                "Add GROQ_API_KEY to .env when live generation is needed",
            )
        return HealthCheck(
            "Groq",
            HealthStatus.READY,
            f"Configured for {self.settings.groq_model}; live call not performed",
        )

    def _qdrant_check(self, *, live: bool) -> HealthCheck:
        if not self.settings.qdrant_configured:
            return HealthCheck(
                "Qdrant Cloud",
                HealthStatus.PENDING,
                "Add QDRANT_URL and QDRANT_API_KEY to .env when indexing is needed",
            )
        if not live:
            return HealthCheck(
                "Qdrant Cloud",
                HealthStatus.READY,
                "Configured; live connectivity check not performed",
            )
        try:
            self.qdrant.ping()
        except Exception as exc:
            return HealthCheck("Qdrant Cloud", HealthStatus.ERROR, type(exc).__name__)
        return HealthCheck("Qdrant Cloud", HealthStatus.READY, "Connection successful")
