from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from app.auth.session import CSRF_COOKIE, SESSION_COOKIE, resolve_session
from app.db import get_db
from app.models.user import User, UserRole


def get_current_user(request: Request, db: DbSession = Depends(get_db)) -> User:
    raw = request.cookies.get(SESSION_COOKIE)
    session = resolve_session(db, raw)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not signed in.")
    user = db.get(User, session.user_id)
    if user is None or user.disabled_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Account disabled.")
    request.state.user = user
    request.state.session = session
    return user


def require_csrf(request: Request) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie_value = request.cookies.get(CSRF_COOKIE)
    header_value = request.headers.get("X-CSRF-Token")
    if not cookie_value or not header_value or cookie_value != header_value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid.")


def require_role(*roles: UserRole) -> Callable[[User], User]:
    def _dep(user: User = Depends(get_current_user), _csrf: None = Depends(require_csrf)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not permitted for this role.")
        return user

    return _dep


require_owner = require_role(UserRole.owner)
require_ops = require_role(UserRole.owner, UserRole.ops)
require_any = require_role(UserRole.owner, UserRole.ops, UserRole.viewer)
