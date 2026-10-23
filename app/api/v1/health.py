import logging
from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.database import check_db_health
from app.core.redis import check_redis_health
from app.schemas.health import HealthResponse, ReadinessResponse

logger = logging.getLogger("app.api.health")
router = APIRouter(tags=["Health & Diagnostics"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse, summary="Service Liveness Probe")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Service Readiness Probe",
    responses={
        status.HTTP_200_OK: {"model": ReadinessResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse},
    },
)
async def readiness_check(response: Response) -> ReadinessResponse:
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()

    dependencies = {
        "database": "ok" if db_healthy else "unhealthy",
        "redis": "ok" if redis_healthy else "unhealthy",
    }

    is_ready = db_healthy and redis_healthy
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        dependencies=dependencies,
    )
