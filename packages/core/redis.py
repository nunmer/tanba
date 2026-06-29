"""Shared async Redis client (lazy singleton)."""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from packages.core.settings import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
