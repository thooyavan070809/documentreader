from app.config import Settings
from app.health import HealthService
from domain.health import HealthStatus
from storage.metadata import Database
from storage.qdrant import QdrantGateway


def test_health_is_useful_without_provider_credentials(
    test_settings: Settings, database: Database
) -> None:
    service = HealthService(
        settings=test_settings,
        database=database,
        qdrant=QdrantGateway(test_settings),
    )

    checks = {check.component: check for check in service.run()}

    assert checks["Metadata database"].status is HealthStatus.READY
    assert checks["Groq"].status is HealthStatus.PENDING
    assert checks["Qdrant Cloud"].status is HealthStatus.PENDING
