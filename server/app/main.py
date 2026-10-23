import asyncio
import ipaddress
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, urlsplit
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import delete, text
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.redis import close_redis_client, get_redis_client
from app.db.session import AsyncSessionLocal
from app.db.models.security_event import SecurityRequestEvent
from app.repositories.exam_repository import ExamRepository
from app.repositories.community_chat_repository import CommunityChatRepository
from app.services.exam_service import ExamService
from app.services.ranking_service import RankingService
from app.repositories.whiteboard_repository import WhiteboardRepository


async def periodic_expired_attempts_sweeper():
    """Background task to auto-submit expired in-progress attempts."""
    while True:
        try:
            await asyncio.sleep(60)  # check every minute
            async with AsyncSessionLocal() as session:
                exam_repo = ExamRepository(session)
                expired_attempts = await exam_repo.list_expired_in_progress_attempts()
                if expired_attempts:
                    logger.info("Sweeper found %d expired attempts to auto-submit", len(expired_attempts))
                    exam_service = ExamService(session)
                    for att in expired_attempts:
                        try:
                            await exam_service.submit_attempt(att.id, att.student_id, is_auto=True)
                            logger.info("Auto-submitted expired attempt %s", att.id)
                        except Exception as e:
                            logger.error("Error auto-submitting attempt %s: %s", att.id, e)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Exception in periodic sweeper: %s", e)


async def periodic_expired_community_chats_sweeper():
    """Delete community conversations 10 hours after their latest message."""
    while True:
        try:
            await asyncio.sleep(60)
            async with AsyncSessionLocal() as session:
                deleted = await CommunityChatRepository(session).delete_expired()
                if deleted:
                    logger.info("Removed %d expired community chat conversations", deleted)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Exception in community chat sweeper: %s", e)


async def periodic_expired_whiteboard_messages_sweeper():
    """Permanently delete live-class messages once their 10-minute TTL elapses."""
    while True:
        try:
            await asyncio.sleep(30)
            async with AsyncSessionLocal() as session:
                deleted = await WhiteboardRepository(session).delete_expired_messages()
                if deleted:
                    logger.info("Removed %d expired live-class messages", deleted)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Exception in live-class message sweeper: %s", e)


async def periodic_security_event_retention_sweeper():
    """Keep the live security feed bounded to the most recent 30 days."""
    while True:
        try:
            await asyncio.sleep(24 * 60 * 60)
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    delete(SecurityRequestEvent).where(
                        SecurityRequestEvent.created_at < datetime.now(timezone.utc) - timedelta(days=30)
                    )
                )
                await session.commit()
                if result.rowcount:
                    logger.info("Removed %d expired security request events", result.rowcount)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Exception in security event retention sweeper: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("Starting %s in %s mode...", settings.APP_NAME, settings.APP_ENV)
    if settings.is_production:
        missing = [
            name
            for name, value in (
                ("CLERK_ISSUER", settings.CLERK_ISSUER),
                ("CLERK_AUDIENCE", settings.CLERK_AUDIENCE),
                ("CLERK_SECRET_KEY", settings.CLERK_SECRET_KEY),
                ("CLERK_WEBHOOK_SECRET", settings.CLERK_WEBHOOK_SECRET),
                ("SUPABASE_URL", settings.SUPABASE_URL),
                ("SUPABASE_SERVICE_KEY", settings.SUPABASE_SERVICE_KEY),
            )
            if not value
        ]
        if settings.DEBUG or settings.ALLOW_DEV_AUTH_BYPASS:
            raise RuntimeError("DEBUG and ALLOW_DEV_AUTH_BYPASS must be disabled in production")
        if missing:
            raise RuntimeError(
                "Required production security settings are missing: " + ", ".join(missing)
            )
        invalid_origins = []
        for origin in settings.CORS_ORIGINS:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme != "https"
                or not parsed.netloc
                or "*" in parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                invalid_origins.append(origin)
        if not settings.CORS_ORIGINS or invalid_origins:
            raise RuntimeError("Production CORS_ORIGINS must contain only exact HTTPS origins")
        jwks_url = settings.CLERK_JWKS_URL or "https://api.clerk.com/v1/jwks"
        if urlsplit(jwks_url).scheme != "https":
            raise RuntimeError("CLERK_JWKS_URL must use HTTPS in production")
        if urlsplit(settings.SUPABASE_URL or "").scheme != "https":
            raise RuntimeError("SUPABASE_URL must use HTTPS in production")
        for setting_name, configured_url in (
            ("DATABASE_URL", settings.DATABASE_URL),
            ("REDIS_URL", settings.REDIS_URL),
        ):
            hostname = urlsplit(configured_url).hostname
            if not hostname or hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
                raise RuntimeError(f"{setting_name} must point to a production service")
        database_query = parse_qs(urlsplit(settings.DATABASE_URL).query)
        database_tls = database_query.get("sslmode", database_query.get("ssl", []))
        if not database_tls or database_tls[0].lower() not in {
            "require",
            "verify-ca",
            "verify-full",
            "true",
            "1",
        }:
            raise RuntimeError("DATABASE_URL must require TLS in production")
        if urlsplit(settings.REDIS_URL).scheme != "rediss":
            raise RuntimeError("REDIS_URL must use TLS (rediss://) in production")
        if not settings.RATE_LIMIT_ENABLED:
            raise RuntimeError("RATE_LIMIT_ENABLED must be enabled in production")

    # Initialize Redis connection
    await get_redis_client()

    # Rebuild cold-start leaderboard if needed
    try:
        async with AsyncSessionLocal() as session:
            ranking_svc = RankingService(session)
            await ranking_svc.rebuild_all_scores()
    except Exception as e:
        logger.warning("Initial leaderboard rebuild skipped or failed (DB may not be migrated yet): %s", e)

    # Start background sweeper
    sweeper_task = asyncio.create_task(periodic_expired_attempts_sweeper())
    community_chat_sweeper_task = asyncio.create_task(
        periodic_expired_community_chats_sweeper()
    )
    whiteboard_chat_sweeper_task = asyncio.create_task(
        periodic_expired_whiteboard_messages_sweeper()
    )
    security_event_sweeper_task = asyncio.create_task(periodic_security_event_retention_sweeper())

    yield

    # Shutdown
    sweeper_task.cancel()
    community_chat_sweeper_task.cancel()
    whiteboard_chat_sweeper_task.cancel()
    security_event_sweeper_task.cancel()
    await asyncio.gather(
        sweeper_task,
        community_chat_sweeper_task,
        whiteboard_chat_sweeper_task,
        security_event_sweeper_task,
        return_exceptions=True,
    )
    await close_redis_client()
    logger.info("Shutdown complete for %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="Full Production Ready Backend for SiliconBrains University",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=None if settings.is_production else r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
    finally:
        # Record API GET traffic only. Never persist query strings, bodies, cookies,
        # or credentials. Exclude the polling endpoint to prevent feed self-noise.
        path = request.url.path
        if (
            request.method == "GET"
            and path.startswith("/api/v1/")
            and not path.startswith("/api/v1/admin/security")
            and path not in {"/api/v1/health", "/api/v1/health/"}
        ):
            safe_path = re.sub(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", "/:id", path)
            safe_path = re.sub(r"/\d+(?=/|$)", "/:id", safe_path)[:240]
            host = request.client.host if request.client else None
            try:
                address = ipaddress.ip_address(host) if host else None
                if address and address.version == 4:
                    client_ip = str(ipaddress.ip_network(f"{address}/24", strict=False).network_address) + "/24"
                elif address:
                    client_ip = ":".join(address.exploded.split(":")[:4]) + "::/64"
                else:
                    client_ip = None
            except ValueError:
                client_ip = None
            try:
                async with AsyncSessionLocal() as telemetry_db:
                    telemetry_db.add(SecurityRequestEvent(
                        actor_id=getattr(request.state, "db_user_id", None),
                        path=safe_path,
                        method="GET",
                        status_code=response.status_code if response is not None else 500,
                        duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
                        client_ip=client_ip,
                        user_agent=request.headers.get("user-agent", "")[:240] or None,
                    ))
                    await telemetry_db.commit()
            except Exception as telemetry_error:
                logger.warning("Security request telemetry write failed: %s", telemetry_error)

    if response is None:
        raise RuntimeError("Request failed before a response was created")
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Exception Handlers (Standard error shape from Docs/architecture.md & Docs/rules.md)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}:
        logger.warning(
            "Access denied status=%d actor_id=%s client=%s path=%s request_id=%s",
            exc.status_code,
            getattr(request.state, "user_id", "anonymous"),
            request.client.host if request.client else "unknown",
            request.url.path,
            getattr(request.state, "request_id", "unknown"),
        )
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": None,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Request validation failed path=%s request_id=%s",
        request.url.path,
        getattr(request.state, "request_id", "unknown"),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload.",
                "details": None if settings.is_production else jsonable_encoder(exc.errors()),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please contact support.",
                "details": str(exc) if settings.DEBUG else None,
            }
        },
    )


# Health Checks & Root
@app.get("/")
@app.head("/")
async def root():
    return {
        "message": f"{settings.APP_NAME} is running",
        "status": "online",
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/health",
    }


@app.get("/health")
@app.get(f"{settings.API_V1_PREFIX}/health")
async def health_check():
    db_ok = False
    redis_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    try:
        redis = await get_redis_client()
        redis_ok = await redis.ping()
    except Exception:
        redis_ok = False

    return {
        "status": "healthy" if db_ok and redis_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
    }


# Mount API Routers
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
