import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Consignment(Base):
    __tablename__ = "consignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    carrier: Mapped[str] = mapped_column(Text, nullable=False, default="Hexalog")
    chargeable_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    freight_cost_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    boxes: Mapped[list["Box"]] = relationship("Box", back_populates="consignment")
