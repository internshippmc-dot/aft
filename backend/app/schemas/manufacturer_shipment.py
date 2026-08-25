import datetime

from pydantic import BaseModel, Field


class ManufacturerShipmentCreate(BaseModel):
    manufacturer: str | None = None
    so_number: str | None = None
    so_date: datetime.date | None = None
    tracking_id: str | None = None
    boxes_received: int | None = None
    so_qty: int | None = None


class ManufacturerShipmentUpdate(BaseModel):
    """PATCH /manufacturer-shipments/{id}. Every field optional — only
    provided fields change. Can only be edited while unbatched (box_id null)."""
    manufacturer: str | None = None
    so_number: str | None = None
    so_date: datetime.date | None = None
    tracking_id: str | None = None
    boxes_received: int | None = None
    so_qty: int | None = None


class ManufacturerShipmentOut(BaseModel):
    id: int
    manufacturer: str | None
    so_number: str | None
    so_date: datetime.date | None
    tracking_id: str | None
    boxes_received: int | None
    so_qty: int | None
    box_aft_number: str | None
    created_at: datetime.datetime


class AttachShipmentsRequest(BaseModel):
    shipment_ids: list[int] = Field(min_length=1)
