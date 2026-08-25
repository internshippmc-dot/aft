"""Manufacturer -> China warehouse shipment tracking fields on boxes

Matches the operator's own tracking sheet columns: Date, SO NO, Box_Recv,
SO NO / UTR Qty (Tracking ID already exists as boxes.cn_tracking).

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-25

"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
ALTER TABLE boxes ADD COLUMN so_number TEXT;
ALTER TABLE boxes ADD COLUMN so_date DATE;
ALTER TABLE boxes ADD COLUMN boxes_received INTEGER;
ALTER TABLE boxes ADD COLUMN so_qty INTEGER;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE boxes DROP COLUMN so_number;
        ALTER TABLE boxes DROP COLUMN so_date;
        ALTER TABLE boxes DROP COLUMN boxes_received;
        ALTER TABLE boxes DROP COLUMN so_qty;
    """)
