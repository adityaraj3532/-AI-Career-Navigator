import logging
from typing import Any, Dict
from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import setup_logging
from app.repositories.token_repository import TokenRepository

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


async def delete_expired_tokens_task(ctx: Dict[Any, Any]) -> int:
    """Scheduled background cleanup job that deletes expired refresh tokens."""
    logger.info("Running expired refresh token purge...")
    async with async_session_factory() as session:
        repo = TokenRepository(session)
        deleted_count = await repo.delete_expired_tokens()
        await session.commit()
    logger.info("Purged %d expired refresh tokens.", deleted_count)
    return deleted_count


class WorkerSettings:
    functions = [ping_task, delete_expired_tokens_task]
    cronjobs = [
        # Run daily at 03:00 UTC
        cron(delete_expired_tokens_task, hour={3}, minute={0}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
