"""Milestone A acceptance: a link created in the dashboard resolves to a 302 in public-api."""

from __future__ import annotations


async def test_end_to_end_tap_resolves(dashboard, public, unique):
    # 1. register -> tokens
    reg = await dashboard.post(
        "/auth/register",
        json={"email": f"owner-{unique}@example.com", "password": "supersecret1"},
    )
    assert reg.status_code == 201, reg.text
    access = reg.json()["access_token"]
    auth = {"Authorization": f"Bearer {access}"}

    # 2. create org
    org = await dashboard.post(
        "/orgs", json={"name": "Demo Coffee", "slug": f"demo-{unique}"}, headers=auth
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["id"]

    # 3. create link
    link = await dashboard.post(f"/orgs/{org_id}/links", json={"type": "redirect"}, headers=auth)
    assert link.status_code == 201, link.text
    code = link.json()["code"]

    # 4. attach a destination
    target = "https://2gis.kz/almaty/firm/demo"
    dest = await dashboard.post(
        f"/links/{link.json()['id']}/destinations",
        json={"url": target, "kind": "review_2gis", "label": "2GIS"},
        headers=auth,
    )
    assert dest.status_code == 201, dest.text

    # 5. tap the public code -> 302 to the destination
    resp = await public.get(f"/r/{code}", follow_redirects=False)
    assert resp.status_code == 302, resp.text
    assert resp.headers["location"] == target


async def test_unknown_code_is_404(public):
    resp = await public.get("/r/NOPE00", follow_redirects=False)
    assert resp.status_code == 404


async def test_link_requires_auth(dashboard, unique):
    resp = await dashboard.post(
        f"/orgs/{'0' * 8}-0000-0000-0000-000000000000/links", json={"type": "redirect"}
    )
    assert resp.status_code == 401
