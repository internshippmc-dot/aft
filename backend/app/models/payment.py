import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_on: Mapped[datetime.date] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    payee: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(Text)
    box_id: Mapped[int | None] = mapped_column(ForeignKey("boxes.id", ondelete="SET NULL"))
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_by: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    box: Mapped["Box | None"] = relationship("Box")
