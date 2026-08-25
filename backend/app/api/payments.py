from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.models.box import Box
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentOut, PaymentUpdate

router = APIRouter(prefix="/payments", tags=["payments"])


def _out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        occurred_on=p.occurred_on,
        type=p.type,
        payee=p.payee,
        reference=p.reference,
        box_aft_number=p.box.aft_number if p.box else None,
        amount_inr=p.amount_inr,
        paid_by=p.paid_by,
        method=p.method,
        notes=p.notes,
        created_at=p.created_at,
    )


@router.get("", response_model=list[PaymentOut])
def list_payments(_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    rows = db.scalars(
        select(Payment).options(selectinload(Payment.box)).order_by(Payment.occurred_on.desc(), Payment.id.desc())
    )
    return [_out(p) for p in rows]


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    box = None
    if body.box_aft_number:
        box = db.scalar(select(Box).where(Box.aft_number == body.box_aft_number))
        if box is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No box {body.box_aft_number}.")

    payment = Payment(
        occurred_on=body.occurred_on,
        type=body.type,
        payee=body.payee,
        reference=body.reference,
        box_id=box.id if box else None,
        amount_inr=body.amount_inr,
        paid_by=body.paid_by,
        method=body.method,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(payment)
    db.flush()
    record_audit(
        db, request, user, "payment.create", "payment", str(payment.id),
        after={"amount_inr": str(body.amount_inr), "type": body.type, "payee": body.payee},
    )
    db.commit()
    db.refresh(payment)
    return _out(payment)


def _get_payment_or_404(db: DbSession, payment_id: int) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id).options(selectinload(Payment.box)))
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No payment {payment_id}.")
    return payment


@router.patch("/{payment_id}", response_model=PaymentOut)
def update_payment(
    payment_id: int, body: PaymentUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    payment = _get_payment_or_404(db, payment_id)
    before = _out(payment).model_dump(mode="json")

    if "box_aft_number" in body.model_fields_set:
        if body.box_aft_number:
            box = db.scalar(select(Box).where(Box.aft_number == body.box_aft_number))
            if box is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No box {body.box_aft_number}.")
            payment.box_id = box.id
        else:
            payment.box_id = None

    for field in ("occurred_on", "type", "payee", "reference", "amount_inr", "paid_by", "method", "notes"):
        value = getattr(body, field)
        if field in body.model_fields_set and (value is not None or field in ("reference", "method", "notes")):
            setattr(payment, field, value)

    db.flush()
    record_audit(
        db, request, user, "payment.update", "payment", str(payment.id),
        before=before, after=_out(payment).model_dump(mode="json"),
    )
    db.commit()
    db.refresh(payment)
    return _out(payment)


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: int, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    payment = _get_payment_or_404(db, payment_id)
    record_audit(db, request, user, "payment.delete", "payment", str(payment.id), before=_out(payment).model_dump(mode="json"))
    db.delete(payment)
    db.commit()
