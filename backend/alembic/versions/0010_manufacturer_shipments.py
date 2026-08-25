"""Manufacturer -> Hexalog shipment intake, decoupled from AFT batches

Replaces the flat so_number/so_date/boxes_received/so_qty columns added to
boxes in 0009 (never deployed) with a proper table: a shipment can be
logged the moment it leaves the manufacturer, before anyone knows which
AFT/flight it'll eventually be consolidated into. box_id is null until
it's actually batched.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-25

"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
ALTER TABLE boxes DROP COLUMN so_number;
ALTER TABLE boxes DROP COLUMN so_date;
ALTER TABLE boxes DROP COLUMN boxes_received;
ALTER TABLE boxes DROP COLUMN so_qty;

CREATE TABLE manufacturer_shipments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    manufacturer    TEXT,
    so_number       TEXT,                       -- e.g. HXL/27-28/SZX/096
    so_date         DATE,
    tracking_id     TEXT,                       -- e.g. SF1572395806095
    boxes_received  INTEGER,
    so_qty          INTEGER,
    box_id          BIGINT REFERENCES boxes(id) ON DELETE SET NULL,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON manufacturer_shipments (box_id);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("""
        DROP TABLE manufacturer_shipments;
        ALTER TABLE boxes ADD COLUMN so_number TEXT;
        ALTER TABLE boxes ADD COLUMN so_date DATE;
        ALTER TABLE boxes ADD COLUMN boxes_received INTEGER;
        ALTER TABLE boxes ADD COLUMN so_qty INTEGER;
    """)
