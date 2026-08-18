import datetime
from decimal import Decimal

from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import EtaOut, OrderItemOut, ShipmentOut


class OrderItemCreate(BaseModel):
    product_title: str = Field(min_length=1, max_length=256)
    colour: str | None = None
    size: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price_inr: Decimal | None = None


class OrderCreateIn(BaseModel):
    """Quick-create payload for an order that was pasted into a box but doesn't
    exist yet — PRD F2 fast path for real order numbers like #2000."""
    order_number: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=256)
    phone: str | None = None
    city: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderSummary(BaseModel):
    order_number: str
    customer_name: str | None
    phone: str | None
    city: str | None
    total_inr: Decimal | None
    placed_at: datetime.datetime
    items: list[OrderItemOut]


class LegTimelineEntry(BaseModel):
    leg: str
    label: str
    date: datetime.date | None
    actual: bool


class OrderDetail(BaseModel):
    order_number: str
    customer_name: str | None
    phone: str | None
    email: str | None
    city: str | None
    total_inr: Decimal | None
    placed_at: datetime.datetime
    elapsed_days: int
    items: list[OrderItemOut]
    box_aft_number: str | None
    consignment_tracking_id: str | None
    stage: str
    timeline: list[LegTimelineEntry]
    eta: EtaOut | None
    sla_risk: bool
    shipment: ShipmentOut | None
