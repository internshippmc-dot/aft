from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.auth.deps import get_current_user
from app.db import get_db
from app.domain.consolidation import summarize
from app.models.user import User
from app.schemas.consolidation import ConsolidationOut

router = APIRouter(prefix="/consolidation", tags=["consolidation"])


@router.get("", response_model=ConsolidationOut)
def get_consolidation(_user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    s = summarize(db)
    return ConsolidationOut(
        unassigned_weight_kg=s.unassigned_weight_kg,
        unassigned_box_count=s.unassigned_box_count,
        minimum_kg=s.minimum_kg,
        gauge_pct=s.gauge_pct,
        shortfall_kg=s.shortfall_kg,
    )
