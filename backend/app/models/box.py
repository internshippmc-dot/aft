import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Box(Base):
    __tablename__ = "boxes"

    id: Mapped[int] = mapped_column(primary_key=True)
    aft_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    consignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("consignments.id", ondelete="SET NULL")
    )
    manufacturer: Mapped[str | None] = mapped_column(Text)
    gross_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    # China Control Tower (see domain/control_tower.py)
    mf_number: Mapped[str | None] = mapped_column(Text)
    cn_tracking: Mapped[str | None] = mapped_column(Text)
    pl_status: Mapped[str | None] = mapped_column(Text)
    pipeline_stage: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    flag_reason: Mapped[str | None] = mapped_column(Text)

    # Manufacturer -> China warehouse shipment tracking sheet. Tracking ID
    # from that sheet is cn_tracking above; these are its other columns.
    so_number: Mapped[str | None] = mapped_column(Text)
    so_date: Mapped[datetime.date | None] = mapped_column()
    boxes_received: Mapped[int | None] = mapped_column(Integer)
    so_qty: Mapped[int | None] = mapped_column(Integer)

    consignment: Mapped["Consignment | None"] = relationship("Consignment", back_populates="boxes")
    items: Mapped[list["BoxItem"]] = relationship(
        "BoxItem", back_populates="box", cascade="all, delete-orphan"
    )


class BoxItem(Base):
    __tablename__ = "box_items"

    box_id: Mapped[int] = mapped_column(ForeignKey("boxes.id", ondelete="CASCADE"), primary_key=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), primary_key=True, unique=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    box: Mapped["Box"] = relationship("Box", back_populates="items")
    order_item: Mapped["OrderItem"] = relationship("OrderItem", back_populates="box_item")

    __table_args__ = (CheckConstraint("quantity > 0", name="box_items_quantity_check"),)
