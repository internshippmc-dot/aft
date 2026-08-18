import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CustomerMessage(Base):
    __tablename__ = "customer_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    box_id: Mapped[int | None] = mapped_column(ForeignKey("boxes.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="Pending")
    body: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    sent_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    order: Mapped["Order"] = relationship("Order")
    box: Mapped["Box | None"] = relationship("Box")
