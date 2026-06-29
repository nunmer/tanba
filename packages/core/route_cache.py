"""Redis route cache: serialized LinkView keyed by code and slug.

Implements the read-side cache (DESIGN §7): a hit means resolution touches no database.
Writes use **delete-on-write** invalidation, not update, to stay race-safe between
concurrent dashboard writers. All operations are best-effort — callers treat Redis
errors as a cache miss so a Redis blip never breaks a redirect or a dashboard edit.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum

from redis.asyncio import Redis

from packages.routing.types import DestinationView, LinkView

NEGATIVE_TTL = 30  # seconds to remember an unknown code/slug (absorbs scanner noise)
_NEGATIVE = "\x00neg"


class Miss(Enum):
    """Sentinels distinguishing a cache miss from a cached 'known unknown'."""

    MISS = "miss"
    NEGATIVE = "negative"


def code_key(code: str) -> str:
    return f"route:code:{code}"


def slug_key(slug: str) -> str:
    return f"route:slug:{slug}"


def _serialize(link: LinkView) -> str:
    return json.dumps(asdict(link), separators=(",", ":"))


def _deserialize(raw: str) -> LinkView:
    data = json.loads(raw)
    destinations = tuple(DestinationView(**d) for d in data.pop("destinations", []))
    return LinkView(**data, destinations=destinations)


async def get(redis: Redis, key: str) -> LinkView | Miss:
    try:
        raw = await redis.get(key)
    except Exception:
        return Miss.MISS
    if raw is None:
        return Miss.MISS
    if raw == _NEGATIVE:
        return Miss.NEGATIVE
    try:
        return _deserialize(raw)
    except (ValueError, TypeError):
        return Miss.MISS


async def cache_link(redis: Redis, link: LinkView, ttl: int) -> None:
    payload = _serialize(link)
    try:
        async with redis.pipeline(transaction=False) as pipe:
            pipe.set(code_key(link.code), payload, ex=ttl)
            if link.slug:
                pipe.set(slug_key(link.slug), payload, ex=ttl)
            await pipe.execute()
    except Exception:
        pass  # cache is an optimization; never fail the request over it


async def cache_negative(redis: Redis, key: str) -> None:
    try:
        await redis.set(key, _NEGATIVE, ex=NEGATIVE_TTL)
    except Exception:
        pass


async def invalidate(redis: Redis, *, code: str, slug: str | None = None) -> None:
    """Delete cached entries for a link so the next request repopulates from Postgres."""
    keys = [code_key(code)]
    if slug:
        keys.append(slug_key(slug))
    try:
        await redis.delete(*keys)
    except Exception:
        pass
