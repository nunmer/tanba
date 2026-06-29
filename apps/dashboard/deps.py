"""Shared FastAPI dependencies: current user, org membership scoping."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db import get_session
from packages.core.errors import AuthError
from packages.core.models import Membership, User
from packages.core.security import decode_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]


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


async def require_membership(
    org_id: uuid.UUID, user: User, session: AsyncSession
) -> Membership:
    """Return the caller's membership for the org, or 404 to hide existence (DESIGN §9)."""
    membership = await session.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.org_id == org_id)
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return membership
