from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession, selectinload

from app.auth.deps import require_owner
from app.db import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.admin import AuditEntryOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit", response_model=list[AuditEntryOut])
def list_audit(
    limit: int = Query(default=100, le=500),
    object_type: str | None = None,
    _user: User = Depends(require_owner),
    db: DbSession = Depends(get_db),
):
    """PRD F10 — owner only, immutable, exportable."""
    query = select(AuditLog).options(selectinload(AuditLog.actor)).order_by(AuditLog.occurred_at.desc()).limit(limit)
    if object_type:
        query = query.where(AuditLog.object_type == object_type)
    rows = db.scalars(query).all()
    return [
        AuditEntryOut(
            id=r.id,
            actor_user_id=r.actor_user_id,
            actor_email=r.actor.email if r.actor else None,
            action=r.action,
            object_type=r.object_type,
            object_id=r.object_id,
            before=r.before,
            after=r.after,
            occurred_at=r.occurred_at,
        )
        for r in rows
    ]
