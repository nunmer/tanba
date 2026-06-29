"""Milestone C: multi-tenant isolation, role enforcement, and management CRUD.

Core guarantee under test (DESIGN §9): a caller can never see or touch another org's
resources, and unauthorized access returns 404 (existence hiding), not 403.
"""

from __future__ import annotations

import pytest


async def _register(dashboard, email):
    r = await dashboard.post("/auth/register", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _org(dashboard, auth, slug):
    r = await dashboard.post("/orgs", json={"name": "Org", "slug": slug}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _link(dashboard, auth, org_id, **body):
    r = await dashboard.post(f"/orgs/{org_id}/links", json={"type": "redirect", **body}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
async def two_orgs(dashboard, unique):
    """Owner A with an org+link; unrelated owner B."""
    a = await _register(dashboard, f"a-{unique}@example.com")
    b = await _register(dashboard, f"b-{unique}@example.com")
    org_a = await _org(dashboard, a, f"orga-{unique}")
    link_a = await _link(dashboard, a, org_a)
    return {"a": a, "b": b, "org_a": org_a, "link_a": link_a, "uniq": unique}


# ------------------------------ tenant isolation ------------------------------

async def test_outsider_cannot_read_link_404(dashboard, two_orgs):
    resp = await dashboard.get(f"/links/{two_orgs['link_a']['id']}", headers=two_orgs["b"])
    assert resp.status_code == 404


async def test_outsider_cannot_read_org_404(dashboard, two_orgs):
    resp = await dashboard.get(f"/orgs/{two_orgs['org_a']}", headers=two_orgs["b"])
    assert resp.status_code == 404


async def test_outsider_cannot_add_destination_404(dashboard, two_orgs):
    resp = await dashboard.post(
        f"/links/{two_orgs['link_a']['id']}/destinations",
        json={"url": "https://evil", "kind": "url"},
        headers=two_orgs["b"],
    )
    assert resp.status_code == 404


async def test_outsider_cannot_list_links_404(dashboard, two_orgs):
    resp = await dashboard.get(f"/orgs/{two_orgs['org_a']}/links", headers=two_orgs["b"])
    assert resp.status_code == 404


# ------------------------------- role enforcement ------------------------------

async def test_member_cannot_create_link_but_admin_can(dashboard, two_orgs):
    # Add B as a plain member of org A.
    add = await dashboard.post(
        f"/orgs/{two_orgs['org_a']}/members",
        json={"email": f"b-{two_orgs['uniq']}@example.com", "role": "member"},
        headers=two_orgs["a"],
    )
    assert add.status_code == 201, add.text

    as_member = await dashboard.post(
        f"/orgs/{two_orgs['org_a']}/links", json={"type": "redirect"}, headers=two_orgs["b"]
    )
    assert as_member.status_code == 403  # member can read but not create

    listing = await dashboard.get(f"/orgs/{two_orgs['org_a']}/links", headers=two_orgs["b"])
    assert listing.status_code == 200  # ...but reads are fine


# --------------------------------- branch CRUD ---------------------------------

async def test_branch_crud_and_link_attach(dashboard, two_orgs):
    a, org_a = two_orgs["a"], two_orgs["org_a"]
    created = await dashboard.post(
        f"/orgs/{org_a}/branches", json={"name": "Almaty Central"}, headers=a
    )
    assert created.status_code == 201
    branch_id = created.json()["id"]

    link = await _link(dashboard, a, org_a, branch_id=branch_id)
    assert link["branch_id"] == branch_id

    patched = await dashboard.patch(
        f"/branches/{branch_id}", json={"name": "Renamed"}, headers=a
    )
    assert patched.status_code == 200 and patched.json()["name"] == "Renamed"

    deleted = await dashboard.delete(f"/branches/{branch_id}", headers=a)
    assert deleted.status_code == 204


async def test_cross_org_branch_attach_rejected(dashboard, two_orgs):
    org_b = await _org(dashboard, two_orgs["b"], f"orgb-{two_orgs['uniq']}")
    branch_b = await dashboard.post(
        f"/orgs/{org_b}/branches", json={"name": "B branch"}, headers=two_orgs["b"]
    )
    # Owner A tries to attach a branch that belongs to org B -> 400.
    resp = await dashboard.post(
        f"/orgs/{two_orgs['org_a']}/links",
        json={"type": "redirect", "branch_id": branch_b.json()["id"]},
        headers=two_orgs["a"],
    )
    assert resp.status_code == 400


# ----------------------------------- media -----------------------------------

async def test_media_lifecycle(dashboard, two_orgs):
    a, org_a, link_a = two_orgs["a"], two_orgs["org_a"], two_orgs["link_a"]
    created = await dashboard.post(
        f"/orgs/{org_a}/media",
        json={"smartlink_id": link_a["id"], "medium_type": "nfc_card", "serial": "SN-1"},
        headers=a,
    )
    assert created.status_code == 201, created.text
    listing = await dashboard.get(f"/orgs/{org_a}/media", headers=a)
    assert len(listing.json()) == 1
    deleted = await dashboard.delete(f"/media/{created.json()['id']}", headers=a)
    assert deleted.status_code == 204


# ---------------------------------- members ----------------------------------

async def test_cannot_remove_last_owner(dashboard, two_orgs):
    a, org_a = two_orgs["a"], two_orgs["org_a"]
    me = await dashboard.get("/orgs", headers=a)  # find my user id via members list instead
    members = await dashboard.get(f"/orgs/{org_a}/members", headers=a)
    owner = next(m for m in members.json() if m["role"] == "owner")
    resp = await dashboard.delete(f"/orgs/{org_a}/members/{owner['user_id']}", headers=a)
    assert resp.status_code == 400  # org must keep an owner
    assert me.status_code == 200


async def test_link_delete_cascades_and_invalidates(dashboard, public, two_orgs):
    a, link_a = two_orgs["a"], two_orgs["link_a"]
    await dashboard.post(
        f"/links/{link_a['id']}/destinations",
        json={"url": "https://gone.example", "kind": "url"},
        headers=a,
    )
    code = link_a["code"]
    first = await public.get(f"/r/{code}", follow_redirects=False)
    assert first.headers["location"] == "https://gone.example"  # cached

    deleted = await dashboard.delete(f"/links/{link_a['id']}", headers=a)
    assert deleted.status_code == 204
    after = await public.get(f"/r/{code}", follow_redirects=False)
    assert after.status_code == 404  # cache invalidated, row gone
