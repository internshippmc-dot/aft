import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.api.orders import _find_order
from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.models.box import Box
from app.models.customer_message import CustomerMessage
from app.models.order import Order
from app.models.user import User
from app.schemas.customer_message import MessageCreate, MessageOut

router = APIRouter(prefix="/messages", tags=["messages"])


def _out(m: CustomerMessage) -> MessageOut:
    return MessageOut(
        id=m.id, type=m.type, order_number=m.order.order_number,
        box_aft_number=m.box.aft_number if m.box else None,
        status=m.status, body=m.body, created_at=m.created_at, sent_at=m.sent_at,
    )


def _options():
    return (selectinload(CustomerMessage.order), selectinload(CustomerMessage.box))


@router.get("", response_model=list[MessageOut])
def list_messages(
    order_number: str | None = None,
    status_filter: str | None = None,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    query = select(CustomerMessage).options(*_options()).order_by(CustomerMessage.created_at.desc())
    if order_number:
        query = query.join(Order).where(Order.order_number == order_number)
    if status_filter:
        query = query.where(CustomerMessage.status == status_filter)
    return [_out(m) for m in db.scalars(query)]


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def create_message(body: MessageCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)):
    order = _find_order(db, body.order_number)
    box: Box | None = None
    for item in order.items:
        if item.box_item is not None:
            box = db.get(Box, item.box_item.box_id)
            break
    message = CustomerMessage(type=body.type, order_id=order.id, box_id=box.id if box else None, body=body.body, created_by=user.id)
    db.add(message)
    db.flush()
    record_audit(db, request, user, "message.create", "customer_message", str(message.id), after={"order_number": order.order_number, "type": body.type})
    db.commit()
    message = db.scalar(select(CustomerMessage).where(CustomerMessage.id == message.id).options(*_options()))
    return _out(message)


@router.patch("/{message_id}/sent", response_model=MessageOut)
def mark_sent(
    message_id: int, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    message = db.scalar(select(CustomerMessage).where(CustomerMessage.id == message_id).options(*_options()))
    if message is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such message.")
    message.status = "Sent"
    message.sent_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()
    record_audit(db, request, user, "message.sent", "customer_message", str(message.id), after={"status": "Sent"})
    db.commit()
    db.refresh(message)
    return _out(message)
