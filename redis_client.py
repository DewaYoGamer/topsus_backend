"""Redis client with graceful degradation.

If Redis is unreachable the safe_* helpers return None/False instead of
raising, so the rest of the app keeps working (cache miss / skip).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Iterable

import redis
from redis.exceptions import RedisError

from .config import get_settings

log = logging.getLogger("topsus3.redis")

_settings = get_settings()


@lru_cache
def get_redis() -> redis.Redis:
    """Singleton Redis client with a connection pool.

    `decode_responses=True` means we get `str` instead of `bytes` from
    get/keys/etc. which is what we want for JSON-cached values.
    """
    return redis.Redis.from_url(
        _settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1.5,
        socket_timeout=1.5,
    )


def ping() -> bool:
    """Return True if Redis is reachable."""
    try:
        return bool(get_redis().ping())
    except RedisError as exc:
        log.warning("Redis ping failed: %s", exc)
        return False


# ---------------- Safe helpers ----------------
def safe_get(key: str) -> str | None:
    try:
        return get_redis().get(key)
    except RedisError as exc:
        log.warning("redis.get(%s) failed: %s", key, exc)
        return None


def safe_set(key: str, value: str, ex: int | None = None) -> bool:
    try:
        return bool(get_redis().set(key, value, ex=ex))
    except RedisError as exc:
        log.warning("redis.set(%s) failed: %s", key, exc)
        return False


def safe_delete(*keys: str) -> int:
    if not keys:
        return 0
    try:
        return int(get_redis().delete(*keys))
    except RedisError as exc:
        log.warning("redis.delete(%s) failed: %s", keys, exc)
        return 0


def safe_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a glob-style pattern (safe, chunked)."""
    try:
        r = get_redis()
        deleted = 0
        for chunk in _chunks(r.scan_iter(match=pattern, count=500), 500):
            if chunk:
                deleted += r.delete(*chunk)
        return deleted
    except RedisError as exc:
        log.warning("redis.delete_pattern(%s) failed: %s", pattern, exc)
        return 0


def safe_incr(key: str, *, amount: int = 1) -> int | None:
    try:
        return int(get_redis().incrby(key, amount))
    except RedisError as exc:
        log.warning("redis.incr(%s) failed: %s", key, exc)
        return None


def safe_expire(key: str, seconds: int) -> bool:
    try:
        return bool(get_redis().expire(key, seconds))
    except RedisError as exc:
        log.warning("redis.expire(%s) failed: %s", key, exc)
        return False


def safe_exists(key: str) -> bool:
    try:
        return bool(get_redis().exists(key))
    except RedisError as exc:
        log.warning("redis.exists(%s) failed: %s", key, exc)
        return False


def _chunks(iterable: Iterable[str], size: int):
    batch: list[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
