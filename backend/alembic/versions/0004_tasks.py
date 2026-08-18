"""tasks and reminders

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-18

"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
CREATE TABLE tasks (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title           TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'Medium',   -- High / Medium / Low
    entity_type     TEXT,                              -- 'order' | 'box' | null
    entity_id       TEXT,                              -- order_number or aft_number
    due_on          DATE,
    status          TEXT NOT NULL DEFAULT 'Open',      -- Open / Done
    notes           TEXT,
    created_by      BIGINT REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX ON tasks (status, due_on);
CREATE INDEX ON tasks (entity_type, entity_id);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE tasks;")
