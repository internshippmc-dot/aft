from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.config import get_settings
from app.db import get_db
from app.domain.box_view import build_summary
from app.domain.legs import write_leg_event
from app.models.box import Box, BoxItem
from app.models.consignment import Consignment
from app.models.leg import LegName, LegScope
from app.models.user import User
from app.schemas.box import LegEventCreate
from app.schemas.consignment import AttachBoxesRequest, ConsignmentCreate, ConsignmentOut

router = APIRouter(prefix="/consignments", tags=["consignments"])
settings = get_settings()


def _get_consignment_or_404(db: DbSession, tracking_id: str) -> Consignment:
    row = db.scalar(
        select(Consignment)
        .where(Consignment.tracking_id == tracking_id.strip())
        .options(selectinload(Consignment.boxes).selectinload(Box.items).selectinload(BoxItem.order_item))
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No consignment with tracking ID {tracking_id}.")
    return row


def _to_out(db: DbSession, c: Consignment) -> ConsignmentOut:
    weight = c.chargeable_weight_kg or Decimal("0")
    minimum = Decimal(str(settings.chargeable_minimum_kg))
    shortfall = max(minimum - weight, Decimal("0"))
    return ConsignmentOut(
        id=c.id,
        tracking_id=c.tracking_id,
        carrier=c.carrier,
        chargeable_weight_kg=c.chargeable_weight_kg,
        freight_cost_inr=c.freight_cost_inr,
        notes=c.notes,
        shortfall_kg=shortfall,
        created_at=c.created_at,
        boxes=[build_summary(db, b) for b in c.boxes],
    )


@router.post("", response_model=ConsignmentOut, status_code=status.HTTP_201_CREATED)
def create_consignment(
    body: ConsignmentCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    tracking_id = body.tracking_id.strip()
    existing = db.scalar(select(Consignment).where(Consignment.tracking_id == tracking_id))
    if existing is not None:
        # PRD F3 — entering a tracking ID that already exists opens it. Still
        # attach any newly-passed boxes rather than dropping them.
        attached, missing = [], []
        for aft in body.box_afts:
            box = db.scalar(select(Box).where(Box.aft_number == aft.strip().upper()))
            if box is None:
                missing.append(aft)
                continue
            box.consignment_id = existing.id
            attached.append(box.aft_number)
        if attached or missing:
            record_audit(
                db, request, user, "consignment.attach_boxes", "consignment", tracking_id,
                after={"attached": attached, "missing": missing},
            )
            db.commit()
        existing = db.scalar(
            select(Consignment)
            .where(Consignment.id == existing.id)
            .options(selectinload(Consignment.boxes).selectinload(Box.items).selectinload(BoxItem.order_item))
        )
        return _to_out(db, existing)

    c = Consignment(
        tracking_id=tracking_id,
        carrier=body.carrier,
        chargeable_weight_kg=body.chargeable_weight_kg,
        freight_cost_inr=body.freight_cost_inr,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(c)
    db.flush()

    attached, missing = [], []
    for aft in body.box_afts:
        box = db.scalar(select(Box).where(Box.aft_number == aft.strip().upper()))
        if box is None:
            missing.append(aft)
            continue
        box.consignment_id = c.id
        attached.append(box.aft_number)

    record_audit(
        db, request, user, "consignment.create", "consignment", tracking_id,
        after={"tracking_id": tracking_id, "boxes_attached": attached, "boxes_missing": missing},
    )
    db.commit()

    c = db.scalar(
        select(Consignment)
        .where(Consignment.id == c.id)
        .options(selectinload(Consignment.boxes).selectinload(Box.items).selectinload(BoxItem.order_item))
    )
    return _to_out(db, c)


@router.get("/{tracking_id}", response_model=ConsignmentOut)
def get_consignment(tracking_id: str, _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    c = _get_consignment_or_404(db, tracking_id)
    return _to_out(db, c)


@router.post("/{tracking_id}/boxes", response_model=ConsignmentOut)
def attach_boxes(
    tracking_id: str,
    body: AttachBoxesRequest,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    c = _get_consignment_or_404(db, tracking_id)
    attached, missing = [], []
    for aft in body.box_afts:
        box = db.scalar(select(Box).where(Box.aft_number == aft.strip().upper()))
        if box is None:
            missing.append(aft)
            continue
        box.consignment_id = c.id
        attached.append(box.aft_number)

    record_audit(
        db, request, user, "consignment.attach_boxes", "consignment", c.tracking_id,
        after={"attached": attached, "missing": missing},
    )
    db.commit()

    c = _get_consignment_or_404(db, tracking_id)
    return _to_out(db, c)


@router.post("/{tracking_id}/legs", response_model=ConsignmentOut)
def add_consignment_leg(
    tracking_id: str,
    body: LegEventCreate,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    """PRD F7 — a date entered here applies to every box and order inside."""
    c = _get_consignment_or_404(db, tracking_id)
    try:
        leg = LegName(body.leg)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown leg '{body.leg}'.")

    before = write_leg_event(db, LegScope.consignment, c.id, leg, body.occurred_on, user)
    record_audit(
        db, request, user, "leg.write", "consignment", c.tracking_id,
        before=before, after={"leg": leg.value, "occurred_on": str(body.occurred_on)},
    )
    db.commit()

    c = _get_consignment_or_404(db, tracking_id)
    return _to_out(db, c)
