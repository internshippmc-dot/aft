"""resources/SOPs and customer messages queue

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-18

"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
CREATE TABLE resources (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type            TEXT NOT NULL,        -- Link / SOP
    title           TEXT NOT NULL,
    category        TEXT,
    url             TEXT,
    description     TEXT,
    process_text    TEXT,
    created_by      BIGINT REFERENCES users(id),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tracked queue only, matching the prototype's actual behaviour — no real
-- WhatsApp/SMS send integration. Ops mark Pending -> Sent by hand.
CREATE TABLE customer_messages (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type            TEXT NOT NULL,
    order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    box_id          BIGINT REFERENCES boxes(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'Pending',
    body            TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at         TIMESTAMPTZ
);
CREATE INDEX ON customer_messages (order_id);
CREATE INDEX ON customer_messages (status);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE customer_messages; DROP TABLE resources;")
