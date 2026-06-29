"""Per-request context the routing engine evaluates against.

The context is built once per request (UA parse, geo lookup, visitor hash) and then
treated as immutable input to the pure `resolve()`/`matches()` functions.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from user_agents import parse as parse_ua

Platform = str  # "ios" | "android" | "other"
Entry = str  # "nfc" | "qr" | "link"


def detect_platform(user_agent: str | None) -> Platform:
    """Map a User-Agent string to a coarse platform bucket."""
    if not user_agent:
        return "other"
    os_family = parse_ua(user_agent).os.family.lower()
    if "ios" in os_family or os_family in {"iphone", "ipad"}:
        return "ios"
    if "android" in os_family:
        return "android"
    return "other"


def compute_visitor_hash(ip: str | None, user_agent: str | None, day: str) -> str:
    """Daily-rotating, non-reversible visitor seed for A/B stickiness and unique counts.

    Not an identity: it changes every day and drops the raw IP (DESIGN §6).
    """
    raw = f"{ip or ''}|{user_agent or ''}|{day}"
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RequestContext:
    platform: Platform
    country: str | None
    city: str | None
    entry: Entry
    visitor_hash: str
    referrer: str | None
    now: datetime


GeoLookup = Callable[[str | None], tuple[str | None, str | None]]


def _no_geo(_ip: str | None) -> tuple[str | None, str | None]:
    return (None, None)


def build_context(
    *,
    user_agent: str | None,
    ip: str | None,
    entry: Entry = "link",
    referrer: str | None = None,
    geo: GeoLookup = _no_geo,
    now: datetime | None = None,
) -> RequestContext:
    now = now or datetime.now(UTC)
    country, city = geo(ip)
    return RequestContext(
        platform=detect_platform(user_agent),
        country=(country.upper() if country else None),
        city=city,
        entry=entry,
        visitor_hash=compute_visitor_hash(ip, user_agent, now.strftime("%Y-%m-%d")),
        referrer=referrer,
        now=now,
    )
