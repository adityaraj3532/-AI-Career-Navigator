import logging
import time
from typing import Dict, Tuple
from app.core.exceptions import AppException
from app.core.redis import get_redis_client

logger = logging.getLogger("app.rate_limit")

_memory_store: Dict[str, Tuple[int, float]] = {}


async def check_rate_limit(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> None:
    """Enforces rate limiting on key.
    
    Attempts Redis first; gracefully falls back to thread-safe in-memory store.
    Raises 429 when max_requests is exceeded in the time window.
    """
    now = time.time()
    try:
        redis = get_redis_client()
        redis_key = f"rl:{key}"
        current = await redis.incr(redis_key)
        if current == 1:
            await redis.expire(redis_key, window_seconds)
        if current > max_requests:
            ttl = await redis.ttl(redis_key)
            retry_after = max(ttl, 1)
            raise AppException(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message=f"Too many requests. Please retry in {retry_after} seconds.",
            )
        return
    except AppException:
        raise
    except Exception as exc:
        logger.debug("Redis rate limiting fallback: %s", exc)

    # In-memory fallback
    global _memory_store
    count, reset_at = _memory_store.get(key, (0, now + window_seconds))
    if now > reset_at:
        count = 0
        reset_at = now + window_seconds

    count += 1
    _memory_store[key] = (count, reset_at)

    if count > max_requests:
        retry_after = int(reset_at - now) + 1
        raise AppException(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message=f"Too many requests. Please retry in {retry_after} seconds.",
        )


def reset_rate_limits() -> None:
    """Utility to clear in-memory rate limit records for testing."""
    global _memory_store
    _memory_store.clear()
