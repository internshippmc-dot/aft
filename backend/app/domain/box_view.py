import datetime
from decimal import Decimal

from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.domain.eta import predict
from app.domain.stages import BOX_LEGS, compute_stage, effective_legs
from app.models.box import Box
from app.schemas.box import AttachResultOut, BoxManifest, BoxSummary, LegsOut, ManifestOrderOut
from app.schemas.common import EtaOut, OrderItemOut
from app.schemas.manufacturer_shipment import ManufacturerShipmentOut

settings = get_settings()


def _oldest_order_placed_at(box: Box) -> datetime.datetime | None:
    orders = {bi.order_item.order for bi in box.items}
    if not orders:
        return None
    return min(o.placed_at for o in orders)


def _sla_risk(box: Box, eta: EtaOut | None) -> bool:
    if eta is None:
        return False
    oldest = _oldest_order_placed_at(box)
    if oldest is None:
        return False
    oldest_date = oldest.date() if isinstance(oldest, datetime.datetime) else oldest
    return (eta.p80_date - oldest_date).days > settings.sla_days


def build_eta(db: DbSession, box: Box) -> EtaOut | None:
    pred = predict(db, box)
    if pred is None:
        return None
    return EtaOut(
        p50_date=pred.p50_date, p80_date=pred.p80_date, sample_n=pred.sample_n, confidence=pred.confidence
    )


def build_summary(db: DbSession, box: Box) -> BoxSummary:
    legs = effective_legs(db, box)
    stage = compute_stage(legs)
    eta = build_eta(db, box)
    orders = {bi.order_item.order_id for bi in box.items}
    return BoxSummary(
        aft_number=box.aft_number,
        tracking_id=box.consignment.tracking_id if box.consignment else None,
        manufacturer=box.manufacturer,
        gross_weight_kg=box.gross_weight_kg,
        order_count=len(orders),
        stage=stage,
        legs=LegsOut(**{leg.value: legs.get(leg) for leg in BOX_LEGS}),
        eta=eta,
        sla_risk=_sla_risk(box, eta),
        created_at=box.created_at,
        shipments=[_shipment_out(s) for s in box.shipments],
    )


def _shipment_out(s) -> ManufacturerShipmentOut:
    return ManufacturerShipmentOut(
        id=s.id, manufacturer=s.manufacturer, so_number=s.so_number, so_date=s.so_date,
        tracking_id=s.tracking_id, boxes_received=s.boxes_received, so_qty=s.so_qty,
        box_aft_number=s.box.aft_number if s.box else None, created_at=s.created_at,
    )


def build_manifest(
    db: DbSession,
    box: Box,
    attach: AttachResultOut | None = None,
) -> BoxManifest:
    legs = effective_legs(db, box)
    stage = compute_stage(legs)
    eta = build_eta(db, box)

    by_order: dict[int, list] = {}
    for bi in box.items:
        by_order.setdefault(bi.order_item.order_id, []).append(bi)

    orders_out: list[ManifestOrderOut] = []
    units_total = 0
    value_total = Decimal("0")
    for _order_id, bis in by_order.items():
        order = bis[0].order_item.order
        items_out = []
        for bi in bis:
            oi = bi.order_item
            items_out.append(
                OrderItemOut(id=oi.id, product_title=oi.product_title, colour=oi.colour, size=oi.size, quantity=bi.quantity)
            )
            units_total += bi.quantity
            if oi.unit_price_inr:
                value_total += oi.unit_price_inr * bi.quantity
        ship = order.ship_address or {}
        orders_out.append(
            ManifestOrderOut(
                order_number=order.order_number,
                customer_name=order.customer.full_name if order.customer else None,
                city=ship.get("city"),
                placed_at=order.placed_at,
                total_inr=order.total_inr,
                items=items_out,
            )
        )
    orders_out.sort(key=lambda o: o.placed_at)

    return BoxManifest(
        aft_number=box.aft_number,
        tracking_id=box.consignment.tracking_id if box.consignment else None,
        manufacturer=box.manufacturer,
        gross_weight_kg=box.gross_weight_kg,
        notes=box.notes,
        stage=stage,
        legs=LegsOut(**{leg.value: legs.get(leg) for leg in BOX_LEGS}),
        eta=eta,
        sla_risk=_sla_risk(box, eta),
        order_count=len(orders_out),
        units_total=units_total,
        value_total=value_total,
        oldest_order_placed_at=_oldest_order_placed_at(box),
        orders=orders_out,
        shipments=[_shipment_out(s) for s in box.shipments],
        attach=attach,
    )
