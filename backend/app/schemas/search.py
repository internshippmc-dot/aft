from pydantic import BaseModel


class OrderHit(BaseModel):
    order_number: str
    customer_name: str | None
    aft_number: str | None


class BoxHit(BaseModel):
    aft_number: str
    tracking_id: str | None
    order_count: int
    stage: str


class SearchResults(BaseModel):
    orders: list[OrderHit]
    boxes: list[BoxHit]
