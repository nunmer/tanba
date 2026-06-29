"""Shared FastAPI dependencies: current user, org membership + role scoping,
and resource loaders that enforce tenant isolation.

Authorization model (DESIGN §9):
  * Not a member of the org  -> 404 (hide existence; don't confirm the resource exists).
  * Member but role too low   -> 403 (caller already knows the org exists).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db import get_session
from packages.core.errors import AuthError
from packages.core.models import Branch, Destination, Membership, PhysicalMedium, SmartLink, User
from packages.core.security import decode_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

ROLE_ORDER = {"member": 0, "admin": 1, "owner": 2}


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        user_id = decode_token(token, "access")
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


async def authorize_org(
    org_id: uuid.UUID, user: User, session: AsyncSession, min_role: str = "member"
) -> Membership:
    """Return the caller's membership for the org, enforcing the role floor."""
    membership = await session.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.org_id == org_id)
    )
    if membership is None:
        raise _NOT_FOUND
    if ROLE_ORDER[membership.role] < ROLE_ORDER[min_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"requires {min_role} role"
        )
    return membership


# Backwards-compatible alias used by existing create routes.
async def require_membership(org_id: uuid.UUID, user: User, session: AsyncSession) -> Membership:
    return await authorize_org(org_id, user, session, "member")


async def load_link(
    link_id: uuid.UUID, user: User, session: AsyncSession, min_role: str = "member"
) -> SmartLink:
    link = await session.get(SmartLink, link_id)
    if link is None:
        raise _NOT_FOUND
    await authorize_org(link.org_id, user, session, min_role)
    return link


async def load_branch(
    branch_id: uuid.UUID, user: User, session: AsyncSession, min_role: str = "member"
) -> Branch:
    branch = await session.get(Branch, branch_id)
    if branch is None:
        raise _NOT_FOUND
    await authorize_org(branch.org_id, user, session, min_role)
    return branch


async def load_destination(
    dest_id: uuid.UUID, user: User, session: AsyncSession, min_role: str = "member"
) -> tuple[Destination, SmartLink]:
    dest = await session.get(Destination, dest_id)
    if dest is None:
        raise _NOT_FOUND
    link = await session.get(SmartLink, dest.smartlink_id)
    if link is None:
        raise _NOT_FOUND
    await authorize_org(link.org_id, user, session, min_role)
    return dest, link


async def load_media(
    media_id: uuid.UUID, user: User, session: AsyncSession, min_role: str = "member"
) -> PhysicalMedium:
    media = await session.get(PhysicalMedium, media_id)
    if media is None:
        raise _NOT_FOUND
    link = await session.get(SmartLink, media.smartlink_id)
    if link is None:
        raise _NOT_FOUND
    await authorize_org(link.org_id, user, session, min_role)
    return media
