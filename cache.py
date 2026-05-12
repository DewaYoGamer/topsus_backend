"""Tiny JSON-based cache layer on top of Redis.

Usage:
    data = cache_get_json("cache:dosen:list")
    if data is None:
        data = expensive_query()
        cache_set_json("cache:dosen:list", data, ttl=60)

    invalidate_dosen_list()
    invalidate_mahasiswa_all()
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from .config import get_settings
from .redis_client import safe_delete, safe_delete_pattern, safe_get, safe_set

_settings = get_settings()

# --- Key constants ---
DOSEN_LIST = "cache:dosen:list"
MHS_LIST_ADMIN = "cache:mhs:list:admin"
MHS_LIST_DOSEN_PREFIX = "cache:mhs:list:dosen:"  # + dosen_id


def _default(obj: Any):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"not serialisable: {type(obj)!r}")


def cache_get_json(key: str) -> Any | None:
    raw = safe_get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


def cache_set_json(key: str, value: Any, ttl: int | None = None) -> bool:
    ttl = ttl if ttl is not None else _settings.cache_ttl_seconds
    try:
        payload = json.dumps(value, default=_default)
    except (TypeError, ValueError):
        return False
    return safe_set(key, payload, ex=ttl)


# ---- Invalidations ----
def invalidate_dosen_list() -> None:
    safe_delete(DOSEN_LIST)
    # A dosen change also affects the embedded `dosen_pembimbing` field
    # on cached mahasiswa lists -> bust those too.
    invalidate_mahasiswa_all()


def invalidate_mahasiswa_all() -> None:
    safe_delete(MHS_LIST_ADMIN)
    safe_delete_pattern(f"{MHS_LIST_DOSEN_PREFIX}*")


def mhs_list_key_for(role: str, user_id: int) -> str | None:
    """Return the cache key to use for a list request, or None if not cacheable."""
    if role == "admin":
        return MHS_LIST_ADMIN
    if role == "dosen":
        return f"{MHS_LIST_DOSEN_PREFIX}{user_id}"
    return None
