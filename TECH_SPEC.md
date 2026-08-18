# Technical Specification — Actually Fair Operations Console

Version 0.2 · August 2026 · Companion to `PRD.md`, `SECURITY.md`, `schema.sql`

This document is written to be executed. An implementing agent should follow the file layout, contracts, and build order exactly, and should not substitute libraries or restructure directories.

---

## 1. Architecture

```
Browser (React SPA)
   │  HTTPS, JSON, session cookie + CSRF token
   ▼
FastAPI application
   ├── auth        session, MFA, RBAC, audit
   ├── api         REST endpoints
   ├── domain      pure business logic, no I/O
   ├── integrations Shopify client, XLSX importer
   └── jobs        APScheduler: sync, ETA recompute, backup
   │
   ▼
PostgreSQL 16   ──► nightly encrypted dump to object storage
```

Single deployable. No microservices. No message broker in v1.

## 2. Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 | Matches the existing Order Automator codebase, so the Shopify client, size mapping, and colour resolution port over |
| ORM | SQLAlchemy 2.0 + Alembic | Migrations are non-negotiable once real fulfilment data lives here |
| DB | PostgreSQL 16 | Needs real date arithmetic, partial indexes, and concurrent writers. SQLite does not survive two ops people entering legs at once |
| Frontend | React 18 + TypeScript + Vite | |
| State | TanStack Query | Server state is the whole app; a client store would duplicate it |
| Styling | Plain CSS with custom properties | See section 9 |
| Auth | Server-side sessions in Postgres, `argon2id`, TOTP | See `SECURITY.md` |
| Jobs | APScheduler in-process | Under 10 users and 3 jobs. Celery is unjustified |
| Tests | pytest, Vitest | |

## 3. Repository layout

```
dashboard/
├── backend/
│   ├── app/
│   │   ├── main.py                 FastAPI app, middleware, router mount
│   │   ├── config.py               pydantic-settings, env only, no defaults for secrets
│   │   ├── db.py                   engine, session dependency
│   │   ├── models/                 SQLAlchemy models, one file per aggregate
│   │   ├── schemas/                Pydantic request and response models
│   │   ├── api/                    auth.py, orders.py, boxes.py, consignments.py, legs.py, search.py, consolidation.py
│   │   ├── domain/                 eta.py, assignment.py, stages.py, consolidation.py
│   │   ├── auth/                   sessions, password, rbac
│   │   ├── audit.py                write-path audit helper
│   │   └── seed.py                 demo data loader
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── routes/                 login, boxes, box detail, order detail
│   │   ├── components/             LegBar, Manifest, SearchBar, EntryPanel
│   │   ├── lib/                    api client, formatting
│   │   └── styles/tokens.css
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 4. Data model

Full DDL in `schema.sql`.

**`consignments`** — one Hexalog shipment. `tracking_id` unique. Carries `chargeable_weight_kg`, `freight_cost_inr`, `carrier`.

**`boxes`** — one carton. `aft_number` unique, uppercased and trimmed on write. `consignment_id` nullable; null means it sits in the consolidation queue.

**`box_items`** — the join that answers the core question. Links `box_id` to `order_item_id` with a `quantity`. A unique index on `order_item_id` prevents the same item living in two boxes.

**`leg_events`** — `(scope_type, scope_id, leg, occurred_on, entered_by, source)`. Scope is `consignment` or `box`.

**`orders`, `order_items`, `customers`** — mirrored from Shopify. `orders.order_number` is TEXT, never integer.

**`eta_snapshots`** — computed predictions with `p50_date`, `p80_date`, `sample_n`, `computed_at`.

**`audit_log`** — append only. `UPDATE`/`DELETE` revoked from the application role at the database level.

Derived stage is not a column. It is computed from the highest completed leg, in `domain/stages.py`.

## 5. Shopify integration

Deferred past this build pass — see PRD §6 F8. `sync_state` table exists in the schema so this can be added without a migration.

## 6. XLSX import

Deferred past this build pass — see PRD §6 F9. `sheet_imports` table exists in the schema so this can be added without a migration.

## 7. ETA engine

`domain/eta.py`

```python
LEGS = ["MFG_DISPATCH", "CN_WAREHOUSE", "FLIGHT", "DELHI_WAREHOUSE"]

def leg_stats(session, leg, window=20) -> LegStats:
    """Median and p80 duration in days from the previous leg,
    over the trailing `window` completed consignments."""

def predict(session, box) -> Prediction:
    """Sum remaining leg medians onto the latest actual leg date.
    Returns p50, p80, sample_n, confidence."""
```

Rules:
- Duration samples come from consignment-scoped events only. Box-scoped events are noisier.
- `sample_n < 5` for any remaining leg returns `confidence = "low"` and uses `DEFAULT_LEG_DAYS` from config.
- Sundays skipped for `FLIGHT` and `DELHI_WAREHOUSE`.
- Recompute on: leg event write, box-to-consignment assignment, nightly.
- Never return a prediction earlier than today.

## 8. API

All routes under `/api/v1`. Session cookie plus `X-CSRF-Token` on every unsafe method.

```
POST   /auth/login                 email + password → session (MFA stubbed for v1)
POST   /auth/logout
GET    /auth/me

GET    /search?q=                  grouped results across all types
GET    /orders/{order_number}      order, items, box, consignment, timeline, eta
GET    /boxes                      filter: unassigned, in_transit, landed
POST   /boxes                      create by aft_number
GET    /boxes/{aft_number}         manifest, legs, eta, weight
POST   /boxes/{aft_number}/items   attach orders; body accepts a list
DELETE /boxes/{aft_number}/items/{order_item_id}
POST   /consignments               create by tracking_id
POST   /consignments/{id}/boxes    attach boxes
POST   /legs                       {scope_type, scope_id, leg, occurred_on}
GET    /consolidation              unassigned weight vs 10 kg minimum
GET    /admin/audit                owner only
```

Errors return `{code, message, detail}`. The message is written for the operator, names the object, and states the fix. No stack traces reach the client.

## 9. Frontend

**Design direction.** Monochrome, dense, keyboard-first, with a single red used only for exceptions and overdue states. Reference: `prototype.html`.

Rules:
- No gradient backgrounds, no glass, no drop shadows beyond a 1px rule, no emoji, no centred hero.
- Border radius is 2px everywhere or nothing.
- All identifiers, dates, weights, and money set in a monospace face with tabular numerals.
- Row height 32px.
- `/` focuses search, `n` opens new box, `Esc` closes panels.

**Signature component — `LegBar`.** Four segments, one per leg. Solid fill for a leg with an actual date, diagonal hatch for a predicted leg, red for a leg that has breached its expected duration.

**Tokens** (`styles/tokens.css`):

```css
--paper:#F2F2F0; --surface:#FFFFFF; --ink:#0F1011;
--graphite:#6A6D6E; --rule:#D9DAD7; --signal:#D9231E;
--mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
```

## 10. Deployment

Local dev: Docker Compose (Postgres + backend + frontend dev server). `.env`, never committed. Migrations run on startup.

## 11. Build order (this pass)

1. Scaffold, config, Alembic against Postgres in Docker.
2. Users, sessions, password hashing, RBAC dependency, audit decorator (TOTP fields exist in schema, enforcement deferred).
3. Schema from `schema.sql` as the first migration.
4. Boxes, consignments, assignment, leg events, ETA engine.
5. Frontend shell, login, box list, manifest, `LegBar`, order detail, search, new-box drawer.
6. Seed data for a usable demo.

## 12. Open decisions (unchanged from v0.1)

- Whether one AFT number can ever span two consignments. Currently modelled as no.
- Whether landed cost allocates by weight or by unit count.
- Shopify sync and XLSX import are scaffolded (tables exist) but not wired up in this pass — see PRD F8/F9.
