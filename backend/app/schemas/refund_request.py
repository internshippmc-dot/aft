import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RefundRequestCreate(BaseModel):
    order_number: str = Field(min_length=1, max_length=64)
    amount_inr: Decimal
    qr_image: str | None = None  # data: URI, the customer's payment QR screenshot
    reason: str | None = None
    # If order_number doesn't exist yet (a customer who ordered outside
    # Shopify, or one Shopify sync hasn't picked up), providing a customer
    # name quick-creates a minimal order instead of failing with a 404.
    customer_name: str | None = None
    phone: str | None = None


class RefundRequestOut(BaseModel):
    id: int
    order_number: str
    customer_name: str | None
    amount_inr: Decimal
    qr_image: str | None
    reason: str | None
    status: str
    requested_by_name: str | None
    paid_by_name: str | None
    paid_at: datetime.datetime | None
    created_at: datetime.datetime
