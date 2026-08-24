"""Shared order notes

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-24

"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
ALTER TABLE orders ADD COLUMN notes TEXT;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN notes;")
