import asyncio
import logging
from typing import Optional
from redis.asyncio import Redis, from_url

from app.core.config import get_settings

logger = logging.getLogger("app.redis")
settings = get_settings()

_redis_client: Optional[Redis] = None
_redis_loop: Optional[asyncio.AbstractEventLoop] = None


def get_redis_client() -> Redis:
    global _redis_client, _redis_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _redis_client is not None and current_loop is not None and _redis_loop != current_loop:
        _redis_client = None

    if _redis_client is None:
        _redis_client = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
        _redis_loop = current_loop
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


async def check_redis_health() -> bool:
    try:
        client = get_redis_client()
        pong = await asyncio.wait_for(client.ping(), timeout=2.0)
        return bool(pong)
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False
