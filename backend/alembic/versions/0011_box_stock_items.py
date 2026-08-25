"""Non-order stock/inventory items on an AFT batch

Some shipments include product bought as stock (e.g. handbags) rather
than against a specific customer order. box_items requires an
order_item_id, so this is a parallel table for items with no linked order.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-25

"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
CREATE TABLE box_stock_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    box_id          BIGINT NOT NULL REFERENCES boxes(id) ON DELETE CASCADE,
    product_title   TEXT NOT NULL,
    colour          TEXT,
    size            TEXT,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_inr  NUMERIC(12,2),
    notes           TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON box_stock_items (box_id);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE box_stock_items;")
