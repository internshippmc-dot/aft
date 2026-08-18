import datetime
from decimal import Decimal

from pydantic import BaseModel


class ControlTowerCard(BaseModel):
    aft_number: str
    mf_number: str | None
    order_count: int
    amount_paid_inr: Decimal
    cn_tracking: str | None
    pl_status: str | None
    hexalog_arrival: datetime.date | None
    flight_date: datetime.date | None
    delhi_arrival: datetime.date | None
    labels_generated: int
    labels_total: int
    delivery_pct: int
    pipeline_stage: str
    next_action: str | None
    flagged: bool
    flag_reason: str | None


class ControlTowerUpdate(BaseModel):
    pipeline_stage: str | None = None
    next_action: str | None = None
    mf_number: str | None = None
    cn_tracking: str | None = None
    pl_status: str | None = None
    flagged: bool | None = None
    flag_reason: str | None = None
