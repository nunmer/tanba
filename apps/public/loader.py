"""Load SmartLink rows from Postgres and map them to the cache/engine LinkView.

This is the one place the public app touches the ORM for routing; everything downstream
operates on the pure LinkView so resolution stays DB-free and cacheable.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.core.models import SmartLink
from packages.routing.types import DestinationView, LinkView


def to_link_view(link: SmartLink) -> LinkView:
    return LinkView(
        id=str(link.id),
        org_id=str(link.org_id),
        code=link.code,
        slug=link.slug,
        type=link.type,
        is_active=link.is_active,
        landing_config=link.landing_config or {},
        destinations=tuple(
            DestinationView(
                id=str(d.id),
                url=d.url,
                kind=d.kind,
                priority=d.priority,
                weight=d.weight,
                match=d.match,
                is_active=d.is_active,
            )
            for d in link.destinations
        ),
    )


async def _load(session: AsyncSession, field, value: str) -> LinkView | None:
    link = await session.scalar(
        select(SmartLink).where(field == value).options(selectinload(SmartLink.destinations))
    )
    return to_link_view(link) if link is not None else None


async def load_by_code(session: AsyncSession, code: str) -> LinkView | None:
    return await _load(session, SmartLink.code, code)


async def load_by_slug(session: AsyncSession, slug: str) -> LinkView | None:
    return await _load(session, SmartLink.slug, slug)
