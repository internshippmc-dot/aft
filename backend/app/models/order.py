import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    shopify_order_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    order_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    placed_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    total_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str | None] = mapped_column(Text)
    financial_status: Mapped[str | None] = mapped_column(Text)
    ship_address: Mapped[dict | None] = mapped_column(JSONB)
    rto_status: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default="now()")
    # Manual override; null = derive stage from the linked box's legs (see app/api/orders.py get_order()).
    status_override: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    shipments: Mapped[list["Shipment"]] = relationship(
        "Shipment", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    shopify_line_item_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    product_title: Mapped[str] = mapped_column(Text, nullable=False)
    variant_title: Mapped[str | None] = mapped_column(Text)
    colour: Mapped[str | None] = mapped_column(Text)
    size: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_inr: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    box_item: Mapped["BoxItem | None"] = relationship(
        "BoxItem", back_populates="order_item", uselist=False
    )

    __table_args__ = (CheckConstraint("quantity > 0", name="order_items_quantity_check"),)
