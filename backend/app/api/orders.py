import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.auth.deps import get_current_user
from app.config import get_settings
from app.db import get_db
from app.domain.box_view import build_eta
from app.domain.stages import BOX_LEGS, STAGE_LABELS, compute_stage, effective_legs
from app.models.box import Box, BoxItem
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.common import OrderItemOut, ShipmentOut
from app.schemas.order import LegTimelineEntry, OrderDetail

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
    stage = compute_stage(legs) if box else "Awaiting box assignment"
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
        timeline=timeline,
        eta=eta,
        sla_risk=sla_risk,
        shipment=shipment_out,
    )


def _first_pending_leg(legs: dict):
    for leg in BOX_LEGS:
        if leg not in legs:
            return leg
    return None
