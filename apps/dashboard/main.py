"""dashboard-api — authenticated management surface."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.dashboard.routers import auth, branches, links, media, members, orgs
from packages.core.settings import get_settings

app = FastAPI(title="Tanba Dashboard API", version="0.3.0")

_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(branches.router)
app.include_router(links.router)
app.include_router(media.router)
app.include_router(members.router)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
