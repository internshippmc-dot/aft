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

    consignment: Mapped["Consignment | None"] = relationship("Consignment", back_populates="boxes")
    items: Mapped[list["BoxItem"]] = relationship(
        "BoxItem", back_populates="box", cascade="all, delete-orphan"
    )
    shipments: Mapped[list["ManufacturerShipment"]] = relationship(
        "ManufacturerShipment", back_populates="box"
    )
    stock_items: Mapped[list["BoxStockItem"]] = relationship(
        "BoxStockItem", back_populates="box", cascade="all, delete-orphan"
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


class ManufacturerShipment(Base):
    """Logged the moment a shipment leaves the manufacturer for Hexalog,
    before it's known which AFT/flight it'll be consolidated into.
    box_id is null until it's actually batched onto one."""
    __tablename__ = "manufacturer_shipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    so_number: Mapped[str | None] = mapped_column(Text)
    so_date: Mapped[datetime.date | None] = mapped_column()
    tracking_id: Mapped[str | None] = mapped_column(Text)
    boxes_received: Mapped[int | None] = mapped_column(Integer)
    so_qty: Mapped[int | None] = mapped_column(Integer)
    box_id: Mapped[int | None] = mapped_column(ForeignKey("boxes.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    box: Mapped["Box | None"] = relationship("Box", back_populates="shipments")


class BoxStockItem(Base):
    """Stock/inventory bought without a specific customer order behind it
    (e.g. "50 handbags" purchased speculatively) but riding in this AFT box."""
    __tablename__ = "box_stock_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    box_id: Mapped[int] = mapped_column(ForeignKey("boxes.id", ondelete="CASCADE"), nullable=False)
    product_title: Mapped[str] = mapped_column(Text, nullable=False)
    colour: Mapped[str | None] = mapped_column(Text)
    size: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")

    box: Mapped["Box"] = relationship("Box", back_populates="stock_items")

    __table_args__ = (CheckConstraint("quantity > 0", name="box_stock_items_quantity_check"),)
