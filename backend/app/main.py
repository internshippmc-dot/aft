import asyncio
import hashlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import admin, auth, boxes, consignments, consolidation, integrations, orders, payments, returns, search
from app.auth.ratelimit import check_rate_limit
from app.auth.session import SESSION_COOKIE
from app.config import get_settings
from app.db import SessionLocal, engine
from app.integrations import ithink, shopify

settings = get_settings()
logger = logging.getLogger("aft.integrations")


async def _sync_loop(name: str, interval_seconds: int, run_once) -> None:
    # Never lets one bad cycle kill the loop — failures already land on
    # sync_state via run_once itself, this is just a last-resort backstop.
    while True:
        try:
            db = SessionLocal()
            try:
                await asyncio.to_thread(run_once, db)
            finally:
                db.close()
        except Exception:
            logger.exception("%s background sync loop raised unexpectedly", name)
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    tasks = [
        asyncio.create_task(
            _sync_loop("shopify", settings.shopify_sync_interval_seconds, shopify.sync_once)
        ),
        asyncio.create_task(
            _sync_loop("ithink_tracking", settings.ithink_tracking_interval_seconds, ithink.track_once)
        ),
    ]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="Actually Fair Operations Console", version="0.1.0", lifespan=lifespan)

if settings.app_env != "production":
    # Dev only — Vite runs on a different origin. Production serves same-origin (TECH_SPEC.md section 9).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.dev_cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def general_rate_limit(request: Request, call_next):
    # SECURITY.md section 8 — 300/min per user on everything that isn't already
    # limited tighter (login and search have their own checks). Keyed on the
    # session cookie hash when signed in, IP otherwise.
    if request.url.path.startswith("/api/v1"):
        raw = request.cookies.get(SESSION_COOKIE)
        key = "rl:user:" + (hashlib.sha256(raw.encode()).hexdigest() if raw else request.client.host or "anon")
        try:
            check_rate_limit(key, max_hits=300, window_seconds=60)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"code": exc.status_code, "message": exc.detail, "detail": None},
                headers=exc.headers,
            )
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # SECURITY.md section 6 — operator-readable message, no stack traces or SQL.
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail, "detail": None},
        headers=exc.headers,
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(boxes.router, prefix="/api/v1")
app.include_router(consignments.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(consolidation.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(integrations.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(returns.router, prefix="/api/v1")


@app.get("/")
def root():
    # The API root isn't a page — point anyone who lands here at the console.
    return {
        "service": "Actually Fair Operations Console API",
        "docs": "/docs",
        "health": "/health",
        "console": settings.dev_cors_origin if settings.app_env != "production" else "/",
    }


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
