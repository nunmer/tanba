"""Branches: list/create under an org, read/update/delete a branch."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from apps.dashboard.deps import CurrentUser, SessionDep, authorize_org, load_branch
from apps.dashboard.schemas import BranchCreate, BranchOut, BranchUpdate
from packages.core.models import Branch

router = APIRouter(tags=["branches"])


@router.get("/orgs/{org_id}/branches", response_model=list[BranchOut])
async def list_branches(org_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> list[Branch]:
    await authorize_org(org_id, user, session, "member")
    rows = await session.scalars(
        select(Branch).where(Branch.org_id == org_id).order_by(Branch.created_at)
    )
    return list(rows)


@router.post(
    "/orgs/{org_id}/branches", response_model=BranchOut, status_code=status.HTTP_201_CREATED
)
async def create_branch(
    org_id: uuid.UUID, body: BranchCreate, user: CurrentUser, session: SessionDep
) -> Branch:
    await authorize_org(org_id, user, session, "admin")
    branch = Branch(
        org_id=org_id, name=body.name, address=body.address, timezone=body.timezone
    )
    session.add(branch)
    await session.flush()
    return branch


@router.get("/branches/{branch_id}", response_model=BranchOut)
async def get_branch(branch_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Branch:
    return await load_branch(branch_id, user, session, "member")


@router.patch("/branches/{branch_id}", response_model=BranchOut)
async def update_branch(
    branch_id: uuid.UUID, body: BranchUpdate, user: CurrentUser, session: SessionDep
) -> Branch:
    branch = await load_branch(branch_id, user, session, "admin")
    if body.name is not None:
        branch.name = body.name
    if body.address is not None:
        branch.address = body.address
    if body.timezone is not None:
        branch.timezone = body.timezone
    await session.flush()
    return branch


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(branch_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    branch = await load_branch(branch_id, user, session, "admin")
    await session.delete(branch)
