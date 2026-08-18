"""payments

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-18

"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
CREATE TABLE payments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_on     DATE NOT NULL,
    type            TEXT NOT NULL,        -- Manufacturer / Hexalog / Logistics / Refund / Other
    payee           TEXT NOT NULL,
    reference       TEXT,
    box_id          BIGINT REFERENCES boxes(id) ON DELETE SET NULL,
    amount_inr      NUMERIC(12,2) NOT NULL,
    paid_by         TEXT NOT NULL,
    method          TEXT,                 -- Bank Transfer / UPI / Wallet / Other
    notes           TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON payments (occurred_on DESC);
CREATE INDEX ON payments (box_id);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE payments;")
