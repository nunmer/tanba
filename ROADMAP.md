# Tanba — Implementation Roadmap (v1)

> Decisions locked for v1: **MVP to validate** · **full vertical feature scope** · **billing stubbed** · **docker-compose local only**.
> See `DESIGN.md` for rationale and `IMPLEMENTATION.md` for the target end state. This file is the build sequence to get there.

## Strategy

Build the *whole feature surface* (all entities/flows from `IMPLEMENTATION.md`) but at **MVP depth** — skip k8s/HA, ClickHouse, real payments. Approach is **walking skeleton first**: a real tap resolves end-to-end by Milestone A, then each layer is thickened.

### Guiding principles
- **Walking skeleton before breadth** — one tap resolves end-to-end early, then deepen.
- **Routing engine is pure & TDD'd** — `matches()`/`resolve()` are side-effect-free; tested with a synthetic context matrix before wiring I/O (DESIGN §4).
- **Single Postgres, `org_id` everywhere** — multi-tenant from row one; sharding deferred (DESIGN §8).
- **Cache-first public path, delete-on-write invalidation** (DESIGN §7).
- **MVP infra** — docker-compose only; k8s manifests are stubs we fill post-validation.

## Default technical decisions

| Area | Default |
|------|---------|
| Stack | FastAPI async, SQLAlchemy 2.0 async + asyncpg, Pydantic v2 / pydantic-settings, Alembic, redis-py async, `uv` |
| Auth | PyJWT access+refresh, `argon2-cffi` hashing |
| UA / Geo | `user-agents` parsing; `geoip2` + MaxMind GeoLite2-City (free account → `GEOIP_DB_PATH`) |
| Landing pages | Jinja2 server-rendered in public-api |
| Logs / metrics | `structlog` JSON logs, `prometheus-client` `/metrics` |
| Tests | pytest + httpx ASGI transport, 80% coverage target |
| Dashboard surface | **API-only for v1** (FastAPI `/docs`) — no React UI |

### Open decisions (revisit when relevant)
1. **Dashboard UI** — API-only for v1; a React dashboard is a v2 milestone.
2. **GeoIP** — MaxMind GeoLite2-City bundled locally; alternative is country-only from a lighter source.

---

## Milestones

### Milestone A — Walking skeleton (end-to-end tap) 🎯
Scaffold + thinnest path proving the whole pipe.
- Monorepo per README layout, `pyproject.toml` + `uv`, `docker-compose.yml` (postgres, redis), `.env.example`, ruff/pyright.
- `packages/core`: settings, async DB session, base model, errors, security (Argon2 + JWT), base32 code gen.
- Minimal model + first Alembic migration: `Organization`, `User`/`Membership`, `SmartLink`, `Destination`.
- `dashboard-api`: register/login, create org, create link (collision-checked `code`), attach one destination.
- `public-api`: `GET /r/{code}` → DB lookup → `302`; `/healthz`.
- **Deliverable:** create a link via dashboard, tap `localhost:8001/r/{code}`, get redirected.

### Milestone B — Routing engine (core value)
- `packages/routing`: pure `matches()` + `resolve()` — platform/country/city/schedule/entry; `priority` + `weight` (sticky A/B by `visitor_hash`); `match:null` default. **TDD: synthetic matrix first.**
- `request_ctx` builder (UA → device/os/browser, geo, visitor_hash, entry, referrer).
- Redis route cache (`route:{code}`/`route:{slug}`), TTL safety net, negative cache for unknown codes.
- `slug` lookup, `/{slug}`, `/l/{code}` force-landing, Jinja2 landing rendering, correct `Cache-Control`.
- **Deliverable:** iOS→Apple Maps / Android→Google Maps / else→2GIS, plus weekend-schedule and an A/B link, cached.

### Milestone C — Multi-tenancy depth & management API
- Remaining model: `Branch`, `PhysicalMedium`, `Subscription` (+ partitioned `InteractionEvent` table, written in D).
- Full dashboard CRUD: orgs/branches/links/destinations/media/members; roles (`owner>admin>member`).
- Tenancy dependency: membership-checked routes, **404-not-403** existence hiding (DESIGN §9).
- Delete-on-write cache invalidation on every link/destination mutation.
- **Deliverable:** complete tenant management; cross-org access returns 404 (asserted by tests).

### Milestone D — Analytics pipeline
- Fire-and-forget event emit to Redis Stream from public-api (never blocks redirect).
- `workers/analytics_worker.py`: consumer group, batch, UA parse, IP→geo then **drop IP**, daily-salted `visitor_hash`, insert into monthly partitions, update `daily_link_stats`/`daily_org_stats` rollups (behind a store adapter for future ClickHouse swap).
- Dashboard `analytics/summary` + `analytics/timeseries` reading rollups.
- **Deliverable:** taps show as unique/repeat, device/geo breakdowns, time series — no PII stored.

### Milestone E — Billing stub + plan gating
- `Subscription` lifecycle without a provider; `plan` set manually/seed.
- Plan-gating dependency (quotas, premium analytics) — the seam a real Kaspi/Stripe integration drops into later.
- **Deliverable:** plan limits enforced; upgrade = admin flip for now.

### Milestone F — Hardening & validation polish
- Rate limiting on public path, structured logs (no IPs), Prometheus metrics (cache hit ratio, resolve latency, stream lag).
- `scripts/seed_demo.py`.
- Test coverage to 80% (routing matrix, API, tenancy-404, worker enrichment/rollup math).
- Fill `deploy/k8s` as stubs + deploy note (not exercised in v1).
- **Deliverable:** demo-ready, observable, tested MVP runnable with `docker compose up`.

---

## Dependency flow

```
A ─▶ B ─▶ C ─▶ D ─▶ E ─▶ F
        (C and D can overlap once the event table exists)
```

## Explicitly NOT in v1 (deferred)

k8s/HA, CDN, managed DB, ClickHouse, real payments, React dashboard UI, edge resolution, white-label/loyalty/CRM roadmap surfaces (DESIGN §11).
