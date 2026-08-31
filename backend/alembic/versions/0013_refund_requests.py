"""Refund requests — QR-code payout queue

Ops enters the customer/order + amount and attaches a screenshot of the
customer's payment QR code; the owner (whoever can actually move money)
marks it paid once they've sent it, which also drops a matching payment
record on the books.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-31

"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

# Kept identical to /schema.sql at the repo root. If you change one, change both.
SCHEMA_SQL = """
CREATE TABLE refund_requests (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount_inr      NUMERIC(12,2) NOT NULL,
    qr_image        TEXT,                 -- data: URI (base64), the customer's payment QR screenshot
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Paid', 'Cancelled')),
    requested_by    BIGINT REFERENCES users(id),
    paid_by         BIGINT REFERENCES users(id),
    paid_at         TIMESTAMPTZ,
    payment_id      BIGINT REFERENCES payments(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON refund_requests (order_id);
CREATE INDEX ON refund_requests (status);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE refund_requests;")
