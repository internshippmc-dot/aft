import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    occurred_on: datetime.date
    type: str = Field(min_length=1, max_length=64)
    payee: str = Field(min_length=1, max_length=256)
    reference: str | None = None
    box_aft_number: str | None = None
    amount_inr: Decimal
    paid_by: str = Field(min_length=1, max_length=128)
    method: str | None = None
    notes: str | None = None


class PaymentOut(BaseModel):
    id: int
    occurred_on: datetime.date
    type: str
    payee: str
    reference: str | None
    box_aft_number: str | None
    amount_inr: Decimal
    paid_by: str
    method: str | None
    notes: str | None
    created_at: datetime.datetime
