"""iThink Logistics — shipment booking + tracking.

API reference: https://docs.ithinklogistics.com/doc-add-order/3 (booking v3)
and https://docs.ithinklogistics.com/doc-track-order/3 (tracking). Both
endpoints take access_token/secret_key inside the JSON body, not as headers.
Note the two live on different domains — my.ithinklogistics.com for booking,
api.ithinklogistics.com for tracking — confirmed against iThink's own docs
(not a typo).
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

ADD_ORDER_URL = "https://my.ithinklogistics.com/api_v3/order/add.json"
TRACK_ORDER_URL = "https://api.ithinklogistics.com/api_v3/order/track.json"
TRACKING_SYNC_KEY = "ithink_tracking"
# iThink caps this request at 10 AWBs per call.
TRACK_BATCH_SIZE = 10

# Best-effort mapping from iThink's current_status_code to what we consider
# "delivered" for Shipment.delivered_on — anything else just updates status.
DELIVERED_CODES = {"DL", "DELIVERED"}

# The warehouses/offices registered as pickup addresses in the iThink portal
# (Settings -> Addresses). Every one of them has its RTO address set to
# "Same as Pickup" there, so whichever address a shipment is picked up from
# is also where a return/RTO comes back to — no separate return-address
# concept needed. Ops picks the address per booking rather than one being
# hardcoded, since shipments actually go out from more than one of these.
PICKUP_ADDRESSES = [
    {"id": "121347", "label": "Actually Fair Delhi Warehouse"},
    {"id": "120998", "label": "MC Warehouse"},
    {"id": "120956", "label": "Actually Fair Technologies"},
]
PICKUP_ADDRESS_IDS = {a["id"] for a in PICKUP_ADDRESSES}


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


def _shipment_payload(order: Order, pickup_address_id: str, *, order_type: str) -> dict:
    """Per the v3 add-order schema, pickup_address_id and order_type are
    fields on the outer `data` object (see _post_add_order), not inside the
    shipment itself — only return_address_id lives on the shipment."""
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
        "sub_order": "",
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
        # required by this account; we don't collect a separate alt number,
        # so fall back to the same phone.
        "alt_phone": address.get("phone") or (order.customer.phone_e164 if order.customer else ""),
        # our data model has no separate billing address — shipping is billing.
        "is_billing_same_as_shipping": "yes",
        "products": items,
        "shipment_length": 10,
        "shipment_width": 10,
        "shipment_height": 10,
        "weight": 0.5,
        "payment_mode": "Prepaid" if (order.financial_status == "paid") else "cod",
        "cod_amount": 0 if order.financial_status == "paid" else float(order.total_inr or 0),
        # This account's validation treats most of iThink's documented
        # "optional" charge/discount fields as mandatory in practice — set
        # to 0 since we don't track any of these separately.
        "shipping_charges": 0,
        "giftwrap_charges": 0,
        "transaction_charges": 0,
        "total_discount": 0,
        "first_attemp_discount": 0,
        "cod_charges": 0,
        "advance_amount": 0,
        "reseller_name": "",
        "eway_bill_number": "",
        "gst_number": "",
        "what3words": "",
        # every registered address's RTO is "Same as Pickup" in the iThink
        # portal, so the return address always mirrors whichever pickup
        # address this particular shipment goes out from.
        "return_address_id": pickup_address_id,
    }


# Preferred courier order — try Bluedart first, then Delhivery, then let
# iThink auto-assign whichever courier is actually serviceable for that
# pickup/delivery pincode pair (per user instruction).
PREFERRED_COURIERS = ["Bluedart", "Delhivery"]


def _post_add_order(shipment_body: dict, pickup_address_id: str, order_type: str, settings, logistics: str | None = None) -> dict:
    data = {
        "shipments": [shipment_body],
        "pickup_address_id": pickup_address_id,
        "order_type": order_type,
        # required by this account even though iThink's own docs list it as
        # optional — "ground" is the value from their own documented example.
        "s_type": "ground",
        **_auth(settings),
    }
    if logistics:
        data["logistics"] = logistics
    resp = httpx.post(ADD_ORDER_URL, json={"data": data}, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    result_data = body.get("data")
    # Observed in practice: a successful booking's "data" can come back as
    # either {"1": {...}} keyed by shipment index, or the shipment dict
    # itself directly — handle both rather than assume the keyed form.
    if isinstance(result_data, dict) and "waybill" in result_data:
        result = result_data
    elif isinstance(result_data, dict):
        result = result_data.get("1") or {}
    else:
        result = {}
    if result.get("status") not in ("Success", "success") and not result.get("waybill"):
        raise RuntimeError(f"iThink booking failed — full response: {body!r}")
    return result


def _post_add_order_with_fallback(shipment_body: dict, pickup_address_id: str, order_type: str, settings) -> dict:
    """Try each preferred courier in turn, then fall back to letting iThink
    auto-assign whichever is actually serviceable, rather than failing
    outright just because the top preference can't carry this shipment.

    iThink registers the "order" id on its side as soon as an attempt is
    made — even one that fails on that courier's serviceability — so a
    retry reusing the exact same id gets rejected as a duplicate before its
    own courier is even tried. Each attempt gets its own suffixed id."""
    base_order = shipment_body["order"]
    last_error: Exception | None = None
    for courier in [*PREFERRED_COURIERS, None]:
        attempt_body = {**shipment_body, "order": f"{base_order}-{courier or 'AUTO'}"}
        try:
            return _post_add_order(attempt_body, pickup_address_id, order_type, settings, logistics=courier)
        except Exception as exc:  # noqa: BLE001 — try the next courier before giving up
            last_error = exc
    raise last_error


def _resolve_pickup_address(pickup_address_id: str | None) -> str:
    pickup_address_id = (pickup_address_id or "").strip()
    if not pickup_address_id:
        raise IThinkNotConfigured("pickup_address_id is required — pick a pickup address to book from.")
    if pickup_address_id not in PICKUP_ADDRESS_IDS:
        known = ", ".join(a["label"] for a in PICKUP_ADDRESSES)
        raise IThinkNotConfigured(f"Unknown pickup_address_id '{pickup_address_id}'. Known addresses: {known}.")
    return pickup_address_id


def book_shipment(db: DbSession, order: Order, pickup_address_id: str | None = None) -> Shipment:
    """PRD-adjacent (not in original PRD, added per user request) — create a
    forward (outbound delivery) iThink shipment for an order and store the
    returned AWB. Raises on any failure; the caller (an owner/ops-triggered
    endpoint) surfaces that directly to the operator rather than silently
    retrying, unlike the background sync loops."""
    settings = get_settings()
    pickup_address_id = _resolve_pickup_address(pickup_address_id)

    body = _shipment_payload(order, pickup_address_id, order_type="forward")
    result = _post_add_order_with_fallback(body, pickup_address_id, "forward", settings)

    shipment = Shipment(
        order_id=order.id,
        courier=result.get("logistic_name"),
        awb=result.get("waybill"),
        status="booked",
        kind="forward",
    )
    db.add(shipment)
    db.flush()
    return shipment


def book_return_shipment(
    db: DbSession, order: Order, return_case: ReturnCase, pickup_address_id: str | None = None
) -> Shipment:
    """Book a reverse pickup — courier collects from the customer's address
    (the order's ship_address, same as forward) and delivers back to
    whichever of our addresses is passed in. Only order_type differs from a
    forward booking, which is how every major Indian courier aggregator
    (iThink included) distinguishes a reverse pickup from an outbound
    delivery."""
    settings = get_settings()
    pickup_address_id = _resolve_pickup_address(pickup_address_id)

    body = _shipment_payload(order, pickup_address_id, order_type="reverse")
    result = _post_add_order_with_fallback(body, pickup_address_id, "reverse", settings)

    shipment = Shipment(
        order_id=order.id,
        return_id=return_case.id,
        courier=result.get("logistic_name"),
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
