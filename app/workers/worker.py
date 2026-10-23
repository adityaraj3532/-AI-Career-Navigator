import logging
from typing import Any, Dict
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("app.worker")


async def startup(ctx: Dict[Any, Any]) -> None:
    logger.info("ARQ background worker starting up...")
    ctx["settings"] = settings


async def shutdown(ctx: Dict[Any, Any]) -> None:
    logger.info("ARQ background worker shutting down...")


async def ping_task(ctx: Dict[Any, Any], message: str = "pong") -> str:
    """Sample background ping task verifying worker pipeline."""
    logger.info("Executing ping_task with message: %s", message)
    return f"Processed: {message}"


class WorkerSettings:
    functions = [ping_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
