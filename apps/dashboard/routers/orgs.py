"""Organizations: create, list, read, and update branding."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.dashboard.deps import CurrentUser, SessionDep, authorize_org
from apps.dashboard.schemas import OrgCreate, OrgOut, OrgUpdate
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


@router.get("/{org_id}", response_model=OrgOut)
async def get_org(org_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Organization:
    await authorize_org(org_id, user, session, "member")
    org = await session.get(Organization, org_id)
    if org is None:  # member row existed but org gone — treat as not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return org


@router.patch("/{org_id}", response_model=OrgOut)
async def update_org(
    org_id: uuid.UUID, body: OrgUpdate, user: CurrentUser, session: SessionDep
) -> Organization:
    await authorize_org(org_id, user, session, "admin")
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    if body.name is not None:
        org.name = body.name
    if body.branding is not None:
        org.branding = body.branding
    await session.flush()
    return org
