"""Smart links and their destinations: full CRUD with delete-on-write cache invalidation.

Every mutation that can change a resolution (link slug/type/active, any destination
change, deletes) drops the cached route so the public app repopulates from Postgres.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.dashboard.deps import (
    CurrentUser,
    SessionDep,
    authorize_org,
    load_destination,
    load_link,
)
from apps.dashboard.schemas import (
    DestinationCreate,
    DestinationOut,
    DestinationUpdate,
    LinkCreate,
    LinkOut,
    LinkUpdate,
)
from packages.core import route_cache
from packages.core.ids import generate_code
from packages.core.models import Branch, Destination, SmartLink
from packages.core.redis import get_redis

router = APIRouter(tags=["links"])

_MAX_CODE_ATTEMPTS = 5


async def _invalidate(code: str, slug: str | None) -> None:
    await route_cache.invalidate(get_redis(), code=code, slug=slug)


async def _validate_branch(branch_id: uuid.UUID | None, org_id: uuid.UUID, session) -> None:
    if branch_id is None:
        return
    branch = await session.get(Branch, branch_id)
    if branch is None or branch.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid branch_id")


# ------------------------------- links -------------------------------

@router.get("/orgs/{org_id}/links", response_model=list[LinkOut])
async def list_links(org_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> list[SmartLink]:
    await authorize_org(org_id, user, session, "member")
    rows = await session.scalars(
        select(SmartLink).where(SmartLink.org_id == org_id).order_by(SmartLink.created_at)
    )
    return list(rows)


@router.post("/orgs/{org_id}/links", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(
    org_id: uuid.UUID, body: LinkCreate, user: CurrentUser, session: SessionDep
) -> SmartLink:
    await authorize_org(org_id, user, session, "admin")
    await _validate_branch(body.branch_id, org_id, session)

    last_exc: IntegrityError | None = None
    for _ in range(_MAX_CODE_ATTEMPTS):
        link = SmartLink(
            org_id=org_id,
            branch_id=body.branch_id,
            code=generate_code(),
            slug=body.slug,
            type=body.type,
            landing_config=body.landing_config or {},
        )
        session.add(link)
        try:
            async with session.begin_nested():  # savepoint: isolate a code collision
                await session.flush()
            return link
        except IntegrityError as exc:
            last_exc = exc
            await session.expunge(link)
            if body.slug is not None and "slug" in str(exc.orig).lower():
                raise HTTPException(status.HTTP_409_CONFLICT, "slug already taken") from exc
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "could not allocate a unique code"
    ) from last_exc


@router.get("/links/{link_id}", response_model=LinkOut)
async def get_link(link_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> SmartLink:
    return await load_link(link_id, user, session, "member")


@router.patch("/links/{link_id}", response_model=LinkOut)
async def update_link(
    link_id: uuid.UUID, body: LinkUpdate, user: CurrentUser, session: SessionDep
) -> SmartLink:
    link = await load_link(link_id, user, session, "admin")
    old_slug = link.slug

    if body.branch_id is not None:
        await _validate_branch(body.branch_id, link.org_id, session)
        link.branch_id = body.branch_id
    if body.slug is not None:
        link.slug = body.slug
    if body.type is not None:
        link.type = body.type
    if body.landing_config is not None:
        link.landing_config = body.landing_config
    if body.is_active is not None:
        link.is_active = body.is_active

    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, "slug already taken") from exc

    await _invalidate(link.code, old_slug)
    if link.slug and link.slug != old_slug:
        await _invalidate(link.code, link.slug)
    return link


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(link_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    link = await load_link(link_id, user, session, "admin")
    code, slug = link.code, link.slug
    await session.delete(link)
    await session.flush()
    await _invalidate(code, slug)


# ---------------------------- destinations ----------------------------

@router.get("/links/{link_id}/destinations", response_model=list[DestinationOut])
async def list_destinations(
    link_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[Destination]:
    await load_link(link_id, user, session, "member")
    rows = await session.scalars(
        select(Destination)
        .where(Destination.smartlink_id == link_id)
        .order_by(Destination.priority)
    )
    return list(rows)


@router.post(
    "/links/{link_id}/destinations",
    response_model=DestinationOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_destination(
    link_id: uuid.UUID, body: DestinationCreate, user: CurrentUser, session: SessionDep
) -> Destination:
    link = await load_link(link_id, user, session, "admin")
    dest = Destination(
        smartlink_id=link.id,
        url=body.url,
        label=body.label,
        kind=body.kind,
        priority=body.priority,
        weight=body.weight,
        match=body.match,
    )
    session.add(dest)
    await session.flush()
    await _invalidate(link.code, link.slug)
    return dest


@router.patch("/destinations/{dest_id}", response_model=DestinationOut)
async def update_destination(
    dest_id: uuid.UUID, body: DestinationUpdate, user: CurrentUser, session: SessionDep
) -> Destination:
    dest, link = await load_destination(dest_id, user, session, "admin")
    for field in ("url", "label", "kind", "priority", "weight", "match", "is_active"):
        value = getattr(body, field)
        if value is not None:
            setattr(dest, field, value)
    await session.flush()
    await _invalidate(link.code, link.slug)
    return dest


@router.delete("/destinations/{dest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination(
    dest_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    dest, link = await load_destination(dest_id, user, session, "admin")
    await session.delete(dest)
    await session.flush()
    await _invalidate(link.code, link.slug)
