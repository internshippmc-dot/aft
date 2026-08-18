# Actually Fair — Operations Console

Consignment tracking, order linkage, and data entry. See `PRD.md`, `TECH_SPEC.md`, and `SECURITY.md` for the full specification this build follows.

## What's implemented in this pass

This is the "core data entry app" slice: boxes, consignments, order assignment, manifest view, leg date entry, ETA prediction, universal search, the consolidation queue, login/roles/audit log. It does **not** yet include Shopify sync or XLSX import (PRD F8/F9) — the database tables for both exist (`sync_state`, `sheet_imports`) so they can be added without a migration. Orders start from the seed script, and can additionally be **quick-created while attaching**: paste an order number that doesn't exist yet (e.g. `#2000`) into a box, and the drawer offers a small create form (customer + items) that creates the order and attaches it in one go.

### Known gaps against SECURITY.md — close before real customer data goes in

- **TOTP/MFA is not enforced.** Login is email + password only. `totp_secret` exists on `users` but nothing writes or checks it.
- **No HIBP password check on set**, no forced-rotation-free minimum-length enforcement beyond Pydantic's `min_length` on the login form (there's no user self-service signup in this pass — accounts are seeded).
- **Rate limiting is in-process**, not Postgres-backed, and only wired on `/auth/login` and `/search`. Fine for the single-instance target in PRD.md, but re-verify if that assumption changes.
- **CSRF** uses a double-submit cookie, checked on every unsafe method via `require_csrf`/`require_role`.

## Stack

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16 on the backend; React 18 + TypeScript + Vite + TanStack Query on the frontend. Full rationale in `TECH_SPEC.md`.

## Run it

Requires Docker Desktop.

```
cp .env.example .env
# edit .env — set POSTGRES_PASSWORD and match it into DATABASE_URL
docker compose up --build
```

This starts three services:

- `db` — Postgres 16, port 5432
- `backend` — runs `alembic upgrade head`, then seeds demo data (skipped if users already exist), then serves the API on `http://localhost:8000` with `--reload`
- `frontend` — Vite dev server on `http://localhost:5173`

Open `http://localhost:5173`. Dev logins (see `backend/app/seed.py`):

| Role | Email | Password |
|---|---|---|
| owner | siddharth@actuallyfair.in | ChangeMe123! |
| ops | ops@actuallyfair.in | ChangeMe123! |
| viewer | viewer@actuallyfair.in | ChangeMe123! |

Change these before this instance is reachable by anyone but you.

### Health check

`GET http://localhost:8000/health` should return `{"status": "ok"}` once Postgres is reachable.

### Re-running the seed

The seed is idempotent by design (it no-ops if any user row exists). To reset and reseed from scratch:

```
docker compose down -v   # drops the db volume — destroys all data
docker compose up --build
```

## Repository layout

```
backend/app/
  models/        SQLAlchemy models, mirror schema.sql exactly
  schemas/       Pydantic request/response models
  api/           FastAPI routers — auth, boxes, consignments, orders, search, consolidation, admin
  domain/        Business logic with no I/O beyond the passed-in db session:
                   stages.py        derived box stage from leg events
                   eta.py           the ETA engine (PRD.md section 7)
                   assignment.py    bulk order-to-box attach + conflict detection
                   consolidation.py 10kg-minimum gauge math
                   legs.py          leg-event write/supersede (shared by box + consignment leg endpoints)
                   box_view.py      assembles BoxSummary/BoxManifest from ORM rows
  auth/          session cookies, argon2id hashing, CSRF, rate limiting, RBAC dependency
  alembic/       one migration — the whole of schema.sql, run verbatim
  seed.py        demo data loader, mirrors prototype.html's fixture boxes

frontend/src/
  routes/        Login, Shell (app frame), BoxDetailView, OrderDetailView
  components/    LegBar (the signature component — see TECH_SPEC.md section 9), SearchBar,
                 BoxListAside, NewBoxDrawer, LegEntryDrawer, AssignConsignmentDrawer, ConsolidationStrip, Toast
  lib/           typed API client, formatting helpers, the eta-note text builder
```

## Design choices that diverge slightly from TECH_SPEC.md

- **Leg-entry endpoints are per-object** (`POST /boxes/{aft}/legs`, `POST /consignments/{tracking_id}/legs`) rather than the single generic `POST /legs` with a numeric `scope_id` the spec sketches. The frontend and operators think in AFT numbers and tracking IDs, not internal row ids, so the human-readable identifier is the API surface.
- **ETA is computed on read, not cached in `eta_snapshots`.** At the scale this console runs at (PRD.md: under 10 concurrent users, and a demo/early-production order volume), recomputing per request is well inside the 300ms budget and avoids a staleness class of bug entirely. The table stays in the schema for when caching is actually needed.
- Assumption 1 in `PRD.md` (AFT number identifies a physical box, distinct from a consignment/shipment) is built as stated.

## Next, in rough order

1. Close the SECURITY.md gaps above before onboarding anyone besides the owner.
2. Shopify sync (`integrations/shopify` — not yet created).
3. XLSX importer with diff preview (`integrations/sheet` — not yet created).
4. Consolidation planner cost-per-kg view, message trigger queue, landed cost (PRD.md section 8, items 1–3) — the consolidation *gauge* is built; the cost-per-kg comparison and the message queue are not.
