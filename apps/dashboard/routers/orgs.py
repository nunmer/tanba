"""Organizations: create (with owner membership) and list the caller's orgs."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.dashboard.deps import CurrentUser, SessionDep
from apps.dashboard.schemas import OrgCreate, OrgOut
from packages.core.models import Membership, Organization

router = APIRouter(prefix="/orgs", tags=["orgs"])


@router.post("", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
async def create_org(body: OrgCreate, user: CurrentUser, session: SessionDep) -> Organization:
    org = Organization(name=body.name, slug=body.slug)
    session.add(org)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="slug already taken"
        ) from exc

    session.add(Membership(user_id=user.id, org_id=org.id, role="owner"))
    await session.flush()
    return org


@router.get("", response_model=list[OrgOut])
async def list_orgs(user: CurrentUser, session: SessionDep) -> list[Organization]:
    rows = await session.scalars(
        select(Organization)
        .join(Membership, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Organization.created_at)
    )
    return list(rows)
