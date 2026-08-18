"""China Control Tower fields on boxes

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-18

"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
ALTER TABLE boxes ADD COLUMN mf_number TEXT;
ALTER TABLE boxes ADD COLUMN cn_tracking TEXT;
ALTER TABLE boxes ADD COLUMN pl_status TEXT;
ALTER TABLE boxes ADD COLUMN pipeline_stage TEXT;
ALTER TABLE boxes ADD COLUMN next_action TEXT;
ALTER TABLE boxes ADD COLUMN flagged BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE boxes ADD COLUMN flag_reason TEXT;
CREATE INDEX ON boxes (pipeline_stage);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE boxes DROP COLUMN mf_number;
        ALTER TABLE boxes DROP COLUMN cn_tracking;
        ALTER TABLE boxes DROP COLUMN pl_status;
        ALTER TABLE boxes DROP COLUMN pipeline_stage;
        ALTER TABLE boxes DROP COLUMN next_action;
        ALTER TABLE boxes DROP COLUMN flagged;
        ALTER TABLE boxes DROP COLUMN flag_reason;
    """)
