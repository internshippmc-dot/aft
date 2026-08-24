"""Manual order status override

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-22

"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
ALTER TABLE orders ADD COLUMN status_override TEXT;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN status_override;")
