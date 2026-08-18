from decimal import Decimal

from pydantic import BaseModel


class ConsolidationOut(BaseModel):
    unassigned_weight_kg: Decimal
    unassigned_box_count: int
    minimum_kg: Decimal
    gauge_pct: float
    shortfall_kg: Decimal
