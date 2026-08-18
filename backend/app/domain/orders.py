import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.schemas.order import OrderCreateIn


def create_order(db: DbSession, data: OrderCreateIn) -> Order:
    """Quick-create an order pasted into a box that doesn't exist yet.

    Reuses the customer by phone if one matches (like the seed loader), otherwise
    creates a new customer. Order is stored with placed_at = now — the console
    has no real order-placed date for ad-hoc entries yet.
    """
    customer = None
    if data.phone:
        customer = db.scalar(select(Customer).where(Customer.phone_e164 == data.phone))
    if customer is None:
        customer = Customer(full_name=data.customer_name, phone_e164=data.phone)
        db.add(customer)
        db.flush()

    order = Order(
        order_number=data.order_number,
        customer_id=customer.id,
        placed_at=datetime.datetime.now(datetime.timezone.utc),
        payment_method=None,
        ship_address={"city": data.city} if data.city else None,
    )
    db.add(order)
    db.flush()

    for item in data.items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_title=item.product_title,
                colour=item.colour,
                size=item.size,
                quantity=item.quantity,
                unit_price_inr=item.unit_price_inr,
            )
        )
    db.flush()
    return order
