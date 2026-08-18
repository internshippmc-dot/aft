import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.box import Box, BoxItem
from app.models.order import Order, OrderItem
from app.models.user import User

_SPLIT_RE = re.compile(r"[,\n\r]+")


def parse_order_numbers(raw: str) -> list[str]:
    """PRD F2 — newline or comma separated list of order numbers."""
    seen: list[str] = []
    for token in _SPLIT_RE.split(raw):
        cleaned = token.strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _find_order(db: DbSession, order_number: str) -> Order | None:
    order = db.scalar(select(Order).where(Order.order_number == order_number))
    if order is not None:
        return order
    alt = order_number[1:] if order_number.startswith("#") else "#" + order_number
    return db.scalar(select(Order).where(Order.order_number == alt))


@dataclass
class AttachFailure:
    order_number: str
    reason: str


@dataclass
class AttachResult:
    attached: list[str] = field(default_factory=list)
    already_in_this_box: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # numbers not in the system — quick-creatable
    failed: list[AttachFailure] = field(default_factory=list)


def attach_orders_to_box(db: DbSession, box: Box, order_numbers: list[str], actor: User) -> AttachResult:
    """PRD F2 — attach whole orders to a box, blocking anything already boxed elsewhere."""
    result = AttachResult()

    existing_item_ids = {bi.order_item_id for bi in box.items}

    for order_number in order_numbers:
        order = _find_order(db, order_number)
        if order is None:
            result.missing.append(order_number)
            continue
        if not order.items:
            result.failed.append(AttachFailure(order_number, "Order has no line items."))
            continue

        conflict_aft = None
        for item in order.items:
            existing = db.scalar(select(BoxItem).where(BoxItem.order_item_id == item.id))
            if existing is not None and existing.box_id != box.id:
                conflict_aft = existing.box.aft_number
                break

        if conflict_aft:
            result.failed.append(
                AttachFailure(order_number, f"Already assigned to box {conflict_aft}.")
            )
            continue

        newly_attached = False
        for item in order.items:
            if item.id in existing_item_ids:
                continue
            db.add(BoxItem(box_id=box.id, order_item_id=item.id, quantity=item.quantity, added_by=actor.id))
            existing_item_ids.add(item.id)
            newly_attached = True

        if newly_attached:
            result.attached.append(order.order_number)
        else:
            result.already_in_this_box.append(order.order_number)

    db.flush()
    return result


def detach_item_from_box(db: DbSession, box: Box, order_item_id: int) -> bool:
    row = db.get(BoxItem, {"box_id": box.id, "order_item_id": order_item_id})
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True
