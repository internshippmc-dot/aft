import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

STATUSES = ["Pending", "Paid", "Cancelled"]


class RefundRequest(Base):
    """Ops logs a customer refund with a screenshot of their payment QR
    code; the owner marks it paid once they've actually sent the money,
    which also drops a matching Payment record (type "Refund") on the
    books."""

    __tablename__ = "refund_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    qr_image: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="Pending")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    paid_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    order: Mapped["Order"] = relationship("Order")
