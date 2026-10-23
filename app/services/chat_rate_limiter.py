"""Rate limiter for AI Chat endpoint with Redis and resilient in-memory fallback."""
from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Dict, List
from uuid import UUID

from fastapi import HTTPException, status
from app.core.redis import get_redis_client

logger = logging.getLogger("app.chat_rate_limiter")

# Rate limit thresholds
HOURLY_LIMIT_REDIS = 30
DAILY_LIMIT_REDIS = 100

# Stricter fallback limits when Redis is offline
HOURLY_LIMIT_IN_MEMORY = 15
DAILY_LIMIT_IN_MEMORY = 50

# In-memory storage: user_id -> list of timestamp floats
_in_memory_timestamps: Dict[UUID, List[float]] = defaultdict(list)


async def check_chat_rate_limit(user_id: UUID) -> None:
    """Enforce per-user hourly and daily rate limits for AI chat.

    Uses Redis if available; falls back to an in-process sliding window if Redis is down.
    Raises HTTPException(429) if limit is exceeded.
    """
    now = datetime.now(timezone.utc)
    now_ts = now.timestamp()
    hour_key = f"chat_rl_hr:{user_id}:{now.strftime('%Y%m%d%H')}"
    day_key = f"chat_rl_day:{user_id}:{now.strftime('%Y%m%d')}"

    # 1. Try Redis
    try:
        import asyncio
        redis = get_redis_client()
        pipe = redis.pipeline()
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)
        results = await asyncio.wait_for(pipe.execute(), timeout=0.5)
        hour_count = results[0]
        day_count = results[2]

        if hour_count > HOURLY_LIMIT_REDIS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Hourly rate limit exceeded ({HOURLY_LIMIT_REDIS} requests/hour). Please wait.",
                headers={"Retry-After": "120"},
            )
        if day_count > DAILY_LIMIT_REDIS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily rate limit exceeded ({DAILY_LIMIT_REDIS} requests/day).",
                headers={"Retry-After": "3600"},
            )
        return
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Redis unavailable for chat rate limiting (%s); falling back to stricter in-memory limiter.", exc)

    # 2. In-memory sliding window fallback
    history = _in_memory_timestamps[user_id]
    one_hour_ago = now_ts - 3600
    one_day_ago = now_ts - 86400

    # Prune timestamps older than 24h
    valid_day = [t for t in history if t >= one_day_ago]
    _in_memory_timestamps[user_id] = valid_day

    recent_hour = [t for t in valid_day if t >= one_hour_ago]

    if len(recent_hour) >= HOURLY_LIMIT_IN_MEMORY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Hourly chat limit exceeded (in-process fallback limit {HOURLY_LIMIT_IN_MEMORY} requests/hour).",
            headers={"Retry-After": "120"},
        )
    if len(valid_day) >= DAILY_LIMIT_IN_MEMORY:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily chat limit exceeded (in-process fallback limit {DAILY_LIMIT_IN_MEMORY} requests/day).",
            headers={"Retry-After": "3600"},
        )

    _in_memory_timestamps[user_id].append(now_ts)


def clear_in_memory_rate_limiter() -> None:
    """Helper for unit tests to reset in-memory limiter state."""
    _in_memory_timestamps.clear()
