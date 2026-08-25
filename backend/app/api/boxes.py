from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.audit import record_audit
from app.auth.deps import get_current_user, require_csrf, require_ops
from app.db import get_db
from app.domain.assignment import _find_order, attach_orders_to_box, detach_item_from_box, parse_order_numbers
from app.domain.box_view import build_manifest, build_summary
from app.domain.legs import write_leg_event
from app.domain.orders import create_order
from app.models.box import Box, BoxItem, BoxStockItem, ManufacturerShipment
from app.models.leg import LegEvent, LegName, LegScope, LegSource
from app.models.user import User
from app.schemas.box import (
    AttachFailureOut,
    AttachOrdersRequest,
    AttachResultOut,
    BoxCreate,
    BoxManifest,
    BoxSummary,
    BoxUpdate,
    LegEventCreate,
)
from app.schemas.box_stock_item import BoxStockItemCreate
from app.schemas.manufacturer_shipment import AttachShipmentsRequest

router = APIRouter(prefix="/boxes", tags=["boxes"])


def _box_options():
    return (
        selectinload(Box.items).selectinload(BoxItem.order_item),
        selectinload(Box.consignment),
        selectinload(Box.shipments),
        selectinload(Box.stock_items),
    )


def _attach_shipments(db: DbSession, box: Box, shipment_ids: list[int]) -> list[int]:
    """Consolidates already-logged, still-unbatched manufacturer shipments
    onto this box. Raises 409 if any requested id doesn't exist or is
    already attached elsewhere — silently grabbing someone else's shipment
    would misattribute a real physical consignment."""
    if not shipment_ids:
        return []
    rows = db.scalars(select(ManufacturerShipment).where(ManufacturerShipment.id.in_(shipment_ids))).all()
    found_ids = {r.id for r in rows}
    missing = [i for i in shipment_ids if i not in found_ids]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No manufacturer shipment(s) with id {missing}.")
    already_batched = [r.id for r in rows if r.box_id is not None and r.box_id != box.id]
    if already_batched:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Shipment(s) {already_batched} are already attached to another AFT batch.",
        )
    for r in rows:
        r.box_id = box.id
    db.flush()
    return [r.id for r in rows]


def _get_box_or_404(db: DbSession, aft_number: str) -> Box:
    box = db.scalar(
        select(Box).where(Box.aft_number == aft_number.strip().upper()).options(*_box_options())
    )
    if box is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No box with AFT number {aft_number}.")
    return box


@router.get("", response_model=list[BoxSummary])
def list_boxes(filter: str = "all", _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    query = select(Box).options(*_box_options())
    boxes = db.scalars(query).all()

    summaries = [build_summary(db, b) for b in boxes]

    if filter == "queue":
        summaries = [s for s in summaries if s.tracking_id is None]
    elif filter == "transit":
        summaries = [s for s in summaries if s.stage not in ("Packing", "Landed")]

    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


def _attach_result_out(result) -> AttachResultOut:
    return AttachResultOut(
        attached=result.attached,
        already_in_this_box=result.already_in_this_box,
        missing=result.missing,
        failed=[AttachFailureOut(order_number=f.order_number, reason=f.reason) for f in result.failed],
    )


def _create_missing_orders(db, request, body, user) -> list[str]:
    """Quick-create any new_orders payloads that don't exist yet (PRD F2 fast
    path for real order numbers like #2000). Returns the order numbers to attach."""
    numbers = []
    for data in body.new_orders:
        order = _find_order(db, data.order_number)
        if order is None:
            order = create_order(db, data)
            record_audit(
                db, request, user, "order.create", "order", data.order_number,
                after={"order_number": data.order_number, "customer_name": data.customer_name,
                       "item_count": len(data.items)},
            )
        numbers.append(data.order_number)
    return numbers


@router.post("", response_model=BoxManifest, status_code=status.HTTP_201_CREATED)
def create_box(
    body: BoxCreate,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    aft = body.aft_number.strip().upper()
    existing = db.scalar(select(Box).where(Box.aft_number == aft).options(*_box_options()))
    if existing is not None:
        # PRD F1 — duplicate entry surfaces the existing box instead of erroring.
        # The drawer is reused for "attach orders to an existing box", so still
        # process any pasted order numbers rather than silently dropping them.
        order_numbers = parse_order_numbers(body.orders_raw or "")
        order_numbers += _create_missing_orders(db, request, body, user)
        if order_numbers:
            result = attach_orders_to_box(db, existing, order_numbers, user)
            record_audit(
                db, request, user, "box.attach_orders", "box", existing.aft_number,
                after={"attached": result.attached, "missing": result.missing,
                       "failed": [f.order_number for f in result.failed]},
            )
            db.commit()
            return build_manifest(db, existing, attach=_attach_result_out(result))
        return build_manifest(db, existing)

    box = Box(
        aft_number=aft,
        manufacturer=body.manufacturer,
        gross_weight_kg=body.gross_weight_kg,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(box)
    db.flush()

    if body.dispatched_on is not None:
        db.add(
            LegEvent(
                scope_type=LegScope.box,
                scope_id=box.id,
                leg=LegName.MFG_DISPATCH,
                occurred_on=body.dispatched_on,
                source=LegSource.manual,
                entered_by=user.id,
            )
        )

    attach = None
    order_numbers = parse_order_numbers(body.orders_raw or "")
    order_numbers += _create_missing_orders(db, request, body, user)
    if order_numbers:
        result = attach_orders_to_box(db, box, order_numbers, user)
        attach = _attach_result_out(result)

    attached_shipment_ids = _attach_shipments(db, box, body.shipment_ids)

    record_audit(
        db, request, user, "box.create", "box", aft,
        after={"aft_number": aft, "manufacturer": body.manufacturer,
               "gross_weight_kg": str(body.gross_weight_kg) if body.gross_weight_kg else None,
               "attached": attach.attached if attach else None,
               "missing": attach.missing if attach else None,
               "failed": [f.order_number for f in attach.failed] if attach else None,
               "shipment_ids": attached_shipment_ids},
    )

    db.commit()
    box = db.scalar(select(Box).where(Box.id == box.id).options(*_box_options()))
    return build_manifest(db, box, attach=attach)


@router.get("/{aft_number}", response_model=BoxManifest)
def get_box(aft_number: str, _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    box = _get_box_or_404(db, aft_number)
    return build_manifest(db, box)


@router.delete("/{aft_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_box(
    aft_number: str, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    """Deletes the AFT batch itself, not what's inside it: orders in it go
    back to unbatched (box_items cascades), and any payments, customer
    messages, or manufacturer shipments linked to it survive — they just
    lose the AFT reference (all SET NULL, per schema.sql)."""
    box = _get_box_or_404(db, aft_number)
    before = {
        "aft_number": box.aft_number,
        "manufacturer": box.manufacturer,
        "order_count": len({bi.order_item.order_id for bi in box.items}),
    }
    record_audit(db, request, user, "box.delete", "box", box.aft_number, before=before)
    db.delete(box)
    db.commit()


@router.post("/{aft_number}/shipments", response_model=BoxManifest)
def attach_shipments(
    aft_number: str, body: AttachShipmentsRequest, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    attached_ids = _attach_shipments(db, box, body.shipment_ids)
    record_audit(db, request, user, "box.attach_shipments", "box", box.aft_number, after={"shipment_ids": attached_ids})
    db.commit()
    box = _get_box_or_404(db, aft_number)
    return build_manifest(db, box)


@router.post("/{aft_number}/stock-items", response_model=BoxManifest, status_code=status.HTTP_201_CREATED)
def add_stock_item(
    aft_number: str, body: BoxStockItemCreate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    """Stock/inventory bought without a specific customer order behind it
    (e.g. handbags bought speculatively) but riding in this AFT box."""
    box = _get_box_or_404(db, aft_number)
    item = BoxStockItem(
        box_id=box.id, product_title=body.product_title, colour=body.colour, size=body.size,
        quantity=body.quantity, unit_price_inr=body.unit_price_inr, notes=body.notes, created_by=user.id,
    )
    db.add(item)
    db.flush()
    record_audit(
        db, request, user, "box.stock_item_add", "box", box.aft_number,
        after={"product_title": body.product_title, "quantity": body.quantity},
    )
    db.commit()
    box = _get_box_or_404(db, aft_number)
    return build_manifest(db, box)


@router.delete("/{aft_number}/stock-items/{item_id}", response_model=BoxManifest)
def delete_stock_item(
    aft_number: str, item_id: int, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    item = next((i for i in box.stock_items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No stock item {item_id} on {aft_number}.")
    record_audit(db, request, user, "box.stock_item_delete", "box", box.aft_number, before={"product_title": item.product_title})
    db.delete(item)
    db.commit()
    box = _get_box_or_404(db, aft_number)
    return build_manifest(db, box)


@router.patch("/{aft_number}", response_model=BoxManifest)
def update_box(
    aft_number: str,
    body: BoxUpdate,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    fields = ("manufacturer", "gross_weight_kg", "notes")

    def _snapshot() -> dict:
        return {f: str(getattr(box, f)) if getattr(box, f) is not None else None for f in fields}

    before = _snapshot()
    for field in fields:
        if field in body.model_fields_set:
            setattr(box, field, getattr(body, field))
    record_audit(db, request, user, "box.update", "box", box.aft_number, before=before, after=_snapshot())
    db.commit()
    box = _get_box_or_404(db, aft_number)
    return build_manifest(db, box)


@router.post("/{aft_number}/items", response_model=AttachResultOut)
def attach_items(
    aft_number: str,
    body: AttachOrdersRequest,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    order_numbers = parse_order_numbers(body.orders_raw or "")
    order_numbers += _create_missing_orders(db, request, body, user)
    if not order_numbers:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Paste order numbers or fill in the create forms first.")

    result = attach_orders_to_box(db, box, order_numbers, user)

    record_audit(
        db, request, user, "box.attach_orders", "box", box.aft_number,
        after={"attached": result.attached, "missing": result.missing,
               "failed": [f.order_number for f in result.failed]},
    )
    db.commit()

    return AttachResultOut(
        attached=result.attached,
        already_in_this_box=result.already_in_this_box,
        missing=result.missing,
        failed=[AttachFailureOut(order_number=f.order_number, reason=f.reason) for f in result.failed],
    )


@router.delete("/{aft_number}/items/{order_item_id}", dependencies=[Depends(require_csrf)])
def detach_item(
    aft_number: str,
    order_item_id: int,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    ok = detach_item_from_box(db, box, order_item_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="That item is not in this box.")
    record_audit(db, request, user, "box.detach_item", "box_item", str(order_item_id), before={"box": box.aft_number})
    db.commit()
    return {"ok": True}


@router.post("/{aft_number}/legs", response_model=BoxManifest)
def add_box_leg(
    aft_number: str,
    body: LegEventCreate,
    request: Request,
    user: User = Depends(require_ops),
    db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    try:
        leg = LegName(body.leg)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Unknown leg '{body.leg}'.")

    before = write_leg_event(db, LegScope.box, box.id, leg, body.occurred_on, user)
    record_audit(
        db, request, user, "leg.write", "box", box.aft_number,
        before=before, after={"leg": leg.value, "occurred_on": str(body.occurred_on)},
    )
    db.commit()

    box = _get_box_or_404(db, aft_number)
    return build_manifest(db, box)
