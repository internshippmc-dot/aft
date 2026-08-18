"""China Control Tower — actually_fair_logistics_prototype_v28.html lines
5650-5688 (window.renderControl15, the final/authoritative kanban version).

Column order matters (matches the prototype exactly) and is the contract
the frontend groups cards by.
"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.domain.stages import effective_legs
from app.models.box import Box
from app.models.leg import LegName, Shipment
from app.models.payment import Payment
from app.schemas.control_tower import ControlTowerCard

PIPELINE_STAGES = [
    "Manufacturer → Hexalog",
    "Sitting in Hexalog",
    "On Flight",
    "Delhi Warehouse",
    "In Transit",
    "Delivered",
    "Feedback",
    "Closed",
]


def default_stage(db: DbSession, box: Box) -> str:
    """A box with no manually-set pipeline_stage yet gets a sensible default
    derived from its box-level leg events, mirroring how far along it
    physically is. Ops can always override via PATCH from there on."""
    legs = effective_legs(db, box)
    if LegName.DELHI_WAREHOUSE in legs:
        return "Delhi Warehouse"
    if LegName.FLIGHT in legs:
        return "On Flight"
    if LegName.CN_WAREHOUSE in legs:
        return "Sitting in Hexalog"
    return "Manufacturer → Hexalog"


def build_card(db: DbSession, box: Box) -> ControlTowerCard:
    order_ids = {bi.order_item.order_id for bi in box.items}
    order_count = len(order_ids)

    amount_paid = db.scalar(
        select(func.coalesce(func.sum(Payment.amount_inr), Decimal(0))).where(Payment.box_id == box.id)
    ) or Decimal(0)

    labelled = delivered = 0
    if order_ids:
        shipments = db.scalars(select(Shipment).where(Shipment.order_id.in_(order_ids)))
        seen_awb: set[int] = set()
        seen_delivered: set[int] = set()
        for s in shipments:
            if s.awb and s.order_id not in seen_awb:
                seen_awb.add(s.order_id)
            if s.delivered_on and s.order_id not in seen_delivered:
                seen_delivered.add(s.order_id)
        labelled = len(seen_awb)
        delivered = len(seen_delivered)

    legs = effective_legs(db, box)
    delivery_pct = round(delivered / order_count * 100) if order_count else 0

    return ControlTowerCard(
        aft_number=box.aft_number,
        mf_number=box.mf_number,
        manufacturer=box.manufacturer,
        order_count=order_count,
        amount_paid_inr=amount_paid,
        cn_tracking=box.cn_tracking,
        pl_status=box.pl_status,
        hexalog_arrival=legs.get(LegName.CN_WAREHOUSE),
        flight_date=legs.get(LegName.FLIGHT),
        delhi_arrival=legs.get(LegName.DELHI_WAREHOUSE),
        labels_generated=labelled,
        labels_total=order_count,
        delivery_pct=delivery_pct,
        pipeline_stage=box.pipeline_stage or default_stage(db, box),
        next_action=box.next_action,
        flagged=box.flagged,
        flag_reason=box.flag_reason,
    )
