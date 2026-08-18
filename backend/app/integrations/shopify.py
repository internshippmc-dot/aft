"""Shopify order sync — PRD.md F8.

Pagination and request shape mirror the already-working reference
implementation in the Shopify-Excel-Exporter script (src/shopify_api.py):
REST Admin API, cursor pagination via the Link response header's
rel="next" page_info token. The OAuth token itself is minted once outside
this app (see config.py's shopify_access_token docstring) — this module
only ever makes authenticated GETs with it, never runs the OAuth flow.
"""

import datetime
import re
from decimal import Decimal, InvalidOperation

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.plumbing import SyncState

SYNC_KEY = "shopify"


class ShopifyNotConfigured(Exception):
    pass


def _client(settings) -> httpx.Client:
    if not settings.shopify_shop or not settings.shopify_access_token:
        raise ShopifyNotConfigured("SHOPIFY_SHOP / SHOPIFY_ACCESS_TOKEN not set.")
    base = f"https://{settings.shopify_shop}/admin/api/{settings.shopify_api_version}"
    return httpx.Client(
        base_url=base,
        headers={
            "X-Shopify-Access-Token": settings.shopify_access_token,
            "Accept": "application/json",
        },
        timeout=30,
    )


def _next_page_info(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' not in part:
            continue
        match = re.search(r"page_info=([^&>]+)", part)
        if match:
            return match.group(1)
    return None


def fetch_orders_since(client: httpx.Client, updated_at_min: str | None) -> list[dict]:
    """Paginate through every order updated since the cursor. status=any so
    cancelled/archived orders that later change still get picked up."""
    orders: list[dict] = []
    page_info: str | None = None
    while True:
        if page_info:
            params = {"limit": 250, "page_info": page_info}
        else:
            params = {"limit": 250, "status": "any", "order": "updated_at asc"}
            if updated_at_min:
                params["updated_at_min"] = updated_at_min
        resp = client.get("/orders.json", params=params)
        resp.raise_for_status()
        batch = resp.json().get("orders", [])
        orders.extend(batch)
        page_info = _next_page_info(resp.headers.get("Link"))
        if not page_info:
            break
    return orders


def _decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _split_variant(variant_title: str | None) -> tuple[str | None, str | None]:
    # Shopify variant titles are conventionally "Colour / Size" — best-effort
    # split, not authoritative (some stores only vary on one axis).
    if not variant_title:
        return None, None
    parts = [p.strip() for p in variant_title.split("/")]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, variant_title


def upsert_order(db: DbSession, raw: dict) -> bool:
    """Insert or update one Shopify order. Returns True if this was a new order."""
    shopify_customer = raw.get("customer") or {}
    customer = None
    if shopify_customer.get("id"):
        customer = db.scalar(
            select(Customer).where(Customer.shopify_customer_id == shopify_customer["id"])
        )
        full_name = f"{shopify_customer.get('first_name', '')} {shopify_customer.get('last_name', '')}".strip()
        if customer is None:
            customer = Customer(
                shopify_customer_id=shopify_customer["id"],
                full_name=full_name or "Unknown",
                phone_e164=shopify_customer.get("phone"),
                email=shopify_customer.get("email"),
            )
            db.add(customer)
            db.flush()
        else:
            customer.full_name = full_name or customer.full_name
            customer.phone_e164 = shopify_customer.get("phone") or customer.phone_e164
            customer.email = shopify_customer.get("email") or customer.email

    order = db.scalar(select(Order).where(Order.shopify_order_id == raw["id"]))
    is_new = order is None
    if order is None:
        order = Order(shopify_order_id=raw["id"], order_number=raw["name"])
        db.add(order)

    order.order_number = raw["name"]
    order.customer_id = customer.id if customer else order.customer_id
    order.placed_at = datetime.datetime.fromisoformat(raw["created_at"])
    order.total_inr = _decimal(raw.get("total_price"))
    order.payment_method = ", ".join(raw.get("payment_gateway_names") or []) or None
    order.financial_status = raw.get("financial_status")
    order.ship_address = raw.get("shipping_address")
    db.flush()

    existing_items = {
        item.shopify_line_item_id: item
        for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))
        if item.shopify_line_item_id is not None
    }
    for line in raw.get("line_items", []):
        colour, size = _split_variant(line.get("variant_title"))
        item = existing_items.get(line["id"])
        if item is None:
            item = OrderItem(order_id=order.id, shopify_line_item_id=line["id"])
            db.add(item)
        item.product_title = line.get("title") or "Untitled"
        item.variant_title = line.get("variant_title")
        item.colour = colour
        item.size = size
        item.quantity = line.get("quantity") or 1
        item.unit_price_inr = _decimal(line.get("price"))

    return is_new


def sync_once(db: DbSession) -> dict:
    """PRD F8 — pull orders updated since the last cursor, upsert, advance
    the cursor. Never raises: failures are recorded on sync_state so the
    caller (manual endpoint or background loop) can report them without
    crashing the process."""
    settings = get_settings()
    state = db.get(SyncState, SYNC_KEY)
    if state is None:
        state = SyncState(key=SYNC_KEY)
        db.add(state)
        db.flush()

    result = {"created": 0, "updated": 0, "error": None}
    try:
        with _client(settings) as client:
            orders = fetch_orders_since(client, state.cursor_value)
        for raw in orders:
            if upsert_order(db, raw):
                result["created"] += 1
            else:
                result["updated"] += 1
            state.cursor_value = raw["updated_at"]
        state.last_success_at = datetime.datetime.now(datetime.timezone.utc)
        state.last_error = None
        db.commit()
    except Exception as exc:  # noqa: BLE001 — genuinely must not propagate from a background loop
        db.rollback()
        state = db.get(SyncState, SYNC_KEY) or SyncState(key=SYNC_KEY)
        state.last_error = str(exc)[:2000]
        db.add(state)
        db.commit()
        result["error"] = str(exc)
    return result
