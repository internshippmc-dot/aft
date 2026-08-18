from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.api.orders import _find_order
from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.models.order import Order
from app.models.return_case import ReturnCase
from app.models.user import User
from app.schemas.return_case import ReturnCreate, ReturnOut, ReturnUpdate

router = APIRouter(prefix="/returns", tags=["returns"])


def _out(r: ReturnCase) -> ReturnOut:
    return ReturnOut(
        id=r.id,
        order_number=r.order.order_number,
        customer_name=r.order.customer.full_name if r.order.customer else None,
        type=r.type,
        reason=r.reason,
        status=r.status,
        requested_on=r.requested_on,
        next_action=r.next_action,
        notes=r.notes,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _options():
    return (selectinload(ReturnCase.order).selectinload(Order.customer),)


@router.get("", response_model=list[ReturnOut])
def list_returns(
    order_number: str | None = None,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    query = select(ReturnCase).options(*_options()).order_by(ReturnCase.created_at.desc())
    if order_number:
        query = query.join(Order).where(Order.order_number == order_number)
    return [_out(r) for r in db.scalars(query)]


@router.post("", response_model=ReturnOut, status_code=status.HTTP_201_CREATED)
def create_return(
    body: ReturnCreate, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    order = _find_order(db, body.order_number)
    case = ReturnCase(
        order_id=order.id,
        type=body.type,
        reason=body.reason,
        requested_on=body.requested_on,
        next_action=body.next_action,
        notes=body.notes,
        created_by=user.id,
    )
    db.add(case)
    db.flush()
    record_audit(db, request, user, "return.create", "return", str(case.id), after={"order_number": order.order_number, "type": body.type})
    db.commit()
    db.refresh(case)
    case = db.scalar(select(ReturnCase).where(ReturnCase.id == case.id).options(*_options()))
    return _out(case)


@router.patch("/{return_id}", response_model=ReturnOut)
def update_return(
    return_id: int, body: ReturnUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    case = db.scalar(select(ReturnCase).where(ReturnCase.id == return_id).options(*_options()))
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No such return.")
    before = {"status": case.status, "next_action": case.next_action, "notes": case.notes}
    if body.status is not None:
        case.status = body.status
    if body.next_action is not None:
        case.next_action = body.next_action
    if body.notes is not None:
        case.notes = body.notes
    db.flush()
    record_audit(
        db, request, user, "return.update", "return", str(case.id),
        before=before, after={"status": case.status, "next_action": case.next_action, "notes": case.notes},
    )
    db.commit()
    db.refresh(case)
    return _out(case)
