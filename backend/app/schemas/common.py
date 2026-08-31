import datetime

from pydantic import BaseModel


class EtaOut(BaseModel):
    p50_date: datetime.date
    p80_date: datetime.date
    sample_n: int
    confidence: str


class OrderItemOut(BaseModel):
    id: int
    product_title: str
    colour: str | None
    size: str | None
    quantity: int


class ShipmentOut(BaseModel):
    id: int
    courier: str | None
    awb: str | None
    status: str | None
    handed_over_on: datetime.date | None
    delivered_on: datetime.date | None
    kind: str = "forward"
