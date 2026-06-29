"""dashboard-api — authenticated management surface."""

from __future__ import annotations

from fastapi import FastAPI

from apps.dashboard.routers import auth, links, orgs

app = FastAPI(title="Tanba Dashboard API", version="0.1.0")

app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(links.router)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
