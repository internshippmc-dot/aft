from fastapi import Request
from sqlalchemy.orm import Session as DbSession

from app.models.audit import AuditLog
from app.models.user import User


def record_audit(
    db: DbSession,
    request: Request,
    actor: User | None,
    action: str,
    object_type: str,
    object_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """PRD F10 / SECURITY.md section 9 — every write records actor, ip, before, after."""
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_ip=request.client.host if request.client else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        before=before,
        after=after,
    )
    db.add(entry)
    db.flush()
