import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.api.orders import _find_order
from app.audit import record_audit
from app.auth.deps import get_current_user, require_owner, require_ops
from app.db import get_db
from app.domain.orders import create_order
from app.models.order import Order
from app.models.payment import Payment
from app.models.refund_request import RefundRequest
from app.models.user import User
from app.schemas.order import OrderCreateIn, OrderItemCreate
from app.schemas.refund_request import RefundRequestCreate, RefundRequestOut

router = APIRouter(prefix="/refunds", tags=["refunds"])


def _get_refund_or_404(db: DbSession, refund_id: int) -> RefundRequest:
    row = db.scalar(
        select(RefundRequest)
        .where(RefundRequest.id == refund_id)
        .options(selectinload(RefundRequest.order).selectinload(Order.customer))
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No refund request {refund_id}.")
    return row


def _user_name(db: DbSession, user_id: int | None) -> str | None:
    if user_id is None:
        return None
    user = db.get(User, user_id)
    return user.full_name if user else None


def _out(db: DbSession, r: RefundRequest) -> RefundRequestOut:
    return RefundRequestOut(
        id=r.id,
        order_number=r.order.order_number,
        customer_name=r.order.customer.full_name if r.order.customer else None,
        amount_inr=r.amount_inr,
        qr_image=r.qr_image,
        reason=r.reason,
        status=r.status,
        requested_by_name=_user_name(db, r.requested_by),
        paid_by_name=_user_name(db, r.paid_by),
        paid_at=r.paid_at,
        created_at=r.created_at,
    )


@router.get("", response_model=list[RefundRequestOut])
def list_refunds(
    status_filter: str | None = None,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    query = (
        select(RefundRequest)
        .options(selectinload(RefundRequest.order).selectinload(Order.customer))
        .order_by(RefundRequest.created_at.desc())
    )
    if status_filter:
        query = query.where(RefundRequest.status == status_filter)
    return [_out(db, r) for r in db.scalars(query)]


@router.post("", response_model=RefundRequestOut, status_code=status.HTTP_201_CREATED)
def create_refund(
    body: RefundRequestCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    try:
        order = _find_order(db, body.order_number)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        if not body.customer_name:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"No order {body.order_number}. Add a customer name to create it and file the refund together.",
            ) from exc
        # Quick-create — a customer who ordered outside Shopify, or one
        # Shopify sync just hasn't picked up yet. Same path used when
        # pasting an unrecognised order number into an AFT batch.
        order = create_order(
            db,
            OrderCreateIn(
                order_number=body.order_number,
                customer_name=body.customer_name,
                phone=body.phone,
                items=[OrderItemCreate(product_title="(added for refund — no line items on file)")],
            ),
        )
        db.flush()
        record_audit(
            db, request, user, "order.quick_create", "order", order.order_number,
            after={"customer_name": body.customer_name, "via": "refund_request"},
        )

    refund = RefundRequest(
        order_id=order.id,
        amount_inr=body.amount_inr,
        qr_image=body.qr_image,
        reason=body.reason,
        requested_by=user.id,
    )
    db.add(refund)
    db.flush()
    record_audit(
        db, request, user, "refund.create", "refund_request", str(refund.id),
        after={"order_number": order.order_number, "amount_inr": str(body.amount_inr)},
    )
    db.commit()
    return _out(db, _get_refund_or_404(db, refund.id))


@router.patch("/{refund_id}/mark-paid", response_model=RefundRequestOut)
def mark_refund_paid(
    refund_id: int, request: Request, user: User = Depends(require_owner), db: DbSession = Depends(get_db)
):
    """Only the owner — whoever can actually move the money — marks a
    refund paid. Also drops a matching Payment record (type "Refund") so
    it shows up in the books without double entry."""
    refund = _get_refund_or_404(db, refund_id)
    if refund.status == "Paid":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Already marked paid.")

    payment = Payment(
        occurred_on=datetime.date.today(),
        type="Refund",
        payee=refund.order.customer.full_name if refund.order.customer else refund.order.order_number,
        reference=refund.order.order_number,
        amount_inr=refund.amount_inr,
        paid_by=user.full_name or user.email,
        notes=refund.reason,
        created_by=user.id,
    )
    db.add(payment)
    db.flush()

    refund.status = "Paid"
    refund.paid_by = user.id
    refund.paid_at = datetime.datetime.now(datetime.timezone.utc)
    refund.payment_id = payment.id
    record_audit(
        db, request, user, "refund.mark_paid", "refund_request", str(refund.id),
        after={"amount_inr": str(refund.amount_inr), "payment_id": payment.id},
    )
    db.commit()
    return _out(db, _get_refund_or_404(db, refund_id))


@router.delete("/{refund_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_refund(
    refund_id: int, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    refund = _get_refund_or_404(db, refund_id)
    if refund.status == "Paid":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Can't delete a refund that's already been paid.")
    record_audit(
        db, request, user, "refund.delete", "refund_request", str(refund.id),
        before={"order_number": refund.order.order_number, "amount_inr": str(refund.amount_inr)},
    )
    db.delete(refund)
    db.commit()
