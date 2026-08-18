import datetime
import hashlib
import secrets

from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.models.user import Session as SessionModel, User

settings = get_settings()

SESSION_COOKIE = "sid"
CSRF_COOKIE = "csrf_token"


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_session(db: DbSession, user: User, ip: str | None, user_agent: str | None) -> tuple[str, str]:
    """Returns (raw_session_token, csrf_token)."""
    raw = secrets.token_urlsafe(32)
    now = datetime.datetime.now(datetime.timezone.utc)
    row = SessionModel(
        id=_hash_token(raw),
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + datetime.timedelta(hours=settings.session_absolute_hours),
        ip=ip,
        user_agent=user_agent,
    )
    db.add(row)
    db.flush()
    csrf = secrets.token_urlsafe(24)
    return raw, csrf


def resolve_session(db: DbSession, raw: str | None) -> SessionModel | None:
    if not raw:
        return None
    row = db.get(SessionModel, _hash_token(raw))
    if row is None or row.revoked_at is not None:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    if row.expires_at <= now:
        return None
    idle_cutoff = row.last_seen_at + datetime.timedelta(minutes=settings.session_idle_minutes)
    if idle_cutoff <= now:
        row.revoked_at = now
        db.commit()
        return None
    row.last_seen_at = now
    db.commit()
    return row


def revoke_session(db: DbSession, raw: str) -> None:
    row = db.get(SessionModel, _hash_token(raw))
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.datetime.now(datetime.timezone.utc)
        db.flush()
