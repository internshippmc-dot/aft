from decimal import Decimal

from pydantic import BaseModel, Field


class BoxStockItemCreate(BaseModel):
    product_title: str = Field(min_length=1, max_length=256)
    colour: str | None = None
    size: str | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price_inr: Decimal | None = None
    notes: str | None = None


class BoxStockItemOut(BaseModel):
    id: int
    product_title: str
    colour: str | None
    size: str | None
    quantity: int
    unit_price_inr: Decimal | None
    notes: str | None
