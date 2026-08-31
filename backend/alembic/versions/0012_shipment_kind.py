"""Forward vs reverse shipments

A return pickup is a physically separate shipment (its own AWB, its own
courier) from the original delivery, and an order can have both. Adds a
`kind` column (forward/reverse) and links reverse shipments back to the
return case they belong to.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-26

"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
ALTER TABLE shipments ADD COLUMN kind TEXT NOT NULL DEFAULT 'forward' CHECK (kind IN ('forward', 'reverse'));
ALTER TABLE shipments ADD COLUMN return_id BIGINT REFERENCES returns(id) ON DELETE SET NULL;
CREATE INDEX ON shipments (return_id);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("ALTER TABLE shipments DROP COLUMN return_id; ALTER TABLE shipments DROP COLUMN kind;")
