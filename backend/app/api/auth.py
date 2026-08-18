import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.audit import record_audit
from app.auth.deps import get_current_user, require_csrf
from app.auth.password import verify_password
from app.auth.ratelimit import check_rate_limit
from app.auth.session import CSRF_COOKIE, SESSION_COOKIE, create_session, resolve_session, revoke_session
from app.config import get_settings
from app.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GENERIC_LOGIN_ERROR = "That email and password combination did not match."


def _set_auth_cookies(response: Response, raw_session: str, csrf: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw_session,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        max_age=settings.session_absolute_hours * 3600,
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
        max_age=settings.session_absolute_hours * 3600,
    )


@router.post("/login", response_model=MeResponse)
def login(body: LoginRequest, request: Request, response: Response, db: DbSession = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:ip:{ip}", max_hits=5, window_seconds=900)
    check_rate_limit(f"login:acct:{body.email.lower()}", max_hits=5, window_seconds=900)

    user = db.scalar(select(User).where(User.email == body.email))

    # SECURITY.md section 2 — identical, constant-shape response for unknown
    # email and wrong password. verify_password still runs against a dummy
    # hash so an unknown email doesn't return measurably faster.
    dummy_hash = "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$AAAAAAAAAAAAAAAAAAAAAA"
    password_ok = verify_password(body.password, user.password_hash if user else dummy_hash)

    if user is None or not password_ok:
        if user is not None:
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    now = datetime.datetime.now(datetime.timezone.utc)
    if user.disabled_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)
    if user.locked_until is not None and user.locked_until > now:
        raise HTTPException(
            status.HTTP_423_LOCKED,
            detail="Too many failed attempts. Try again in 15 minutes.",
        )

    user.failed_attempts = 0
    user.locked_until = None
    raw_session, csrf = create_session(db, user, ip, request.headers.get("user-agent"))
    record_audit(db, request, user, "user.login", "user", str(user.id))
    db.commit()

    _set_auth_cookies(response, raw_session, csrf)
    return MeResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role)


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        session = resolve_session(db, raw)
        if session is not None:
            record_audit(db, request, None, "user.logout", "user", str(session.user_id))
        revoke_session(db, raw)
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)):
    return MeResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role)
