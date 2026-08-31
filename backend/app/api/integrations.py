from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.api.orders import _find_order
from app.audit import record_audit
from app.auth.deps import require_owner, require_ops
from app.db import get_db
from app.integrations import ithink, shopify
from app.models.plumbing import SyncState
from app.models.return_case import ReturnCase
from app.models.user import User
from app.schemas.common import ShipmentOut
from app.schemas.integrations import IThinkBookRequest, PickupAddressOut, SyncStateOut, SyncSummary

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/ithink/pickup-addresses", response_model=list[PickupAddressOut])
def list_pickup_addresses(_user: User = Depends(require_ops)):
    return [PickupAddressOut(**a) for a in ithink.PICKUP_ADDRESSES]


@router.get("/status", response_model=dict[str, SyncStateOut | None])
def status_(_user: User = Depends(require_owner), db: DbSession = Depends(get_db)):
    out: dict[str, SyncStateOut | None] = {}
    for key in (shopify.SYNC_KEY, ithink.TRACKING_SYNC_KEY):
        state = db.get(SyncState, key)
        out[key] = (
            SyncStateOut(
                cursor_value=state.cursor_value,
                last_success_at=state.last_success_at,
                last_error=state.last_error,
            )
            if state
            else None
        )
    return out


@router.post("/shopify/sync", response_model=SyncSummary)
def sync_shopify(request: Request, user: User = Depends(require_owner), db: DbSession = Depends(get_db)):
    # sync_once() never raises — including "not configured" — it always
    # records failures on sync_state and returns them in the result dict,
    # since it's also called from the unattended background loop.
    result = shopify.sync_once(db)
    record_audit(
        db, request, user, "integrations.shopify_sync", "sync_state", shopify.SYNC_KEY,
        after={"created": result["created"], "updated": result["updated"], "error": result["error"]},
    )
    db.commit()
    return SyncSummary(created=result["created"], updated=result["updated"], error=result["error"])


@router.post("/orders/{order_number}/ithink/book", response_model=ShipmentOut)
def book_ithink_shipment(
    order_number: str, body: IThinkBookRequest, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    order = _find_order(db, order_number)
    try:
        shipment = ithink.book_shipment(db, order, body.pickup_address_id)
    except ithink.IThinkNotConfigured as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface the real iThink error to the operator
        db.rollback()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    record_audit(
        db, request, user, "integrations.ithink_book", "shipment", str(shipment.id),
        after={"order_number": order.order_number, "courier": shipment.courier, "awb": shipment.awb},
    )
    db.commit()
    return ShipmentOut(
        id=shipment.id,
        courier=shipment.courier,
        awb=shipment.awb,
        status=shipment.status,
        handed_over_on=shipment.handed_over_on,
        delivered_on=shipment.delivered_on,
        kind=shipment.kind,
    )


@router.post("/returns/{return_id}/ithink/book", response_model=ShipmentOut)
def book_ithink_return_shipment(
    return_id: int, body: IThinkBookRequest, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    """Books a reverse pickup — courier collects from the customer and brings
    it back to our warehouse — for an existing return/exchange case."""
    return_case = db.get(ReturnCase, return_id)
    if return_case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No return case {return_id}.")
    order = return_case.order
    try:
        shipment = ithink.book_return_shipment(db, order, return_case, body.pickup_address_id)
    except ithink.IThinkNotConfigured as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface the real iThink error to the operator
        db.rollback()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if return_case.status == "Requested":
        return_case.status = "Pickup Scheduled"
    record_audit(
        db, request, user, "integrations.ithink_book_return", "shipment", str(shipment.id),
        after={"order_number": order.order_number, "return_id": return_id, "courier": shipment.courier, "awb": shipment.awb},
    )
    db.commit()
    return ShipmentOut(
        id=shipment.id,
        courier=shipment.courier,
        awb=shipment.awb,
        status=shipment.status,
        handed_over_on=shipment.handed_over_on,
        delivered_on=shipment.delivered_on,
        kind=shipment.kind,
    )
