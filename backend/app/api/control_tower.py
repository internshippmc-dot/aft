from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.boxes import _box_options, _get_box_or_404
from app.audit import record_audit
from app.auth.deps import get_current_user, require_ops
from app.db import get_db
from app.domain.control_tower import PIPELINE_STAGES, build_card
from app.models.box import Box
from app.models.user import User
from app.schemas.control_tower import ControlTowerCard, ControlTowerUpdate

router = APIRouter(prefix="/control-tower", tags=["control-tower"])


@router.get("", response_model=list[ControlTowerCard])
def list_cards(_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    boxes = db.scalars(select(Box).options(*_box_options()))
    return [build_card(db, b) for b in boxes]


@router.patch("/{aft_number}", response_model=ControlTowerCard)
def update_card(
    aft_number: str, body: ControlTowerUpdate, request: Request,
    user: User = Depends(require_ops), db: DbSession = Depends(get_db),
):
    box = _get_box_or_404(db, aft_number)
    if body.pipeline_stage is not None and body.pipeline_stage not in PIPELINE_STAGES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"pipeline_stage must be one of {PIPELINE_STAGES}")

    before = {"pipeline_stage": box.pipeline_stage, "next_action": box.next_action, "flagged": box.flagged}
    for field in ("pipeline_stage", "next_action", "mf_number", "cn_tracking", "pl_status", "flagged", "flag_reason"):
        value = getattr(body, field)
        if value is not None:
            setattr(box, field, value)
    db.flush()
    record_audit(
        db, request, user, "box.control_tower_update", "box", box.aft_number,
        before=before, after={"pipeline_stage": box.pipeline_stage, "next_action": box.next_action, "flagged": box.flagged},
    )
    db.commit()
    db.refresh(box)
    return build_card(db, box)
