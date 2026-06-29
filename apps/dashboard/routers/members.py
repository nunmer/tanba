"""Team membership management. Admin+ only; the org must always keep at least one owner."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from apps.dashboard.deps import CurrentUser, SessionDep, authorize_org
from apps.dashboard.schemas import MemberCreate, MemberOut, MemberUpdate
from packages.core.models import Membership, User

router = APIRouter(prefix="/orgs/{org_id}/members", tags=["members"])


def _to_out(membership: Membership, email: str) -> MemberOut:
    return MemberOut(
        id=membership.id,
        user_id=membership.user_id,
        org_id=membership.org_id,
        email=email,
        role=membership.role,
    )


async def _owner_count(org_id: uuid.UUID, session: SessionDep) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.org_id == org_id, Membership.role == "owner")
    ) or 0


@router.get("", response_model=list[MemberOut])
async def list_members(
    org_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[MemberOut]:
    await authorize_org(org_id, user, session, "member")
    rows = await session.execute(
        select(Membership, User.email)
        .join(User, User.id == Membership.user_id)
        .where(Membership.org_id == org_id)
        .order_by(Membership.created_at)
    )
    return [_to_out(m, email) for m, email in rows.all()]


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: uuid.UUID, body: MemberCreate, user: CurrentUser, session: SessionDep
) -> MemberOut:
    await authorize_org(org_id, user, session, "admin")
    target = await session.scalar(select(User).where(User.email == body.email.lower()))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    existing = await session.scalar(
        select(Membership).where(
            Membership.org_id == org_id, Membership.user_id == target.id
        )
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already a member")

    membership = Membership(org_id=org_id, user_id=target.id, role=body.role)
    session.add(membership)
    await session.flush()
    return _to_out(membership, target.email)


@router.patch("/{user_id}", response_model=MemberOut)
async def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: MemberUpdate,
    user: CurrentUser,
    session: SessionDep,
) -> MemberOut:
    await authorize_org(org_id, user, session, "admin")
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    # Don't allow demoting the last remaining owner.
    demoting_owner = membership.role == "owner" and body.role != "owner"
    if demoting_owner and await _owner_count(org_id, session) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="org needs an owner")

    membership.role = body.role
    await session.flush()
    target = await session.get(User, user_id)
    return _to_out(membership, target.email if target else "")


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: uuid.UUID, user_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await authorize_org(org_id, user, session, "admin")
    membership = await session.scalar(
        select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id)
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    if membership.role == "owner" and await _owner_count(org_id, session) <= 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="org needs an owner")

    await session.delete(membership)
