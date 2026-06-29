"""Shared test fixtures: ASGI clients for both apps over the same database."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from apps.dashboard.main import app as dashboard_app
from apps.public.main import app as public_app
from packages.core.db import engine


@pytest.fixture(autouse=True)
async def _dispose_engine() -> AsyncGenerator[None, None]:
    """pytest-asyncio runs each test in its own loop; dispose pooled connections after
    each so the next test doesn't reuse a connection bound to a closed loop."""
    yield
    await engine.dispose()


@pytest.fixture
async def dashboard() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=dashboard_app)
    async with AsyncClient(transport=transport, base_url="http://dash.test") as client:
        yield client


@pytest.fixture
async def public() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=public_app)
    async with AsyncClient(transport=transport, base_url="http://pub.test") as client:
        yield client


@pytest.fixture
def unique() -> str:
    """A short unique token for emails/slugs so tests don't collide across runs."""
    return uuid.uuid4().hex[:10]
