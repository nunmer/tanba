# Tanba — Implementation

How the system is built. Naming and endpoints here match `README.md` and `DESIGN.md`.

---

## 1. Components

```
            ┌─────────────┐
  tap/scan  │     CDN     │  caches landing pages + static
 ──────────▶│  / edge     │
            └──────┬──────┘
                   │ /r/{code}, /{slug}
            ┌──────▼──────────┐      resolve      ┌──────────┐
            │   public-api    │◀────────────────▶ │  Redis   │ hot routes, rate limit
            │ (no auth)       │      miss→DB       └────┬─────┘
            └──────┬──────────┘                        │
                   │ emit event (non-blocking)         │
                   ▼                                    │
            ┌─────────────┐   consume   ┌───────────────▼────┐
            │ Redis Stream│────────────▶│ analytics_worker   │ enrich, aggregate
            └─────────────┘             └─────────┬──────────┘
                                                  │ write
   ┌─────────────┐  manage   ┌──────────────┐     ▼
   │ dashboard   │──────────▶│  PostgreSQL  │◀── raw events + rollups
   │ (auth)      │  query    │  (tenant)    │
   └─────────────┘           └──────────────┘
```

The public app must answer in single-digit milliseconds on a cache hit. Everything off the hot path (analytics enrichment, aggregation) is asynchronous.

---

## 2. Data model

Deliberately few entities. Routing rules are folded into `Destination` rather than a separate rules table; physical media reference a smart link rather than owning logic. (Rationale in `DESIGN.md`.)

### Organization — tenant root
| field | notes |
|-------|-------|
| `id` | uuid, pk |
| `name` | |
| `slug` | unique, reserved for vanity URLs |
| `plan` | `free` \| `pro` \| `business` |
| `branding` | jsonb: logo, colors, default landing theme |
| `created_at` | |

### User / Membership — team
| User | |
|------|---|
| `id`, `email` (unique), `password_hash` (Argon2), `created_at` | |

| Membership | |
|------------|---|
| `id`, `user_id`, `org_id` | |
| `role` | `owner` \| `admin` \| `member` |

A user may belong to multiple organizations.

### Branch — location
| field | notes |
|-------|-------|
| `id` | uuid, pk |
| `org_id` | fk |
| `name`, `address`, `timezone` | |

### SmartLink — the permanent resource
| field | notes |
|-------|-------|
| `id` | uuid, pk |
| `org_id` | fk (tenant) |
| `branch_id` | fk, nullable → org-level link |
| `code` | short, unique, e.g. `7F3K29` |
| `slug` | optional vanity path, unique |
| `type` | `redirect` \| `multi` \| `landing` |
| `landing_config` | jsonb (used when `type=landing` or `multi`) |
| `is_active` | bool |
| `created_at` | |

`code` and `slug` are the two public lookup keys. Both resolve to the same SmartLink.

### Destination — target + routing rule
A SmartLink has one or more Destinations. The set of Destinations *is* the routing table for that link.

| field | notes |
|-------|-------|
| `id` | uuid, pk |
| `smartlink_id` | fk |
| `label` | "2GIS review", "Instagram", … |
| `url` | external target |
| `kind` | `review_2gis` \| `google_maps` \| `apple_maps` \| `yandex_maps` \| `instagram` \| `whatsapp` \| `telegram` \| `url` |
| `priority` | lower wins among matching rules |
| `weight` | for A/B split within the same priority |
| `match` | jsonb predicate (see §4) — `null` = always matches |
| `is_active` | bool |

### PhysicalMedium — provisioned tag/QR (optional inventory)
| field | notes |
|-------|-------|
| `id` | uuid, pk |
| `smartlink_id` | fk |
| `medium_type` | `nfc_card` \| `nfc_stand` \| `nfc_sticker` \| `qr_stand` \| `business_card` |
| `serial` | physical serial / batch |
| `provisioned_at` | |

### InteractionEvent — raw analytics
Append-only, partitioned by month.

| field | notes |
|-------|-------|
| `id` | uuid, pk |
| `smartlink_id` | fk |
| `org_id`, `branch_id` | denormalized for fast scoped queries |
| `entry` | `nfc` \| `qr` \| `link` |
| `destination_id` | resolved target, nullable |
| `device`, `os`, `browser` | parsed from UA |
| `country`, `city` | coarse geo from IP (IP itself not stored) |
| `visitor_hash` | salted hash for unique/repeat counting |
| `referrer` | nullable |
| `ts` | timestamptz |

### Subscription — billing
| field | notes |
|-------|-------|
| `id`, `org_id`, `plan`, `status`, `period_end`, `provider_ref` | |

**Tenant rule:** every tenant-scoped row carries `org_id`. All dashboard queries filter on it (§7). The public app reads by `code`/`slug` and writes events only.

---

## 3. Smart link lifecycle

1. Dashboard creates a SmartLink → generates a unique `code` (base32, collision-checked), optionally a `slug`.
2. One or more Destinations are attached.
3. The business prints/programs physical media with `https://tanba.kz/r/{code}` (or the slug). Optionally records a PhysicalMedium row.
4. Customer taps/scans → public app resolves and redirects.
5. Business edits Destinations any time → next request reflects the change after cache invalidation (§6). **No physical media touched.**

---

## 4. Routing engine

Lives in `packages/routing`, called by `public-api`.

### Resolution algorithm

```
resolve(code_or_slug, request_ctx) -> Resolution
  1. link = cache_get(key) or db_lookup(key)        # SmartLink + active Destinations
     if not link or not link.is_active: -> 404 page
  2. cache_set(key, link, ttl=ROUTE_CACHE_TTL)
  3. if link.type == "landing":  -> render landing
  4. candidates = [d for d in link.destinations
                     if d.is_active and matches(d.match, request_ctx)]
     if empty: -> link.fallback or 404
  5. group by priority; take lowest priority group
  6. if one candidate: pick it
     else: weighted pick by d.weight (A/B), seed = visitor_hash for stickiness
  7. emit_event(link, chosen, request_ctx)           # non-blocking
  8. -> 302 chosen.url
```

`request_ctx` is built once per request: parsed UA (device/os/browser), country/city from GeoIP, `visitor_hash`, `entry` type, referrer.

### `match` predicate (jsonb)

A small, evaluable DSL. `null` always matches. Examples:

```json
{ "platform": "ios" }
{ "country": ["KZ"] }
{ "platform": "android", "city": "Almaty" }
{ "schedule": { "days": ["sat","sun"], "from": "10:00", "to": "22:00", "tz": "Asia/Almaty" } }
```

Supported keys: `platform` (ios/android/other), `country`, `city`, `schedule`, `entry`. Evaluation is pure and side-effect free → trivially testable and cacheable.

### Rule types this composes into

- **Platform routing** — iOS → Apple Maps, Android → Google Maps, else 2GIS.
- **Regional routing** — `country`/`city` predicates.
- **A/B testing** — same `priority`, different `weight`, sticky per visitor.
- **Scheduled** — `schedule` predicate.
- **Default** — a Destination with `match: null` at highest `priority` number.

Adding a new rule type = adding a key to `matches()`; no schema change.

### Link types & multiple destinations

A SmartLink's `type` decides what a tap *does* with its destinations:

| `type` | Behavior |
|--------|----------|
| `redirect` | Resolves to **exactly one** destination and `302`s to it. Among matching destinations the lowest `priority` wins; ties at the same priority are an **A/B split by `weight`**, sticky per visitor. Two always-match (`match: null`) destinations at equal priority therefore behave as a 50/50 A/B test — a single visitor consistently sees one of them, *not* both. |
| `multi` | Renders the landing page as a **menu**, listing every active destination as a button. Use this when the customer should *choose* (e.g. leave a 2GIS review **and** follow on Instagram). |
| `landing` | Renders the full branded landing page (`landing_config`). |

Common gotcha: adding several "always" destinations to a `redirect` link and expecting a menu. That produces an A/B split; switch the link to `multi` for a menu. The dashboard surfaces this with an inline warning and a type switcher.

---

## 5. Endpoints

### Public app (no auth)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/r/{code}` | resolve short code → 302 or landing |
| GET | `/{slug}` | resolve vanity slug |
| GET | `/l/{code}` | force landing/multi-action view |
| POST | `/e` | beacon endpoint for client-side enrichment (optional) |
| GET | `/healthz` `/metrics` | liveness, Prometheus |

Responses set `Cache-Control` appropriately: landing pages cacheable at the edge; dynamic redirects are `private, no-store` (they branch on UA/geo).

### Dashboard app (auth required)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/register` `/auth/login` `/auth/refresh` | tokens |
| GET/POST | `/orgs` | list / create organizations |
| GET/PATCH | `/orgs/{id}` | read / update (branding) |
| GET/POST | `/orgs/{id}/branches` | branches |
| GET/POST | `/orgs/{id}/links` | smart links |
| GET/PATCH/DELETE | `/links/{id}` | manage a link |
| GET/POST | `/links/{id}/destinations` | routing targets |
| PATCH/DELETE | `/destinations/{id}` | |
| GET/POST | `/orgs/{id}/media` | physical media inventory |
| GET | `/orgs/{id}/analytics/summary` | rollup metrics |
| GET | `/orgs/{id}/analytics/timeseries` | time series |
| GET/POST/DELETE | `/orgs/{id}/members` | team |
| GET/POST | `/orgs/{id}/billing` | subscription |

All `/orgs/{id}/*` and resource routes enforce membership (§7).

---

## 6. Caching & invalidation

- **Key:** `route:{code}` and `route:{slug}` → serialized SmartLink + active Destinations.
- **TTL:** `ROUTE_CACHE_TTL` (e.g. 300s) as a safety net.
- **Write path:** any dashboard mutation to a SmartLink or its Destinations publishes an invalidation that deletes both keys. Next public request repopulates from Postgres.
- **Negative cache:** unknown codes cached briefly to absorb scanner/bot noise.
- **Edge:** landing pages get a short `s-maxage`; redirects are not edge-cached because they depend on per-request context.

This makes edits effectively immediate (delete-on-write) while the TTL bounds staleness if an invalidation is ever missed.

---

## 7. Multi-tenancy & auth

- **Auth:** dashboard issues JWT access + refresh; passwords hashed with Argon2. A dependency resolves the current user from the access token.
- **Scoping:** a FastAPI dependency loads the `Membership` for `(user, org_id)` on every org-scoped route; absence → 404 (not 403, to avoid leaking existence). For resource routes (`/links/{id}`), the resource's `org_id` is checked against the caller's memberships.
- **Roles:** `owner` > `admin` > `member`. Billing and member management require `admin`+.
- **Isolation:** all tenant rows carry `org_id`; queries are always filtered by it. Public app never reads tenant-private fields.

---

## 8. Analytics pipeline

1. **Emit (public app):** after resolution, push a compact event to the Redis stream `EVENT_STREAM`. Fire-and-forget; failures are logged, never block the redirect.
2. **Consume (worker):** `analytics_worker` reads the stream in a consumer group, batches, and:
   - parses UA → device/os/browser,
   - resolves IP → country/city via GeoIP, then **discards the IP**,
   - computes `visitor_hash = hash(salt + ip + ua + day)` for unique/repeat without identity,
   - inserts into `interaction_event` (monthly partitions),
   - updates rollup tables (`daily_link_stats`, `daily_org_stats`).
3. **Query (dashboard):** analytics endpoints read rollups for summaries and partitioned raw events for drill-down.

Scaling: more partitions in the consumer group = more worker replicas. At high volume, swap the raw store for ClickHouse behind the same worker interface (the worker writes through a thin store adapter).

---

## 9. Background jobs

Run by the worker process (or a scheduler):

- analytics consumption (continuous),
- daily/weekly rollup compaction,
- scheduled reports (premium),
- partition creation/retention,
- billing reconciliation with the payment provider.

---

## 10. Deployment

Single image, multiple entrypoints.

| Workload | Type | Scaling |
|----------|------|---------|
| `public-api` | Deployment | HPA on RPS/CPU; behind CDN + ingress; many replicas |
| `dashboard-api` | Deployment | small fixed pool |
| `analytics-worker` | Deployment | scaled by Redis stream lag |
| `postgres` | managed / StatefulSet | primary + read replica |
| `redis` | managed / StatefulSet | one primary, optional replica |

Notes:
- Public and dashboard are separate Deployments/Services so they scale and fail independently.
- Migrations run as a pre-deploy `Job` (`alembic upgrade head`).
- Config via `ConfigMap`/`Secret`; `JWT_SECRET`, DSNs in Secrets.
- `/healthz` for liveness/readiness; `/metrics` scraped by Prometheus.

---

## 11. Observability

- **Metrics (Prometheus):** request rate/latency per app, cache hit ratio, resolution time, redirect vs landing counts, stream lag, worker throughput, DB pool saturation.
- **Dashboards (Grafana):** public latency SLO, cache hit ratio, ingestion lag, errors by endpoint.
- **Logs:** structured JSON with `request_id`, `org_id` (when known), `code`. No PII, no raw IPs.
- **Alerts:** p99 resolution latency, cache hit ratio drop, stream lag growth, 5xx rate.

---

## 12. Testing

- **Routing:** pure-function tests over `matches()` and `resolve()` with synthetic `request_ctx` (platform/geo/schedule/AB matrices).
- **API:** httpx + ASGI transport against both apps.
- **Tenancy:** authorization tests asserting cross-org access returns 404.
- **Pipeline:** worker tests with an embedded Redis stream → assert enrichment, `visitor_hash` stability, rollup math.
