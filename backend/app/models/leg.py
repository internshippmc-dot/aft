import datetime
import enum
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Text
from sqlalchemy.dialects.postgresql import ENUM, NUMERIC, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class LegName(str, enum.Enum):
    MFG_DISPATCH = "MFG_DISPATCH"
    CN_WAREHOUSE = "CN_WAREHOUSE"
    FLIGHT = "FLIGHT"
    DELHI_WAREHOUSE = "DELHI_WAREHOUSE"
    LAST_MILE_HANDOVER = "LAST_MILE_HANDOVER"


class LegScope(str, enum.Enum):
    consignment = "consignment"
    box = "box"


class LegSource(str, enum.Enum):
    manual = "manual"
    sheet = "sheet"
    shopify = "shopify"
    carrier = "carrier"


leg_name_enum = ENUM(LegName, name="leg_name", create_type=False)
leg_scope_enum = ENUM(LegScope, name="leg_scope", create_type=False)
leg_source_enum = ENUM(LegSource, name="leg_source", create_type=False)


class LegEvent(Base):
    __tablename__ = "leg_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[LegScope] = mapped_column(leg_scope_enum, nullable=False)
    scope_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leg: Mapped[LegName] = mapped_column(leg_name_enum, nullable=False)
    occurred_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    source: Mapped[LegSource] = mapped_column(leg_source_enum, nullable=False, default=LegSource.manual)
    entered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    entered_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    superseded_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    courier: Mapped[str | None] = mapped_column(Text)
    awb: Mapped[str | None] = mapped_column(Text)
    courier_price_inr: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 2))
    handed_over_on: Mapped[datetime.date | None] = mapped_column(Date)
    delivered_on: Mapped[datetime.date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default="forward")
    return_id: Mapped[int | None] = mapped_column(ForeignKey("returns.id", ondelete="SET NULL"))

    order: Mapped["Order"] = relationship("Order", back_populates="shipments")


class EtaSnapshot(Base):
    __tablename__ = "eta_snapshots"

    box_id: Mapped[int] = mapped_column(ForeignKey("boxes.id", ondelete="CASCADE"), primary_key=True)
    p50_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    p80_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    sample_n: Mapped[int] = mapped_column(nullable=False)
    confidence: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
