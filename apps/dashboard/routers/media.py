"""Physical media inventory: list/create under an org, delete a medium."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from apps.dashboard.deps import CurrentUser, SessionDep, authorize_org, load_media
from apps.dashboard.schemas import MediaCreate, MediaOut
from packages.core.models import PhysicalMedium, SmartLink

router = APIRouter(tags=["media"])


@router.get("/orgs/{org_id}/media", response_model=list[MediaOut])
async def list_media(
    org_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[PhysicalMedium]:
    await authorize_org(org_id, user, session, "member")
    rows = await session.scalars(
        select(PhysicalMedium)
        .join(SmartLink, SmartLink.id == PhysicalMedium.smartlink_id)
        .where(SmartLink.org_id == org_id)
        .order_by(PhysicalMedium.provisioned_at)
    )
    return list(rows)


@router.post("/orgs/{org_id}/media", response_model=MediaOut, status_code=status.HTTP_201_CREATED)
async def create_media(
    org_id: uuid.UUID, body: MediaCreate, user: CurrentUser, session: SessionDep
) -> PhysicalMedium:
    await authorize_org(org_id, user, session, "admin")
    link = await session.get(SmartLink, body.smartlink_id)
    if link is None or link.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid smartlink_id")
    media = PhysicalMedium(
        smartlink_id=body.smartlink_id, medium_type=body.medium_type, serial=body.serial
    )
    session.add(media)
    await session.flush()
    return media


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(media_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    media = await load_media(media_id, user, session, "admin")
    await session.delete(media)
