import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.audit import record_audit
from app.auth import totp as totp_module
from app.auth.deps import get_current_user, require_csrf
from app.auth.password import hash_password, needs_rehash, verify_password
from app.auth.ratelimit import check_rate_limit
from app.auth.session import CSRF_COOKIE, SESSION_COOKIE, create_session, resolve_session, revoke_session
from app.config import get_settings
from app.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, MeResponse, TotpConfirmIn, TotpDisableIn, TotpEnrollStartOut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GENERIC_LOGIN_ERROR = "That email and password combination did not match."
TOTP_REQUIRED_ERROR = "Enter your two-factor authentication code."


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

    if user.totp_enrolled_at is not None:
        # Password was right; a missing code is just "we haven't asked yet"
        # from the login form's point of view, not an attacker guessing —
        # don't burn a lockout attempt on it. A wrong code does count,
        # same as a wrong password, since it's the same brute-force surface.
        if not body.totp_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=TOTP_REQUIRED_ERROR)
        if not totp_module.verify_code(user.totp_secret, body.totp_code):
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = now + datetime.timedelta(minutes=15)
            db.commit()
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    user.failed_attempts = 0
    user.locked_until = None
    raw_session, csrf = create_session(db, user, ip, request.headers.get("user-agent"))
    record_audit(db, request, user, "user.login", "user", str(user.id))
    db.commit()

    _set_auth_cookies(response, raw_session, csrf)
    return MeResponse(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        totp_enrolled=user.totp_enrolled_at is not None,
    )


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
    return MeResponse(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        totp_enrolled=user.totp_enrolled_at is not None,
    )


@router.post("/totp/enroll/start", response_model=TotpEnrollStartOut)
def totp_enroll_start(
    request: Request, user: User = Depends(get_current_user), _csrf: None = Depends(require_csrf),
    db: DbSession = Depends(get_db),
):
    if user.totp_enrolled_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Two-factor authentication is already enabled. Disable it first to re-enroll.",
        )
    secret = totp_module.generate_secret()
    user.totp_secret = secret  # pending until /enroll/confirm — totp_enrolled_at stays null
    db.commit()
    return TotpEnrollStartOut(secret=secret, provisioning_uri=totp_module.provisioning_uri(user.email, secret))


@router.post("/totp/enroll/confirm", response_model=MeResponse)
def totp_enroll_confirm(
    body: TotpConfirmIn, request: Request, user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf), db: DbSession = Depends(get_db),
):
    if not user.totp_secret or user.totp_enrolled_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="No pending two-factor enrollment to confirm.")
    if not totp_module.verify_code(user.totp_secret, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="That code didn't match. Try again.")
    user.totp_enrolled_at = datetime.datetime.now(datetime.timezone.utc)
    record_audit(db, request, user, "user.totp_enabled", "user", str(user.id))
    db.commit()
    return MeResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role, totp_enrolled=True)


@router.post("/totp/disable", response_model=MeResponse)
def totp_disable(
    body: TotpDisableIn, request: Request, user: User = Depends(get_current_user),
    _csrf: None = Depends(require_csrf), db: DbSession = Depends(get_db),
):
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")
    user.totp_secret = None
    user.totp_enrolled_at = None
    record_audit(db, request, user, "user.totp_disabled", "user", str(user.id))
    db.commit()
    return MeResponse(id=user.id, email=user.email, full_name=user.full_name, role=user.role, totp_enrolled=False)
