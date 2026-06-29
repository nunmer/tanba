"""Pure-function tests for the routing engine: predicate matrix + resolution logic.

No I/O — synthetic RequestContext / LinkView only (DESIGN §4, §12).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from packages.routing import DestinationView, LinkView, RequestContext, matches, resolve
from packages.routing.predicate import _WEEKDAYS

ALMATY = ZoneInfo("Asia/Almaty")


def ctx(
    *,
    platform="other",
    country=None,
    city=None,
    entry="link",
    visitor_hash="seed",
    now=None,
) -> RequestContext:
    return RequestContext(
        platform=platform,
        country=country,
        city=city,
        entry=entry,
        visitor_hash=visitor_hash,
        referrer=None,
        now=now or datetime(2026, 6, 27, 12, 0, tzinfo=ALMATY),
    )


def dest(url, *, kind="url", priority=100, weight=1, match=None, active=True) -> DestinationView:
    return DestinationView(
        id=url, url=url, kind=kind, priority=priority, weight=weight, match=match, is_active=active
    )


def link(*destinations, type="redirect", active=True, lid="link-1") -> LinkView:
    return LinkView(
        id=lid, org_id="org-1", code="ABC123", slug=None, type=type,
        is_active=active, destinations=tuple(destinations),
    )


# --------------------------- predicate: matches() ---------------------------

def test_none_and_empty_always_match():
    assert matches(None, ctx()) is True
    assert matches({}, ctx()) is True


@pytest.mark.parametrize(
    "predicate,platform,expected",
    [
        ({"platform": "ios"}, "ios", True),
        ({"platform": "ios"}, "android", False),
        ({"platform": ["ios", "android"]}, "android", True),
        ({"platform": ["ios", "android"]}, "other", False),
    ],
)
def test_platform(predicate, platform, expected):
    assert matches(predicate, ctx(platform=platform)) is expected


def test_country_normalizes_case_and_requires_known_geo():
    assert matches({"country": "kz"}, ctx(country="KZ")) is True
    assert matches({"country": ["KZ", "RU"]}, ctx(country="RU")) is True
    assert matches({"country": "KZ"}, ctx(country="US")) is False
    assert matches({"country": "KZ"}, ctx(country=None)) is False  # unknown geo fails closed


def test_city_case_insensitive():
    assert matches({"city": "Almaty"}, ctx(city="almaty")) is True
    assert matches({"city": ["Almaty", "Astana"]}, ctx(city="Astana")) is True
    assert matches({"city": "Almaty"}, ctx(city=None)) is False


def test_entry():
    assert matches({"entry": "nfc"}, ctx(entry="nfc")) is True
    assert matches({"entry": ["nfc", "qr"]}, ctx(entry="qr")) is True
    assert matches({"entry": "nfc"}, ctx(entry="link")) is False


def test_unknown_key_fails_closed():
    assert matches({"weather": "sunny"}, ctx()) is False
    assert matches({"platform": "ios", "weather": "sunny"}, ctx(platform="ios")) is False


def test_multiple_keys_are_anded():
    p = {"platform": "android", "city": "Almaty"}
    assert matches(p, ctx(platform="android", city="Almaty")) is True
    assert matches(p, ctx(platform="android", city="Astana")) is False


def test_schedule_days():
    when = datetime(2026, 6, 27, 14, 0, tzinfo=ALMATY)
    today = _WEEKDAYS[when.weekday()]
    other = _WEEKDAYS[(when.weekday() + 1) % 7]
    assert matches({"schedule": {"days": [today]}}, ctx(now=when)) is True
    assert matches({"schedule": {"days": [other]}}, ctx(now=when)) is False


def test_schedule_time_window():
    inside = datetime(2026, 6, 27, 14, 0, tzinfo=ALMATY)
    outside = datetime(2026, 6, 27, 9, 0, tzinfo=ALMATY)
    window = {"schedule": {"from": "10:00", "to": "22:00"}}
    assert matches(window, ctx(now=inside)) is True
    assert matches(window, ctx(now=outside)) is False


def test_schedule_window_wraps_midnight():
    window = {"schedule": {"from": "22:00", "to": "02:00"}}
    assert matches(window, ctx(now=datetime(2026, 6, 27, 23, 30, tzinfo=ALMATY))) is True
    assert matches(window, ctx(now=datetime(2026, 6, 27, 1, 30, tzinfo=ALMATY))) is True
    assert matches(window, ctx(now=datetime(2026, 6, 27, 12, 0, tzinfo=ALMATY))) is False


def test_schedule_respects_timezone():
    # 20:00 UTC is 01:00 next day in Almaty (UTC+5) -> outside a 10:00-22:00 Almaty window
    utc_eve = datetime(2026, 6, 27, 20, 0, tzinfo=ZoneInfo("UTC"))
    assert matches({"schedule": {"from": "10:00", "to": "22:00"}}, ctx(now=utc_eve)) is False


# ------------------------------ engine: resolve() ------------------------------

def test_inactive_link_not_found():
    r = resolve(link(dest("https://x"), active=False), ctx())
    assert r.kind == "not_found"


def test_landing_and_multi_render_landing():
    assert resolve(link(type="landing"), ctx()).kind == "landing"
    assert resolve(link(type="multi"), ctx()).kind == "landing"


def test_platform_routing():
    apple = dest("https://maps.apple.com", kind="apple_maps", priority=10, match={"platform": "ios"})
    google = dest("https://maps.google.com", kind="google_maps", priority=10, match={"platform": "android"})
    twogis = dest("https://2gis.kz", kind="review_2gis", priority=100, match=None)  # default
    page = link(apple, google, twogis)

    assert resolve(page, ctx(platform="ios")).destination.url == "https://maps.apple.com"
    assert resolve(page, ctx(platform="android")).destination.url == "https://maps.google.com"
    assert resolve(page, ctx(platform="other")).destination.url == "https://2gis.kz"


def test_lower_priority_number_wins():
    hi = dest("https://promo", priority=1)
    lo = dest("https://normal", priority=100)
    assert resolve(link(hi, lo), ctx()).destination.url == "https://promo"


def test_no_matching_candidate_is_not_found():
    only_ios = dest("https://apple", match={"platform": "ios"})
    assert resolve(link(only_ios), ctx(platform="android")).kind == "not_found"


def test_inactive_destination_skipped():
    off = dest("https://off", priority=1, active=False)
    on = dest("https://on", priority=10)
    assert resolve(link(off, on), ctx()).destination.url == "https://on"


def test_ab_is_sticky_per_visitor():
    a = dest("https://a", priority=10, weight=1)
    b = dest("https://b", priority=10, weight=1)
    page = link(a, b)
    first = resolve(page, ctx(visitor_hash="visitor-42")).destination.url
    again = resolve(page, ctx(visitor_hash="visitor-42")).destination.url
    assert first == again  # deterministic for the same visitor


def test_ab_distribution_follows_weight():
    a = dest("https://a", priority=10, weight=9)
    b = dest("https://b", priority=10, weight=1)
    page = link(a, b)
    picks = [resolve(page, ctx(visitor_hash=f"v{i}")).destination.url for i in range(1000)]
    share_a = picks.count("https://a") / len(picks)
    assert 0.85 <= share_a <= 0.95  # ~90% to the heavier variant
