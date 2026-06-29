"""public-api — anonymous route resolution (Milestone A: direct DB lookup, single target).

Caching, the full predicate engine, landing rendering, and analytics emit arrive in
Milestones B–D. Here a tap resolves to the highest-priority active destination.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from packages.core.db import get_session
from packages.core.models import Destination, SmartLink

SessionDep = Annotated[AsyncSession, Depends(get_session)]

app = FastAPI(title="Tanba Public API", version="0.1.0")


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


async def _resolve_code(code: str, session: AsyncSession) -> SmartLink | None:
    return await session.scalar(
        select(SmartLink)
        .where(SmartLink.code == code, SmartLink.is_active.is_(True))
        .options(selectinload(SmartLink.destinations))
    )


@app.get("/r/{code}")
async def resolve(code: str, session: SessionDep) -> Response:
    link = await _resolve_code(code, session)
    if link is None:
        return Response("Not found", status_code=status.HTTP_404_NOT_FOUND)

    active = [d for d in link.destinations if d.is_active]
    if not active:
        return Response("No destination", status_code=status.HTTP_404_NOT_FOUND)

    chosen: Destination = min(active, key=lambda d: d.priority)
    # 302 + no-store: redirects branch on per-request context in later milestones (DESIGN §7).
    return RedirectResponse(
        chosen.url,
        status_code=status.HTTP_302_FOUND,
        headers={"Cache-Control": "private, no-store"},
    )
