"""Demo data loader — run once after migrations. Idempotent: skips if users already exist.

Mirrors the box/order shape from prototype.html so the console is immediately
usable, plus 20 synthetic historical consignments purely to give the ETA
engine (domain/eta.py) enough samples for a high-confidence prediction.
"""

import datetime
import random
from decimal import Decimal

from sqlalchemy import select

from app.auth.password import hash_password
from app.db import SessionLocal
from app.models.box import Box, BoxItem
from app.models.consignment import Consignment
from app.models.customer import Customer
from app.models.leg import LegEvent, LegName, LegScope, LegSource
from app.models.order import Order, OrderItem
from app.models.user import User, UserRole

DEV_PASSWORD = "ChangeMe123!"


def _dt(date_str: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(date_str).replace(tzinfo=datetime.timezone.utc)


def _date(date_str: str) -> datetime.date:
    return datetime.date.fromisoformat(date_str)


BOXES_DATA = [
    dict(
        aft="AFT-0231", tracking="HXL-772104", mfr="Kathy · Yiwu", weight="6.20",
        legs={"MFG_DISPATCH": "2026-08-01", "CN_WAREHOUSE": "2026-08-03", "FLIGHT": "2026-08-06", "DELHI_WAREHOUSE": "2026-08-09"},
        orders=[
            dict(no="#AF1442", name="Ananya Rao", phone="+919820114455", city="Pune", total=4190, placed="2026-07-29",
                 items=[("Scallop Court Set", "Sage", "M", 1), ("Daily Track Set", "Black", "M", 1)]),
            dict(no="#AF1447", name="Ishaan Mehta", phone="+919833001299", city="Mumbai", total=2380, placed="2026-07-30",
                 items=[("Featherweight Running Set", "Slate", "L", 1)]),
            dict(no="#AF1451", name="Tara Bhatia", phone="+919711220034", city="Gurugram", total=5560, placed="2026-07-30",
                 items=[("Cerine Tote", "Tan", None, 1), ("Luna Set", "Ivory", "S", 1)]),
        ],
    ),
    dict(
        aft="AFT-0232", tracking="HXL-772104", mfr="Kathy · Yiwu", weight="5.05",
        legs={"MFG_DISPATCH": "2026-08-01", "CN_WAREHOUSE": "2026-08-03", "FLIGHT": "2026-08-06", "DELHI_WAREHOUSE": "2026-08-09"},
        orders=[
            dict(no="#AF1455", name="Rhea Kulkarni", phone="+919920778812", city="Nashik", total=3120, placed="2026-07-31",
                 items=[("Clubhouse Set", "Red", "S", 1)]),
            dict(no="#AF1459", name="Kabir Sethi", phone="+919818440021", city="Delhi", total=2890, placed="2026-07-31",
                 items=[("Trackline Set", "Navy", "XL", 1)]),
        ],
    ),
    dict(
        aft="AFT-0234", tracking="HXL-772107", mfr="Kathy · Yiwu", weight="8.60",
        legs={"MFG_DISPATCH": "2026-08-07", "CN_WAREHOUSE": "2026-08-09", "FLIGHT": "2026-08-12"},
        orders=[
            dict(no="#AF1502", name="Meher Qureshi", phone="+919867332210", city="Mumbai", total=6240, placed="2026-08-02",
                 items=[("Riviera Set", "Multi", "M", 1), ("Aria Set", "Cream", "M", 1)]),
            dict(no="#AF1508", name="Devansh Iyer", phone="+919845220017", city="Bengaluru", total=2450, placed="2026-08-03",
                 items=[("Celeste Active Set", "Navy", "L", 1)]),
            dict(no="#AF1511", name="Simran Gill", phone="+919779001188", city="Chandigarh", total=4980, placed="2026-08-03",
                 items=[("Portofino Set", "Stripe", "S", 1), ("Scallop Halter Set", "Black", "S", 1)]),
            dict(no="#AF1516", name="Nikhil Shetty", phone="+919820665510", city="Thane", total=2210, placed="2026-08-04",
                 items=[("Muse Dress", "Olive", "M", 1)]),
        ],
    ),
    dict(
        aft="AFT-0235", tracking=None, mfr="Kathy · Yiwu", weight="3.10",
        legs={"MFG_DISPATCH": "2026-08-11"},
        orders=[
            dict(no="#AF1544", name="Aarohi Nair", phone="+919846771200", city="Kochi", total=3390, placed="2026-08-07",
                 items=[("Butterline Active Set", "Blush", "M", 1)]),
            dict(no="#AF1549", name="Yash Agarwal", phone="+919831009944", city="Kolkata", total=2760, placed="2026-08-08",
                 items=[("Curveline Set", "Charcoal", "L", 1)]),
        ],
    ),
    dict(
        aft="AFT-0236", tracking=None, mfr="Kathy · Yiwu", weight="2.40",
        legs={"MFG_DISPATCH": "2026-08-12"},
        orders=[
            dict(no="#AF1560", name="Priya Deshmukh", phone="+919921330077", city="Pune", total=5120, placed="2026-08-09",
                 items=[("Cerine Tote", "Black", None, 1), ("Meridian Set", "Brown", "M", 1)]),
        ],
    ),
    dict(aft="AFT-0237", tracking=None, mfr="Kathy · Yiwu", weight="1.90", legs={}, orders=[]),
]

CONSIGNMENT_META = {
    "HXL-772104": dict(chargeable_weight_kg=Decimal("11.30"), freight_cost_inr=Decimal("9870.00")),
    "HXL-772107": dict(chargeable_weight_kg=Decimal("8.60"), freight_cost_inr=Decimal("7310.00")),
}


def _get_or_create_customer(db, name: str, phone: str, city: str) -> Customer:
    existing = db.scalar(select(Customer).where(Customer.phone_e164 == phone))
    if existing:
        return existing
    c = Customer(full_name=name, phone_e164=phone, email=None)
    db.add(c)
    db.flush()
    return c


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User)):
            print("Seed skipped — users already exist.")
            return

        owner = User(email="siddharth@actuallyfair.in", full_name="Siddharth", password_hash=hash_password(DEV_PASSWORD), role=UserRole.owner)
        ops = User(email="ops@actuallyfair.in", full_name="Ops", password_hash=hash_password(DEV_PASSWORD), role=UserRole.ops)
        viewer = User(email="viewer@actuallyfair.in", full_name="Viewer", password_hash=hash_password(DEV_PASSWORD), role=UserRole.viewer)
        db.add_all([owner, ops, viewer])
        db.flush()

        consignments: dict[str, Consignment] = {}
        for tracking_id, meta in CONSIGNMENT_META.items():
            c = Consignment(tracking_id=tracking_id, created_by=owner.id, **meta)
            db.add(c)
            db.flush()
            consignments[tracking_id] = c

        for bd in BOXES_DATA:
            box = Box(
                aft_number=bd["aft"],
                manufacturer=bd["mfr"],
                gross_weight_kg=Decimal(bd["weight"]),
                created_by=owner.id,
            )
            if bd["tracking"]:
                box.consignment_id = consignments[bd["tracking"]].id
            db.add(box)
            db.flush()

            scope_type = LegScope.consignment if bd["tracking"] else LegScope.box
            scope_id = consignments[bd["tracking"]].id if bd["tracking"] else box.id
            for leg_name, date_str in bd["legs"].items():
                # avoid inserting the same consignment-scoped leg twice (shared by two boxes)
                already = db.scalar(
                    select(LegEvent).where(
                        LegEvent.scope_type == scope_type,
                        LegEvent.scope_id == scope_id,
                        LegEvent.leg == LegName(leg_name),
                        LegEvent.superseded_at.is_(None),
                    )
                )
                if already:
                    continue
                db.add(LegEvent(
                    scope_type=scope_type, scope_id=scope_id, leg=LegName(leg_name),
                    occurred_on=_date(date_str), source=LegSource.manual, entered_by=owner.id,
                ))

            for od in bd["orders"]:
                customer = _get_or_create_customer(db, od["name"], od["phone"], od["city"])
                order = Order(
                    order_number=od["no"],
                    customer_id=customer.id,
                    placed_at=_dt(od["placed"] + "T09:00:00"),
                    total_inr=Decimal(str(od["total"])),
                    payment_method="prepaid",
                    financial_status="paid",
                    ship_address={"city": od["city"]},
                )
                db.add(order)
                db.flush()

                per_item_price = (Decimal(str(od["total"])) / len(od["items"])).quantize(Decimal("0.01"))
                for title, colour, size, qty in od["items"]:
                    item = OrderItem(
                        order_id=order.id, product_title=title, colour=colour, size=size,
                        quantity=qty, unit_price_inr=per_item_price,
                    )
                    db.add(item)
                    db.flush()
                    db.add(BoxItem(box_id=box.id, order_item_id=item.id, quantity=qty, added_by=owner.id))

        _seed_historical_consignments(db, owner)

        db.commit()
        print(f"Seeded {len(BOXES_DATA)} boxes, {len(consignments)} consignments, 3 users.")
        print(f"Dev login — owner: siddharth@actuallyfair.in / {DEV_PASSWORD}")
        print(f"           ops:   ops@actuallyfair.in / {DEV_PASSWORD}")
        print(f"           viewer: viewer@actuallyfair.in / {DEV_PASSWORD}")
    finally:
        db.close()


def _seed_historical_consignments(db, owner: User) -> None:
    """20 completed, invisible-to-the-UI consignments so domain/eta.py has
    trailing-window samples to compute a high-confidence prediction from."""
    rng = random.Random(42)
    base = _date("2026-05-01")
    for i in range(20):
        dispatch = base + datetime.timedelta(days=i * 3 + rng.randint(0, 2))
        cn = dispatch + datetime.timedelta(days=rng.randint(1, 3))
        flight = cn + datetime.timedelta(days=rng.randint(2, 4))
        delhi = flight + datetime.timedelta(days=rng.randint(2, 4))
        if delhi.weekday() == 6:
            delhi += datetime.timedelta(days=1)

        c = Consignment(tracking_id=f"HXL-HIST-{i:03d}", created_by=owner.id)
        db.add(c)
        db.flush()
        for leg, date in [
            (LegName.MFG_DISPATCH, dispatch),
            (LegName.CN_WAREHOUSE, cn),
            (LegName.FLIGHT, flight),
            (LegName.DELHI_WAREHOUSE, delhi),
        ]:
            db.add(LegEvent(
                scope_type=LegScope.consignment, scope_id=c.id, leg=leg,
                occurred_on=date, source=LegSource.sheet, entered_by=owner.id,
            ))


if __name__ == "__main__":
    seed()
