"""returns and exchanges

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-18

"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
CREATE TABLE returns (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,        -- Return / Exchange
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'Requested',
    requested_on    DATE NOT NULL,
    next_action     TEXT,
    notes           TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON returns (order_id);
CREATE INDEX ON returns (status);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE returns;")
