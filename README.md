# Tanba

Cloud-based customer interaction platform for offline businesses. Physical touchpoints (NFC tags, QR codes, smart links) carry a **permanent Tanba URL**; all destinations, business logic, and analytics live in the cloud and can be changed without ever reprogramming the physical medium.

```
https://tanba.kz/r/7F3K29        # short code
https://tanba.kz/starbucks-almaty # custom slug
```

The URL never changes. The backend decides what happens at request time.

> Tanba is **not an NFC store**. NFC is one of many entry points into the platform.

---

## Why

Static NFC/QR solutions bake the destination into the medium. Changing where a tag points means physically rewriting every tag, and there is zero visibility into how customers interact. Tanba moves the destination into a server-side routing layer, so a business can repoint thousands of deployed tags instantly and measure every tap.

---

## Features

- **Dynamic routing** — server resolves the final destination per request (platform-aware, geo-aware, A/B split, scheduled).
- **Permanent identifiers** — physical media never need reprogramming.
- **Landing pages** — single-action redirect, multi-action menu, or full landing page per smart link.
- **Analytics** — taps, scans, unique/repeat visitors, device/OS/browser, coarse geo, referral, timestamp — without storing PII.
- **Multi-tenant dashboard** — organizations, branches, smart links, team members, billing, branding.
- **Multi-location** — one organization, many branches, centralized administration.

---

## Architecture at a glance

Two deployable applications over a shared data and cache layer.

| App | Auth | Responsibility |
|-----|------|----------------|
| **Public** (`public-api`) | none | route resolution, landing pages, redirect logic, analytics ingestion |
| **Dashboard** (`dashboard-api`) | required | auth, org/branch/link management, analytics queries, team, billing |

The split exists because the two have opposite profiles: the public app is read-heavy, latency-critical, cache-fronted, and exposed to the world; the dashboard is write-heavy, low-traffic, and authenticated. See `DESIGN.md`.

---

## Tech stack

| Concern | Choice |
|---------|--------|
| Language | Python 3.12 |
| API framework | FastAPI (async) |
| Primary store | PostgreSQL 16 (multi-tenant) |
| Cache / hot routes | Redis 7 |
| Event stream | Redis Streams (Kafka-ready) |
| Analytics store | PostgreSQL (partitioned) → ClickHouse at scale |
| Background work | Worker process consuming the event stream |
| Migrations | Alembic |
| Auth | JWT access + refresh, Argon2 hashing |
| Packaging | `uv` / `pyproject.toml` |
| Runtime | Docker, Kubernetes |
| Observability | Prometheus + Grafana, structured JSON logs |

---

## Repository layout

Monorepo. The two apps share models, schemas, and infra glue.

```
tanba/
├── apps/
│   ├── public/            # public-api: routing, landing, ingestion (no auth)
│   │   ├── main.py
│   │   ├── routing/       # resolution engine
│   │   ├── landing/       # landing page rendering
│   │   └── ingest/        # analytics event emit
│   └── dashboard/         # dashboard-api: management surface (auth)
│       ├── main.py
│       ├── auth/
│       ├── orgs/
│       ├── links/
│       ├── analytics/
│       └── billing/
├── packages/
│   ├── core/              # shared: models, db session, settings, errors
│   │   ├── models/        # Organization, Branch, SmartLink, Destination, ...
│   │   ├── db.py
│   │   └── settings.py
│   ├── routing/           # rule evaluation (used by public app)
│   └── analytics/         # event schema, enrichment, aggregation
├── workers/
│   └── analytics_worker.py
├── migrations/            # Alembic
├── deploy/
│   ├── docker/
│   └── k8s/               # manifests / helm
├── tests/
├── docker-compose.yml     # local dev
├── pyproject.toml
├── README.md
├── IMPLEMENTATION.md
└── DESIGN.md
```

---

## Quick start (local)

Prerequisites: Docker + Docker Compose, Python 3.12, `uv`.

```bash
# 1. clone
git clone https://github.com/<you>/tanba.git && cd tanba

# 2. dependencies
uv sync

# 3. infra (postgres, redis)
docker compose up -d postgres redis

# 4. configure
cp .env.example .env        # then edit

# 5. migrate
uv run alembic upgrade head

# 6. seed a demo org + smart link (optional)
uv run python -m scripts.seed_demo

# 7. run the apps
uv run uvicorn apps.public.main:app   --port 8001 --reload   # public
uv run uvicorn apps.dashboard.main:app --port 8002 --reload   # dashboard

# 8. run the analytics worker
uv run python -m workers.analytics_worker
```

Then:

- Public:   `http://localhost:8001/r/<code>`
- Dashboard: `http://localhost:8002/docs`

---

## Environment

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres DSN |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | signing key for dashboard tokens |
| `JWT_ACCESS_TTL` / `JWT_REFRESH_TTL` | token lifetimes |
| `ROUTE_CACHE_TTL` | seconds a resolved route stays cached |
| `PUBLIC_BASE_URL` | e.g. `https://tanba.kz` |
| `GEOIP_DB_PATH` | path to the IP→geo database |
| `EVENT_STREAM` | Redis stream key for interaction events |
| `ENV` | `local` \| `staging` \| `production` |

See `.env.example`.

---

## Testing

```bash
uv run pytest                    # all
uv run pytest tests/routing      # routing engine
uv run pytest -m "not slow"
```

---

## Deployment

Both apps build from the same base image, selected by entrypoint. Public scales horizontally behind a CDN; dashboard runs a smaller fixed pool; the analytics worker is a separate deployment scaled by stream lag. Manifests live in `deploy/k8s/`. Details in `IMPLEMENTATION.md` → Deployment.

---

## Documentation

- **`IMPLEMENTATION.md`** — data model, routing engine, endpoints, analytics pipeline, caching, auth, deployment.
- **`DESIGN.md`** — architecture decisions, rationale, tradeoffs, scalability strategy.

---

## License

Proprietary. © Tanba.
