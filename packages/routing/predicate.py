"""The tiny `match` DSL evaluator (DESIGN §4).

A predicate is a jsonb object; all keys must pass (AND). `None`/`{}` always matches.
Supported keys: platform, country, city, entry, schedule. Unknown keys **fail closed**
so a predicate the engine doesn't understand never silently matches.
"""

from __future__ import annotations

from datetime import time
from typing import Any
from zoneinfo import ZoneInfo

from packages.routing.context import RequestContext

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _match_platform(value: Any, ctx: RequestContext) -> bool:
    return ctx.platform in {str(v).lower() for v in _as_list(value)}


def _match_country(value: Any, ctx: RequestContext) -> bool:
    if ctx.country is None:
        return False
    return ctx.country in {str(v).upper() for v in _as_list(value)}


def _match_city(value: Any, ctx: RequestContext) -> bool:
    if ctx.city is None:
        return False
    return ctx.city.casefold() in {str(v).casefold() for v in _as_list(value)}


def _match_entry(value: Any, ctx: RequestContext) -> bool:
    return ctx.entry in {str(v).lower() for v in _as_list(value)}


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def _match_schedule(value: Any, ctx: RequestContext) -> bool:
    if not isinstance(value, dict):
        return False
    tz = ZoneInfo(value.get("tz", "Asia/Almaty"))
    local = ctx.now.astimezone(tz)

    days = value.get("days")
    if days is not None:
        wanted = {str(d).lower()[:3] for d in _as_list(days)}
        if _WEEKDAYS[local.weekday()] not in wanted:
            return False

    start_raw, end_raw = value.get("from"), value.get("to")
    if start_raw is None or end_raw is None:
        return True
    start, end, current = _parse_hhmm(start_raw), _parse_hhmm(end_raw), local.time()
    if start <= end:
        return start <= current <= end
    # window wraps past midnight (e.g. 22:00 -> 02:00)
    return current >= start or current <= end


_EVALUATORS = {
    "platform": _match_platform,
    "country": _match_country,
    "city": _match_city,
    "entry": _match_entry,
    "schedule": _match_schedule,
}


def matches(predicate: dict[str, Any] | None, ctx: RequestContext) -> bool:
    """True if every key in the predicate matches the context. None/{} always matches."""
    if not predicate:
        return True
    for key, value in predicate.items():
        evaluator = _EVALUATORS.get(key)
        if evaluator is None or not evaluator(value, ctx):
            return False
    return True
