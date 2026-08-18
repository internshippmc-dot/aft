import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    order_number: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=64)
    body: str | None = None


class MessageOut(BaseModel):
    id: int
    type: str
    order_number: str
    box_aft_number: str | None
    status: str
    body: str | None
    created_at: datetime.datetime
    sent_at: datetime.datetime | None
