import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.box import Box
from app.models.leg import LegEvent, LegName, LegScope

# TECH_SPEC.md section 7 — the four legs the box-level LegBar tracks.
# LAST_MILE_HANDOVER is order/shipment-scoped and handled separately.
BOX_LEGS: list[LegName] = [
    LegName.MFG_DISPATCH,
    LegName.CN_WAREHOUSE,
    LegName.FLIGHT,
    LegName.DELHI_WAREHOUSE,
]

STAGE_LABELS = {
    None: "Packing",
    LegName.MFG_DISPATCH: "Dispatched",
    LegName.CN_WAREHOUSE: "CN warehouse",
    LegName.FLIGHT: "In the air",
    LegName.DELHI_WAREHOUSE: "Landed",
}


def effective_legs(db: DbSession, box: Box) -> dict[LegName, datetime.date]:
    """PRD F3/F7 — a date entered on a consignment applies to every box inside it.
    Consignment-scoped events take precedence; box-scoped events fill in legs
    entered before the box joined a consignment (e.g. MFG_DISPATCH)."""
    result: dict[LegName, datetime.date] = {}

    box_events = db.scalars(
        select(LegEvent).where(
            LegEvent.scope_type == LegScope.box,
            LegEvent.scope_id == box.id,
            LegEvent.superseded_at.is_(None),
        )
    )
    for ev in box_events:
        result[ev.leg] = ev.occurred_on

    if box.consignment_id is not None:
        cons_events = db.scalars(
            select(LegEvent).where(
                LegEvent.scope_type == LegScope.consignment,
                LegEvent.scope_id == box.consignment_id,
                LegEvent.superseded_at.is_(None),
            )
        )
        for ev in cons_events:
            result[ev.leg] = ev.occurred_on

    return result


def compute_stage(legs: dict[LegName, datetime.date]) -> str:
    highest = None
    for leg in BOX_LEGS:
        if leg in legs:
            highest = leg
    return STAGE_LABELS[highest]
