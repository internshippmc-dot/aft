from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models.box import Box

settings = get_settings()


@dataclass
class ConsolidationSummary:
    unassigned_weight_kg: Decimal
    unassigned_box_count: int
    minimum_kg: Decimal
    gauge_pct: float
    shortfall_kg: Decimal


def summarize(db: DbSession) -> ConsolidationSummary:
    """PRD section 8.1 — the hold-or-ship decision against the 10 kg Hexalog minimum."""
    boxes = db.scalars(select(Box).where(Box.consignment_id.is_(None))).all()
    weight = sum((b.gross_weight_kg or Decimal("0") for b in boxes), Decimal("0"))
    minimum = Decimal(str(settings.chargeable_minimum_kg))
    gauge_pct = float(min(weight / minimum, Decimal("1")) * 100) if minimum else 0.0
    shortfall = max(minimum - weight, Decimal("0"))
    return ConsolidationSummary(
        unassigned_weight_kg=weight,
        unassigned_box_count=len(boxes),
        minimum_kg=minimum,
        gauge_pct=gauge_pct,
        shortfall_kg=shortfall,
    )
