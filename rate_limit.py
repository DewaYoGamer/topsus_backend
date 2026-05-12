"""Redis-backed sliding-window(ish) rate limiter using INCR + EXPIRE.

If Redis is unreachable the limiter fails open (allows the request) to avoid
taking the service down with the cache.
"""
from __future__ import annotations

from dataclasses import dataclass

from .redis_client import get_redis
from redis.exceptions import RedisError


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int  # seconds until reset (approx)


def check_rate_limit(key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
    """Token-bucket-ish limiter.

    The first request in a window sets the key with TTL=window; subsequent
    requests INCR it. Once count > limit it's blocked.
    """
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(key, 1)
        pipe.ttl(key)
        count, ttl = pipe.execute()
        count = int(count)
        ttl = int(ttl)
        if count == 1 or ttl < 0:
            # fresh key -> set the TTL
            r.expire(key, window_seconds)
            ttl = window_seconds
        if count > limit:
            return RateLimitResult(
                allowed=False, remaining=0, retry_after=max(ttl, 1)
            )
        return RateLimitResult(
            allowed=True, remaining=max(limit - count, 0), retry_after=max(ttl, 0)
        )
    except RedisError:
        # Fail-open: Redis is down, don't block legitimate users.
        return RateLimitResult(allowed=True, remaining=limit, retry_after=0)
