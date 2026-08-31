"""iThink Logistics — shipment booking + tracking.

API reference: https://docs.ithinklogistics.com/doc-add-order/1 (booking) and
https://docs.ithinklogistics.com/doc-track-order/3 (tracking). Both endpoints
take access_token/secret_key inside the JSON body, not as headers.
"""

import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models.leg import Shipment
from app.models.order import Order
from app.models.plumbing import SyncState
from app.models.return_case import ReturnCase

# iThink's endpoints aren't consistently versioned across their own docs —
# add-order lives under /api, track-order under /api_v3.
ADD_ORDER_URL = "https://api.ithinklogistics.com/api/order/add.json"
TRACK_ORDER_URL = "https://api.ithinklogistics.com/api_v3/order/track.json"
TRACKING_SYNC_KEY = "ithink_tracking"
# iThink caps this request at 10 AWBs per call.
TRACK_BATCH_SIZE = 10

# Best-effort mapping from iThink's current_status_code to what we consider
# "delivered" for Shipment.delivered_on — anything else just updates status.
DELIVERED_CODES = {"DL", "DELIVERED"}


class IThinkNotConfigured(Exception):
    pass


def _auth(settings) -> dict:
    if not settings.ithink_access_token or not settings.ithink_secret_key:
        raise IThinkNotConfigured("ITHINK_ACCESS_TOKEN / ITHINK_SECRET_KEY not set.")
    return {"access_token": settings.ithink_access_token, "secret_key": settings.ithink_secret_key}


def _order_number_suffix(order_number: str, kind: str) -> str:
    """iThink requires a unique order id per shipment call — a forward and a
    reverse booking for the same order number would otherwise collide."""
    return order_number if kind == "forward" else f"{order_number}-RET"


def _shipment_payload(order: Order, settings, *, order_type: str) -> dict:
    address = order.ship_address or {}
    items = [
        {
            "product_name": item.product_title,
            "product_quantity": item.quantity,
            "product_price": float(item.unit_price_inr or 0),
        }
        for item in order.items
    ]
    return {
        "order": _order_number_suffix(order.order_number, order_type),
        "order_date": order.placed_at.strftime("%Y-%m-%d %H:%M:%S"),
        "total_amount": float(order.total_inr or 0),
        "name": address.get("name") or (order.customer.full_name if order.customer else "Customer"),
        "add": address.get("address1") or "",
        "add2": address.get("address2") or "",
        "pin": address.get("zip") or "",
        "city": address.get("city") or "",
        "state": address.get("province") or "",
        "country": address.get("country") or "India",
        "phone": address.get("phone") or (order.customer.phone_e164 if order.customer else ""),
        "products": items,
        "shipment_length": 10,
        "shipment_width": 10,
        "shipment_height": 10,
        "weight": 0.5,
        "payment_mode": "Prepaid" if (order.financial_status == "paid") else "cod",
        "cod_amount": 0 if order.financial_status == "paid" else float(order.total_inr or 0),
        "return_address_id": settings.ithink_return_address_id,
        "pickup_address_id": settings.ithink_pickup_address_id,
        "order_type": order_type,
    }


def _post_add_order(shipment_body: dict, settings) -> dict:
    payload = {"data": {"shipments": [shipment_body], **_auth(settings)}}
    resp = httpx.post(ADD_ORDER_URL, json=payload, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    result = (body.get("data") or {}).get("1") or {}
    if result.get("status") != "Success":
        raise RuntimeError(f"iThink booking failed: {result.get('remark') or body}")
    return result


def book_shipment(db: DbSession, order: Order) -> Shipment:
    """PRD-adjacent (not in original PRD, added per user request) — create a
    forward (outbound delivery) iThink shipment for an order and store the
    returned AWB. Raises on any failure; the caller (an owner/ops-triggered
    endpoint) surfaces that directly to the operator rather than silently
    retrying, unlike the background sync loops."""
    settings = get_settings()
    if not settings.ithink_pickup_address_id or not settings.ithink_return_address_id:
        raise IThinkNotConfigured("ITHINK_PICKUP_ADDRESS_ID / ITHINK_RETURN_ADDRESS_ID not set.")

    result = _post_add_order(_shipment_payload(order, settings, order_type="forward"), settings)

    shipment = Shipment(
        order_id=order.id,
        courier=result.get("logistic"),
        awb=result.get("waybill"),
        status="booked",
        kind="forward",
    )
    db.add(shipment)
    db.flush()
    return shipment


def book_return_shipment(db: DbSession, order: Order, return_case: ReturnCase) -> Shipment:
    """Book a reverse pickup — courier collects from the customer's address
    (the order's ship_address, same as forward) and delivers back to our
    warehouse. Same two address IDs as forward; only order_type differs,
    which is how every major Indian courier aggregator (iThink included)
    distinguishes a reverse pickup from an outbound delivery."""
    settings = get_settings()
    if not settings.ithink_pickup_address_id or not settings.ithink_return_address_id:
        raise IThinkNotConfigured("ITHINK_PICKUP_ADDRESS_ID / ITHINK_RETURN_ADDRESS_ID not set.")

    result = _post_add_order(_shipment_payload(order, settings, order_type="reverse"), settings)

    shipment = Shipment(
        order_id=order.id,
        return_id=return_case.id,
        courier=result.get("logistic"),
        awb=result.get("waybill"),
        status="booked",
        kind="reverse",
    )
    db.add(shipment)
    db.flush()
    return shipment


def track_once(db: DbSession) -> dict:
    """Poll every open shipment (has an AWB, not yet delivered) in batches of
    10 and update status/handed_over_on/delivered_on. Never raises — same
    failure-recorded-on-sync_state contract as the Shopify loop."""
    settings = get_settings()
    state = db.get(SyncState, TRACKING_SYNC_KEY)
    if state is None:
        state = SyncState(key=TRACKING_SYNC_KEY)
        db.add(state)
        db.flush()

    result = {"updated": 0, "error": None}
    try:
        auth = _auth(settings)
        open_shipments = list(
            db.scalars(
                select(Shipment).where(Shipment.awb.is_not(None), Shipment.delivered_on.is_(None))
            )
        )
        for i in range(0, len(open_shipments), TRACK_BATCH_SIZE):
            batch = open_shipments[i : i + TRACK_BATCH_SIZE]
            awb_list = ",".join(s.awb for s in batch)
            resp = httpx.post(
                TRACK_ORDER_URL,
                json={"data": {"awb_number_list": awb_list, **auth}},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data") or {}
            for shipment in batch:
                info = data.get(shipment.awb)
                if not info or info.get("message") != "success":
                    continue
                shipment.status = info.get("current_status")
                if info.get("current_status_code") in DELIVERED_CODES:
                    date_str = (info.get("last_scan_details") or {}).get("status_date_time")
                    shipment.delivered_on = (
                        datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()
                        if date_str
                        else datetime.date.today()
                    )
                elif shipment.handed_over_on is None and info.get("current_status_code") not in ("MN", "PICKUP_PENDING"):
                    shipment.handed_over_on = datetime.date.today()
                result["updated"] += 1
        state.last_success_at = datetime.datetime.now(datetime.timezone.utc)
        state.last_error = None
        db.commit()
    except Exception as exc:  # noqa: BLE001 — must not crash the background loop
        db.rollback()
        state = db.get(SyncState, TRACKING_SYNC_KEY) or SyncState(key=TRACKING_SYNC_KEY)
        state.last_error = str(exc)[:2000]
        db.add(state)
        db.commit()
        result["error"] = str(exc)
    return result
