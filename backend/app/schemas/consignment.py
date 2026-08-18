import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.box import BoxSummary


class ConsignmentCreate(BaseModel):
    tracking_id: str = Field(min_length=1, max_length=64)
    carrier: str = "Hexalog"
    chargeable_weight_kg: Decimal | None = None
    freight_cost_inr: Decimal | None = None
    notes: str | None = None
    box_afts: list[str] = Field(default_factory=list)


class AttachBoxesRequest(BaseModel):
    box_afts: list[str] = Field(min_length=1)


class ConsignmentOut(BaseModel):
    id: int
    tracking_id: str
    carrier: str
    chargeable_weight_kg: Decimal | None
    freight_cost_inr: Decimal | None
    notes: str | None
    shortfall_kg: Decimal
    created_at: datetime.datetime
    boxes: list[BoxSummary]
