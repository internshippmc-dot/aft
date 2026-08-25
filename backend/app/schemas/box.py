import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import EtaOut, OrderItemOut
from app.schemas.manufacturer_shipment import ManufacturerShipmentOut
from app.schemas.order import OrderCreateIn


class BoxCreate(BaseModel):
    aft_number: str = Field(min_length=1, max_length=64)
    manufacturer: str | None = None
    gross_weight_kg: Decimal | None = None
    notes: str | None = None
    dispatched_on: datetime.date | None = None
    orders_raw: str | None = None  # bulk paste, PRD F1 + F2 combined at creation
    new_orders: list[OrderCreateIn] = Field(default_factory=list)  # quick-create for pasted-but-unknown numbers
    shipment_ids: list[int] = Field(default_factory=list)  # consolidate pending manufacturer shipments in at creation


class BoxUpdate(BaseModel):
    """Editable box fields — PATCH /boxes/{aft_number}. None means "not
    provided"; explicit null clears the field (checked via model_fields_set)."""
    manufacturer: str | None = None
    gross_weight_kg: Decimal | None = None
    notes: str | None = None


class AttachOrdersRequest(BaseModel):
    orders_raw: str | None = None
    new_orders: list[OrderCreateIn] = Field(default_factory=list)


class AttachFailureOut(BaseModel):
    order_number: str
    reason: str


class AttachResultOut(BaseModel):
    attached: list[str]
    already_in_this_box: list[str]
    missing: list[str] = []  # pasted order numbers that don't exist yet — quick-creatable
    failed: list[AttachFailureOut]


class LegsOut(BaseModel):
    MFG_DISPATCH: datetime.date | None = None
    CN_WAREHOUSE: datetime.date | None = None
    FLIGHT: datetime.date | None = None
    DELHI_WAREHOUSE: datetime.date | None = None


class BoxSummary(BaseModel):
    aft_number: str
    tracking_id: str | None
    manufacturer: str | None
    gross_weight_kg: Decimal | None
    order_count: int
    stage: str
    legs: LegsOut
    eta: EtaOut | None
    sla_risk: bool
    created_at: datetime.datetime
    shipments: list[ManufacturerShipmentOut] = Field(default_factory=list)


class ManifestOrderOut(BaseModel):
    order_number: str
    customer_name: str | None
    city: str | None
    placed_at: datetime.datetime
    total_inr: Decimal | None
    items: list[OrderItemOut]


class BoxManifest(BaseModel):
    aft_number: str
    tracking_id: str | None
    manufacturer: str | None
    gross_weight_kg: Decimal | None
    notes: str | None
    stage: str
    legs: LegsOut
    eta: EtaOut | None
    sla_risk: bool
    order_count: int
    units_total: int
    value_total: Decimal
    oldest_order_placed_at: datetime.datetime | None
    orders: list[ManifestOrderOut]
    shipments: list[ManufacturerShipmentOut] = Field(default_factory=list)
    # set on POST /boxes only, when orders were pasted at creation — lets the
    # drawer report which orders failed to attach instead of silently dropping them
    attach: AttachResultOut | None = None


class LegEventCreate(BaseModel):
    leg: str
    occurred_on: datetime.date
