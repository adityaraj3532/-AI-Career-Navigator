from datetime import datetime, timezone
from typing import Dict
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Liveness status of the API")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: datetime = Field(default_factory=utc_now)


class ReadinessResponse(BaseModel):
    status: str = Field(..., description="Readiness status: 'ready' or 'not_ready'")
    dependencies: Dict[str, str] = Field(
        ...,
        description="Health status of external dependencies (database, redis)",
    )
    timestamp: datetime = Field(default_factory=utc_now)
