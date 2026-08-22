from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.api.orders import _find_order
from app.audit import record_audit
from app.auth.deps import require_owner, require_ops
from app.db import get_db
from app.integrations import ithink, shopify
from app.models.plumbing import SyncState
from app.models.user import User
from app.schemas.common import ShipmentOut
from app.schemas.integrations import SyncStateOut, SyncSummary

router = APIRouter(prefix="/integrations", tags=["integrations"])


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
    order_number: str, request: Request, user: User = Depends(require_ops), db: DbSession = Depends(get_db)
):
    order = _find_order(db, order_number)
    try:
        shipment = ithink.book_shipment(db, order)
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
    )
