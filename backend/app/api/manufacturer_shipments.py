from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.domain.box_view import _shipment_out
from app.models.box import ManufacturerShipment
from app.models.user import User
from app.schemas.manufacturer_shipment import (
    ManufacturerShipmentCreate,
    ManufacturerShipmentOut,
    ManufacturerShipmentUpdate,
)

router = APIRouter(prefix="/manufacturer-shipments", tags=["manufacturer-shipments"])


def _options():
    return (selectinload(ManufacturerShipment.box),)


@router.get("", response_model=list[ManufacturerShipmentOut])
def list_shipments(
    unbatched: bool = False,
    _user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    query = select(ManufacturerShipment).options(*_options()).order_by(ManufacturerShipment.created_at.desc())
    if unbatched:
        query = query.where(ManufacturerShipment.box_id.is_(None))
    return [_shipment_out(s) for s in db.scalars(query)]


@router.post("", response_model=ManufacturerShipmentOut, status_code=status.HTTP_201_CREATED)
def create_shipment(
    body: ManufacturerShipmentCreate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    shipment = ManufacturerShipment(
        manufacturer=body.manufacturer, so_number=body.so_number, so_date=body.so_date,
        tracking_id=body.tracking_id, boxes_received=body.boxes_received, so_qty=body.so_qty,
        created_by=user.id,
    )
    db.add(shipment)
    db.flush()
    record_audit(
        db, request, user, "manufacturer_shipment.create", "manufacturer_shipment", str(shipment.id),
        after={"so_number": body.so_number, "manufacturer": body.manufacturer},
    )
    db.commit()
    shipment = db.scalar(select(ManufacturerShipment).where(ManufacturerShipment.id == shipment.id).options(*_options()))
    return _shipment_out(shipment)


def _get_or_404(db: DbSession, shipment_id: int) -> ManufacturerShipment:
    shipment = db.scalar(
        select(ManufacturerShipment).where(ManufacturerShipment.id == shipment_id).options(*_options())
    )
    if shipment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No manufacturer shipment {shipment_id}.")
    return shipment


@router.patch("/{shipment_id}", response_model=ManufacturerShipmentOut)
def update_shipment(
    shipment_id: int, body: ManufacturerShipmentUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    shipment = _get_or_404(db, shipment_id)
    if shipment.box_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This shipment is already attached to an AFT batch — edit it from the batch instead.",
        )
    before = {f: getattr(shipment, f) for f in body.model_fields_set}
    for field in body.model_fields_set:
        setattr(shipment, field, getattr(body, field))
    db.flush()
    record_audit(
        db, request, user, "manufacturer_shipment.update", "manufacturer_shipment", str(shipment.id),
        before={k: str(v) if v is not None else None for k, v in before.items()},
        after={k: str(getattr(shipment, k)) if getattr(shipment, k) is not None else None for k in before},
    )
    db.commit()
    db.refresh(shipment)
    return _shipment_out(shipment)


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipment(
    shipment_id: int, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    shipment = _get_or_404(db, shipment_id)
    if shipment.box_id is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This shipment is already attached to an AFT batch and can't be deleted from here.",
        )
    record_audit(
        db, request, user, "manufacturer_shipment.delete", "manufacturer_shipment", str(shipment.id),
        before={"so_number": shipment.so_number},
    )
    db.delete(shipment)
    db.commit()
