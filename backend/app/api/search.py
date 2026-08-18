from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.auth.deps import get_current_user
from app.auth.ratelimit import check_rate_limit
from app.db import get_db
from app.domain.stages import compute_stage, effective_legs
from app.models.box import Box, BoxItem
from app.models.consignment import Consignment
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.user import User
from app.schemas.search import BoxHit, OrderHit, SearchResults

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResults)
def search(q: str = "", user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    check_rate_limit(f"search:user:{user.id}", max_hits=60, window_seconds=60)

    q = q.strip()
    if not q:
        return SearchResults(orders=[], boxes=[])
    like = f"%{q}%"

    order_rows = db.scalars(
        select(Order)
        .join(Customer, Order.customer_id == Customer.id, isouter=True)
        .where(
            or_(
                Order.order_number.ilike(like),
                Customer.full_name.ilike(like),
                Customer.phone_e164.ilike(like),
                Customer.email.ilike(like),
            )
        )
        .options(selectinload(Order.items).selectinload(OrderItem.box_item), selectinload(Order.customer))
        .limit(8)
    ).all()

    # one query for every box an item in these orders sits in, instead of a
    # per-order lookup (PRD F4 — search must stay fast as order volume grows)
    item_ids = [i.id for o in order_rows for i in o.items]
    aft_by_item: dict[int, str] = {}
    if item_ids:
        rows = db.execute(
            select(BoxItem.order_item_id, Box.aft_number)
            .join(Box, BoxItem.box_id == Box.id)
            .where(BoxItem.order_item_id.in_(item_ids))
        ).all()
        aft_by_item = {row.order_item_id: row.aft_number for row in rows}

    order_hits = []
    for order in order_rows:
        aft_number = next((aft_by_item[i.id] for i in order.items if i.id in aft_by_item), None)
        order_hits.append(
            OrderHit(
                order_number=order.order_number,
                customer_name=order.customer.full_name if order.customer else None,
                aft_number=aft_number,
            )
        )

    aft_matches = db.scalars(
        select(Box)
        .where(Box.aft_number.ilike(like))
        .options(selectinload(Box.consignment), selectinload(Box.items))
        .limit(8)
    ).all()
    tracking_matches = db.scalars(
        select(Box)
        .join(Consignment, Box.consignment_id == Consignment.id)
        .where(Consignment.tracking_id.ilike(like))
        .options(selectinload(Box.consignment), selectinload(Box.items))
        .limit(8)
    ).all()

    box_rows: list[Box] = []
    seen_ids: set[int] = set()
    for b in [*aft_matches, *tracking_matches]:
        if b.id not in seen_ids:
            box_rows.append(b)
            seen_ids.add(b.id)

    box_hits = []
    for box in box_rows[:8]:
        legs = effective_legs(db, box)
        box_hits.append(
            BoxHit(
                aft_number=box.aft_number,
                tracking_id=box.consignment.tracking_id if box.consignment else None,
                order_count=len({bi.order_item.order_id for bi in box.items}),
                stage=compute_stage(legs),
            )
        )

    return SearchResults(orders=order_hits, boxes=box_hits)
