import datetime

from pydantic import BaseModel, Field


class ReturnCreate(BaseModel):
    order_number: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=32)
    reason: str | None = None
    requested_on: datetime.date
    next_action: str | None = None
    notes: str | None = None


class ReturnUpdate(BaseModel):
    status: str | None = None
    next_action: str | None = None
    notes: str | None = None


class ReturnOut(BaseModel):
    id: int
    order_number: str
    customer_name: str | None
    type: str
    reason: str | None
    status: str
    requested_on: datetime.date
    next_action: str | None
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
