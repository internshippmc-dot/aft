import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.config import get_settings
from app.db import get_db
from app.domain.box_view import build_eta
from app.domain.orders import create_order
from app.domain.stages import BOX_LEGS, STAGE_LABELS, compute_stage, effective_legs
from app.models.box import Box, BoxItem
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.common import OrderItemOut, ShipmentOut
from app.schemas.order import (
    ORDER_STATUS_OVERRIDES,
    LegTimelineEntry,
    OrderCreateIn,
    OrderDetail,
    OrderListItem,
    OrderUpdate,
)

router = APIRouter(prefix="/orders", tags=["orders"])
settings = get_settings()


def _find_order(db: DbSession, order_number: str) -> Order:
    order = db.scalar(
        select(Order)
        .where(Order.order_number == order_number)
        .options(selectinload(Order.items).selectinload(OrderItem.box_item), selectinload(Order.customer))
    )
    if order is None:
        alt = order_number[1:] if order_number.startswith("#") else "#" + order_number
        order = db.scalar(
            select(Order)
            .where(Order.order_number == alt)
            .options(selectinload(Order.items).selectinload(OrderItem.box_item), selectinload(Order.customer))
        )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No order {order_number}.")
    return order


@router.get("", response_model=list[OrderListItem])
def list_orders(q: str | None = None, _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    query = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.box_item), selectinload(Order.customer))
        .order_by(Order.placed_at.desc())
        .limit(500)
    )
    if q:
        needle = f"%{q.strip()}%"
        query = query.join(Order.customer, isouter=True).where(
            (Order.order_number.ilike(needle)) | (Customer.full_name.ilike(needle))
        )
    out: list[OrderListItem] = []
    for order in db.scalars(query):
        box: Box | None = None
        for item in order.items:
            if item.box_item is not None:
                box = db.get(Box, item.box_item.box_id)
                break
        ship = order.ship_address or {}
        stage = order.status_override or (
            compute_stage(effective_legs(db, box)) if box else "Awaiting box assignment"
        )
        out.append(
            OrderListItem(
                order_number=order.order_number,
                customer_name=order.customer.full_name if order.customer else None,
                city=ship.get("city"),
                total_inr=order.total_inr,
                placed_at=order.placed_at,
                item_count=len(order.items),
                box_aft_number=box.aft_number if box else None,
                source="shopify" if order.shopify_order_id else "manual",
                stage=stage,
                status_override=order.status_override,
                notes=order.notes,
            )
        )
    return out


@router.post("", response_model=OrderDetail, status_code=status.HTTP_201_CREATED)
def create_order_endpoint(
    body: OrderCreateIn, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    if db.scalar(select(Order).where(Order.order_number == body.order_number)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Order {body.order_number} already exists.")
    order = create_order(db, body)
    record_audit(
        db, request, user, "order.create", "order", order.order_number,
        after={"customer_name": body.customer_name, "item_count": len(body.items)},
    )
    db.commit()
    return get_order(order.order_number, user, db)


@router.get("/{order_number}", response_model=OrderDetail)
def get_order(order_number: str, _user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    order = _find_order(db, order_number)

    box: Box | None = None
    for item in order.items:
        if item.box_item is not None:
            box = db.scalar(
                select(Box)
                .where(Box.id == item.box_item.box_id)
                .options(selectinload(Box.consignment))
            )
            break

    now = datetime.datetime.now(datetime.timezone.utc)
    placed = order.placed_at if order.placed_at.tzinfo else order.placed_at.replace(tzinfo=datetime.timezone.utc)
    elapsed_days = (now - placed).days

    legs = effective_legs(db, box) if box else {}
    stage = order.status_override or (compute_stage(legs) if box else "Awaiting box assignment")
    eta = build_eta(db, box) if box else None

    timeline: list[LegTimelineEntry] = []
    for leg in BOX_LEGS:
        timeline.append(
            LegTimelineEntry(
                leg=leg.value,
                label=STAGE_LABELS[leg],
                date=legs.get(leg) or (eta.p50_date if eta and leg == _first_pending_leg(legs) else None),
                actual=leg in legs,
            )
        )

    sla_risk = False
    if eta is not None:
        sla_risk = (eta.p80_date - placed.date()).days > settings.sla_days

    ship = order.ship_address or {}
    items_out = [
        OrderItemOut(id=i.id, product_title=i.product_title, colour=i.colour, size=i.size, quantity=i.quantity)
        for i in order.items
    ]
    shipment = max(order.shipments, key=lambda s: s.id, default=None)
    shipment_out = (
        ShipmentOut(
            id=shipment.id,
            courier=shipment.courier,
            awb=shipment.awb,
            status=shipment.status,
            handed_over_on=shipment.handed_over_on,
            delivered_on=shipment.delivered_on,
        )
        if shipment
        else None
    )

    return OrderDetail(
        order_number=order.order_number,
        customer_name=order.customer.full_name if order.customer else None,
        phone=order.customer.phone_e164 if order.customer else None,
        email=order.customer.email if order.customer else None,
        city=ship.get("city"),
        total_inr=order.total_inr,
        placed_at=order.placed_at,
        elapsed_days=elapsed_days,
        items=items_out,
        box_aft_number=box.aft_number if box else None,
        consignment_tracking_id=box.consignment.tracking_id if box and box.consignment else None,
        stage=stage,
        status_override=order.status_override,
        notes=order.notes,
        timeline=timeline,
        eta=eta,
        sla_risk=sla_risk,
        shipment=shipment_out,
    )


@router.patch("/{order_number}", response_model=OrderDetail)
def update_order(
    order_number: str, body: OrderUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    order = _find_order(db, order_number)
    before = {"status_override": order.status_override, "notes": order.notes}
    changed = False

    if "status_override" in body.model_fields_set:
        if body.status_override is not None and body.status_override not in ORDER_STATUS_OVERRIDES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status_override must be one of {ORDER_STATUS_OVERRIDES} or null.",
            )
        order.status_override = body.status_override
        changed = True

    if "notes" in body.model_fields_set:
        order.notes = body.notes
        changed = True

    if changed:
        record_audit(
            db, request, user, "order.update", "order", order.order_number,
            before=before, after={"status_override": order.status_override, "notes": order.notes},
        )
        db.commit()
    return get_order(order.order_number, user, db)


def _first_pending_leg(legs: dict):
    for leg in BOX_LEGS:
        if leg not in legs:
            return leg
    return None
