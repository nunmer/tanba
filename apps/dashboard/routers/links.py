"""Smart links and their destinations (Milestone A subset)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from apps.dashboard.deps import CurrentUser, SessionDep, require_membership
from apps.dashboard.schemas import (
    DestinationCreate,
    DestinationOut,
    LinkCreate,
    LinkOut,
)
from packages.core import route_cache
from packages.core.ids import generate_code
from packages.core.models import Destination, SmartLink
from packages.core.redis import get_redis

router = APIRouter(tags=["links"])

_MAX_CODE_ATTEMPTS = 5


async def _load_link_for_user(link_id: uuid.UUID, user, session) -> SmartLink:
    link = await session.get(SmartLink, link_id)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    await require_membership(link.org_id, user, session)  # 404 if not a member
    return link


@router.post("/orgs/{org_id}/links", response_model=LinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(
    org_id: uuid.UUID, body: LinkCreate, user: CurrentUser, session: SessionDep
) -> SmartLink:
    await require_membership(org_id, user, session)

    last_exc: IntegrityError | None = None
    for _ in range(_MAX_CODE_ATTEMPTS):
        link = SmartLink(org_id=org_id, code=generate_code(), slug=body.slug, type=body.type)
        session.add(link)
        try:
            async with session.begin_nested():  # savepoint: isolate a code collision
                await session.flush()
            return link
        except IntegrityError as exc:
            last_exc = exc
            await session.expunge(link)
            # A slug clash is not retryable; only code collisions are.
            if body.slug is not None and "slug" in str(exc.orig).lower():
                raise HTTPException(status.HTTP_409_CONFLICT, "slug already taken") from exc
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "could not allocate a unique code"
    ) from last_exc


@router.get("/links/{link_id}", response_model=LinkOut)
async def get_link(link_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> SmartLink:
    return await _load_link_for_user(link_id, user, session)


@router.post(
    "/links/{link_id}/destinations",
    response_model=DestinationOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_destination(
    link_id: uuid.UUID, body: DestinationCreate, user: CurrentUser, session: SessionDep
) -> Destination:
    link = await _load_link_for_user(link_id, user, session)
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
    # delete-on-write: drop any cached resolution so the new destination is seen at once
    await route_cache.invalidate(get_redis(), code=link.code, slug=link.slug)
    return dest
