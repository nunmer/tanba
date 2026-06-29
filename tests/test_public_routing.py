"""Integration tests for Milestone B public resolution: platform routing, slug,
landing, and delete-on-write cache invalidation. Exercises the full HTTP path."""

from __future__ import annotations

import pytest

IOS_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
ANDROID_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36"
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


async def _make_owner(dashboard, unique):
    reg = await dashboard.post(
        "/auth/register",
        json={"email": f"b-{unique}@example.com", "password": "supersecret1"},
    )
    access = reg.json()["access_token"]
    auth = {"Authorization": f"Bearer {access}"}
    org = await dashboard.post(
        "/orgs", json={"name": "B Cafe", "slug": f"bcafe-{unique}"}, headers=auth
    )
    return auth, org.json()["id"]


async def _add_dest(dashboard, auth, link_id, url, kind, **extra):
    body = {"url": url, "kind": kind, "label": kind, **extra}
    r = await dashboard.post(f"/links/{link_id}/destinations", json=body, headers=auth)
    assert r.status_code == 201, r.text


@pytest.fixture
async def platform_link(dashboard, unique):
    """A link with iOS->Apple, Android->Google, default->2GIS (the canonical example)."""
    auth, org_id = await _make_owner(dashboard, unique)
    link = await dashboard.post(
        f"/orgs/{org_id}/links", json={"slug": f"maps-{unique}", "type": "redirect"}, headers=auth
    )
    link_id = link.json()["id"]
    await _add_dest(dashboard, auth, link_id, "https://maps.apple.com/x", "apple_maps",
                    priority=10, match={"platform": "ios"})
    await _add_dest(dashboard, auth, link_id, "https://maps.google.com/x", "google_maps",
                    priority=10, match={"platform": "android"})
    await _add_dest(dashboard, auth, link_id, "https://2gis.kz/x", "review_2gis", priority=100)
    return {"auth": auth, "id": link_id, "code": link.json()["code"], "slug": link.json()["slug"]}


async def test_platform_routing_via_user_agent(public, platform_link):
    code = platform_link["code"]
    ios = await public.get(f"/r/{code}", headers={"User-Agent": IOS_UA}, follow_redirects=False)
    android = await public.get(f"/r/{code}", headers={"User-Agent": ANDROID_UA}, follow_redirects=False)
    desktop = await public.get(f"/r/{code}", headers={"User-Agent": DESKTOP_UA}, follow_redirects=False)

    assert ios.headers["location"] == "https://maps.apple.com/x"
    assert android.headers["location"] == "https://maps.google.com/x"
    assert desktop.headers["location"] == "https://2gis.kz/x"
    assert ios.headers["cache-control"] == "private, no-store"


async def test_slug_resolves(public, platform_link):
    resp = await public.get(
        f"/{platform_link['slug']}", headers={"User-Agent": IOS_UA}, follow_redirects=False
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://maps.apple.com/x"


async def test_force_landing_lists_actions(public, platform_link):
    resp = await public.get(f"/l/{platform_link['code']}")
    assert resp.status_code == 200
    assert "cache-control" in resp.headers and "s-maxage" in resp.headers["cache-control"]
    assert "2gis.kz" in resp.text


async def test_unknown_slug_404(public, unique):
    resp = await public.get(f"/nope-{unique}", follow_redirects=False)
    assert resp.status_code == 404


async def test_cache_invalidation_on_new_destination(public, dashboard, unique):
    """A higher-priority destination added after the first tap is seen immediately."""
    auth, org_id = await _make_owner(dashboard, unique)
    link = await dashboard.post(f"/orgs/{org_id}/links", json={"type": "redirect"}, headers=auth)
    link_id, code = link.json()["id"], link.json()["code"]
    await _add_dest(dashboard, auth, link_id, "https://old.example", "url", priority=100)

    first = await public.get(f"/r/{code}", headers={"User-Agent": DESKTOP_UA}, follow_redirects=False)
    assert first.headers["location"] == "https://old.example"  # populates cache

    # Adding a higher-priority destination must invalidate the cached resolution.
    await _add_dest(dashboard, auth, link_id, "https://new.example", "url", priority=1)
    second = await public.get(f"/r/{code}", headers={"User-Agent": DESKTOP_UA}, follow_redirects=False)
    assert second.headers["location"] == "https://new.example"
