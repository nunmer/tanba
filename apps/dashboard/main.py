"""dashboard-api — authenticated management surface."""

from __future__ import annotations

from fastapi import FastAPI

from apps.dashboard.routers import auth, branches, links, media, members, orgs

app = FastAPI(title="Tanba Dashboard API", version="0.3.0")

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(branches.router)
app.include_router(links.router)
app.include_router(media.router)
app.include_router(members.router)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
