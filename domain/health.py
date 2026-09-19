"""Provider-neutral health-check result types."""

from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    READY = "ready"
    PENDING = "pending"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class HealthCheck:
    component: str
    status: HealthStatus
    message: str
