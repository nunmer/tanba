"""public-api — anonymous route resolution (Milestone B).

Cache-first: a hit resolves with no database touch. On miss we load from Postgres,
populate the cache, then resolve. Resolution itself is the pure engine in
`packages.routing`; this module only does I/O and HTTP shaping.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from apps.public.loader import load_by_code, load_by_slug
from packages.core import route_cache
from packages.core.db import get_session
from packages.core.geoip import GeoResolver
from packages.core.redis import close_redis, get_redis
from packages.core.settings import get_settings
from packages.routing import LinkView, Resolution, build_context, resolve

_TEMPLATES = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=select_autoescape(["html"]),
)
_VALID_ENTRY = {"nfc", "qr", "link"}
_LANDING_CACHE = "public, s-maxage=60"
_REDIRECT_CACHE = "private, no-store"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    app.state.geo = GeoResolver(settings.geoip_db_path or None)
    yield
    app.state.geo.close()
    await close_redis()


app = FastAPI(
    title="Tanba Public API",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Default geo resolver so the app works under test transports that don't run lifespan;
# lifespan replaces it with one built from settings at startup.
app.state.geo = GeoResolver(get_settings().geoip_db_path or None)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _entry(request: Request, default: str = "link") -> str:
    value = request.query_params.get("e", default).lower()
    return value if value in _VALID_ENTRY else default


def _build_ctx(request: Request, entry: str):
    return build_context(
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
        entry=entry,
        referrer=request.headers.get("referer"),
        geo=request.app.state.geo,
    )


async def _get_link(
    session: AsyncSession, *, code: str | None, slug: str | None
) -> LinkView | None:
    """Return a LinkView via cache-first lookup, or None (with negative caching) if absent."""
    redis = get_redis()
    key = route_cache.code_key(code) if code else route_cache.slug_key(slug or "")
    cached = await route_cache.get(redis, key)
    if isinstance(cached, LinkView):
        return cached
    if cached is route_cache.Miss.NEGATIVE:
        return None

    link = await load_by_code(session, code) if code else await load_by_slug(session, slug or "")
    if link is None:
        await route_cache.cache_negative(redis, key)
        return None
    await route_cache.cache_link(redis, link, get_settings().route_cache_ttl)
    return link


def _render_landing(link: LinkView) -> HTMLResponse:
    cfg = link.landing_config or {}
    theme = cfg.get("theme", {})
    actions = cfg.get("actions") or [
        {"label": d.kind.replace("_", " ").title(), "url": d.url}
        for d in link.destinations
        if d.is_active
    ]
    html = _TEMPLATES.get_template("landing.html").render(
        title=cfg.get("title", "Choose an option"),
        subtitle=cfg.get("subtitle"),
        bg=theme.get("bg", "#0f1115"),
        fg=theme.get("fg", "#f5f5f5"),
        accent=theme.get("accent", "#2f6df6"),
        actions=actions,
    )
    return HTMLResponse(html, headers={"Cache-Control": _LANDING_CACHE})


def _respond(resolution: Resolution, link: LinkView) -> Response:
    if resolution.kind == "landing":
        return _render_landing(link)
    if resolution.is_redirect and resolution.destination is not None:
        return RedirectResponse(
            resolution.destination.url,
            status_code=status.HTTP_302_FOUND,
            headers={"Cache-Control": _REDIRECT_CACHE},
        )
    return Response("Not found", status_code=status.HTTP_404_NOT_FOUND)


@app.get("/r/{code}")
async def resolve_code(code: str, request: Request, session: SessionDep) -> Response:
    link = await _get_link(session, code=code, slug=None)
    if link is None:
        return Response("Not found", status_code=status.HTTP_404_NOT_FOUND)
    return _respond(resolve(link, _build_ctx(request, _entry(request, "nfc"))), link)


@app.get("/l/{code}")
async def force_landing(code: str, request: Request, session: SessionDep) -> Response:
    """Force the landing/multi-action view regardless of link type."""
    link = await _get_link(session, code=code, slug=None)
    if link is None:
        return Response("Not found", status_code=status.HTTP_404_NOT_FOUND)
    return _render_landing(link)


@app.get("/{slug}")
async def resolve_slug(slug: str, request: Request, session: SessionDep) -> Response:
    link = await _get_link(session, code=None, slug=slug)
    if link is None:
        return Response("Not found", status_code=status.HTTP_404_NOT_FOUND)
    return _respond(resolve(link, _build_ctx(request, _entry(request, "link"))), link)
