-- Actually Fair Operations Console — initial schema
-- PostgreSQL 16. Apply as the first Alembic migration.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS citext;

-- ---------------------------------------------------------------- identity

CREATE TYPE user_role AS ENUM ('owner', 'ops', 'viewer');

CREATE TABLE users (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email           CITEXT NOT NULL UNIQUE,
    full_name       TEXT NOT NULL,
    password_hash   TEXT NOT NULL,              -- argon2id
    role            user_role NOT NULL DEFAULT 'viewer',
    totp_secret     TEXT,                       -- encrypted at rest
    totp_enrolled_at TIMESTAMPTZ,
    failed_attempts SMALLINT NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ,
    disabled_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,           -- 256-bit random, stored hashed
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    ip              INET,
    user_agent      TEXT,
    revoked_at      TIMESTAMPTZ
);
CREATE INDEX ON sessions (user_id) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------- commerce

CREATE TABLE customers (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shopify_customer_id BIGINT UNIQUE,
    full_name       TEXT NOT NULL,
    phone_e164      TEXT,
    email           CITEXT,
    opt_out         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON customers (phone_e164);
CREATE INDEX customers_name_trgm ON customers USING gin (full_name gin_trgm_ops);

CREATE TABLE orders (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    shopify_order_id BIGINT UNIQUE,
    order_number    TEXT NOT NULL UNIQUE,       -- TEXT, never integer
    customer_id     BIGINT REFERENCES customers(id),
    placed_at       TIMESTAMPTZ NOT NULL,
    total_inr       NUMERIC(12,2),
    payment_method  TEXT,                       -- prepaid | cod
    financial_status TEXT,
    ship_address    JSONB,
    rto_status      TEXT,
    archived_at     TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON orders (placed_at DESC);
CREATE INDEX ON orders (customer_id);

CREATE TABLE order_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    shopify_line_item_id BIGINT UNIQUE,
    product_title   TEXT NOT NULL,
    variant_title   TEXT,
    colour          TEXT,
    size            TEXT,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_inr  NUMERIC(12,2)
);
CREATE INDEX ON order_items (order_id);

-- ---------------------------------------------------------------- logistics

CREATE TABLE consignments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tracking_id     TEXT NOT NULL UNIQUE,       -- Hexalog AWB
    carrier         TEXT NOT NULL DEFAULT 'Hexalog',
    chargeable_weight_kg NUMERIC(8,3),
    freight_cost_inr NUMERIC(12,2),
    notes           TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE boxes (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aft_number      TEXT NOT NULL UNIQUE,       -- uppercased, trimmed on write
    consignment_id  BIGINT REFERENCES consignments(id) ON DELETE SET NULL,
    manufacturer    TEXT,
    gross_weight_kg NUMERIC(8,3),
    notes           TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON boxes (consignment_id);
-- the consolidation queue
CREATE INDEX boxes_unassigned ON boxes (created_at) WHERE consignment_id IS NULL;

-- the join that answers "what is in this box"
CREATE TABLE box_items (
    box_id          BIGINT NOT NULL REFERENCES boxes(id) ON DELETE CASCADE,
    order_item_id   BIGINT NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    added_by        BIGINT REFERENCES users(id),
    added_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (box_id, order_item_id)
);
-- one item cannot sit in two boxes
CREATE UNIQUE INDEX box_items_one_box_per_item ON box_items (order_item_id);

CREATE TYPE leg_name AS ENUM (
    'MFG_DISPATCH', 'CN_WAREHOUSE', 'FLIGHT',
    'DELHI_WAREHOUSE', 'LAST_MILE_HANDOVER'
);
CREATE TYPE leg_scope AS ENUM ('consignment', 'box');
CREATE TYPE leg_source AS ENUM ('manual', 'sheet', 'shopify', 'carrier');

CREATE TABLE leg_events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scope_type      leg_scope NOT NULL,
    scope_id        BIGINT NOT NULL,
    leg             leg_name NOT NULL,
    occurred_on     DATE NOT NULL,
    source          leg_source NOT NULL DEFAULT 'manual',
    entered_by      BIGINT REFERENCES users(id),
    entered_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at   TIMESTAMPTZ
);
CREATE UNIQUE INDEX leg_events_current
    ON leg_events (scope_type, scope_id, leg)
    WHERE superseded_at IS NULL;

-- last mile, per order
CREATE TABLE shipments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    courier         TEXT,
    awb             TEXT,
    courier_price_inr NUMERIC(10,2),
    handed_over_on  DATE,
    delivered_on    DATE,
    status          TEXT
);
CREATE INDEX ON shipments (awb);
CREATE INDEX ON shipments (order_id);

-- ---------------------------------------------------------------- computed

CREATE TABLE eta_snapshots (
    box_id          BIGINT PRIMARY KEY REFERENCES boxes(id) ON DELETE CASCADE,
    p50_date        DATE NOT NULL,
    p80_date        DATE NOT NULL,
    sample_n        INTEGER NOT NULL,
    confidence      TEXT NOT NULL,              -- high | low
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- plumbing

CREATE TABLE sheet_imports (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filename        TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    row_count       INTEGER,
    committed_at    TIMESTAMPTZ,
    committed_by    BIGINT REFERENCES users(id),
    diff            JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sync_state (
    key             TEXT PRIMARY KEY,
    cursor_value    TEXT,
    last_success_at TIMESTAMPTZ,
    last_error      TEXT
);

CREATE TABLE audit_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id   BIGINT REFERENCES users(id),
    actor_ip        INET,
    action          TEXT NOT NULL,              -- box.create, leg.write, ...
    object_type     TEXT NOT NULL,
    object_id       TEXT NOT NULL,
    before          JSONB,
    after           JSONB,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON audit_log (occurred_at DESC);
CREATE INDEX ON audit_log (object_type, object_id);

-- append only, enforced at the database
REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC;
