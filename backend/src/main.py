"""
CrewAI Orchestration Platform - Backend API
FastAPI application entry point
"""

import os
import logging
from typing import List, Optional
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

# Configure structured logging (JSON vs pretty) based on LOG_FORMAT
_log_format = os.getenv("LOG_FORMAT", "json").lower()
_processors = [
    structlog.stdlib.filter_by_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
]
if _log_format == "pretty":
    _processors.append(structlog.dev.ConsoleRenderer())
else:
    _processors.append(structlog.processors.JSONRenderer())

structlog.configure(
    processors=_processors,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Resolve CORS settings from environment
def _get_allowed_origins() -> List[str]:
    env_val = os.getenv("ALLOWED_ORIGINS")
    if env_val:
        return [o.strip() for o in env_val.split(",") if o.strip()]
    # Sensible localhost defaults for dev
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://frontend:3000",
    ]


def _get_allowed_origin_regex() -> Optional[str]:
    # Support either name; prefer ALLOWED_ORIGIN_REGEX
    allow_all = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"
    if allow_all:
        # Allow any http(s) origin (use with caution)
        return r"^https?://.*$"
    return os.getenv("ALLOWED_ORIGIN_REGEX") or os.getenv("ALLOW_ORIGIN_REGEX")


# Configure base logging level from env
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.getLogger().setLevel(_LOG_LEVEL)
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_name).setLevel(_LOG_LEVEL)

# Enable detailed SQL logs if requested
if os.getenv("SQL_ECHO", "false").lower() == "true":
    logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

# Allow raising specific module log levels via comma-separated env
_debug_modules = os.getenv("LOG_DEBUG_MODULES")
if _debug_modules:
    for _mod in [m.strip() for m in _debug_modules.split(",") if m.strip()]:
        logging.getLogger(_mod).setLevel(logging.DEBUG)

# Create FastAPI application
app = FastAPI(
    title="Automation Platform API",
    description="Multi-tenant platform for creating, managing, and executing AI workflows",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware (env-driven)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_origin_regex=_get_allowed_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Optional request logging middleware
if os.getenv("LOG_HTTP", "false").lower() == "true":
    @app.middleware("http")
    async def _log_http_requests(request, call_next):
        start = logging.default_timer() if hasattr(logging, 'default_timer') else None
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            try:
                duration_ms = None
                if start is not None:
                    import time as _t
                    duration_ms = int((_t.perf_counter() - start) * 1000)  # type: ignore[arg-type]
            except Exception:
                duration_ms = None
            structlog.get_logger().info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status_code=getattr(response, "status_code", 0),
                duration_ms=duration_ms,
                client_ip=(request.client.host if request.client else None),
            )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("starting_crewai_platform", environment="development")

    try:
        # Initialize database tables (synchronous)
        from .db import init_db
        init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))

    try:
        # Warm up Redis client (optional)
        from .db.redis import get_redis_client
        get_redis_client()
        logger.info("redis_initialized")
    except Exception as e:
        logger.error("redis_init_failed", error=str(e))

    # Seed system roles (idempotent)
    try:
        from .db import SessionLocal
        from .services.role_seed import seed_system_roles

        db = SessionLocal()
        try:
            seed_system_roles(db)
            logger.info("system_roles_seeded")
        finally:
            db.close()
    except Exception as e:
        logger.error("system_roles_seed_failed", error=str(e))

    # Seed default prompts (idempotent) unless disabled
    try:
        seed_enabled = os.getenv("SEED_DEFAULT_PROMPTS", "true").lower() != "false"
        if seed_enabled:
            from .db import SessionLocal
            from .services.prompt_seed import seed_default_prompts
            from .models import Tenant, User

            db = SessionLocal()
            try:
                # Import TenantStatus enum
                from .models.tenant import TenantStatus

                # Query first active tenant and first active user (typically admin) for seeding
                first_tenant = db.query(Tenant).filter(Tenant.status == TenantStatus.ACTIVE).first()
                first_user = db.query(User).filter(User.is_active == True).first()

                if first_tenant and first_user:
                    seed_default_prompts(db, tenant_id=first_tenant.id, user_id=first_user.id)
                    logger.info("default_prompts_seeded", tenant_id=str(first_tenant.id), user_id=str(first_user.id))
                else:
                    logger.warning("default_prompts_skipped", reason="no_active_tenant_or_user")
            finally:
                db.close()
    except Exception as e:
        logger.error("default_prompts_seed_failed", error=str(e))

    # Start Redis notification listener for WebSocket notifications
    try:
        from .websocket.redis_listener import start_notification_listener
        await start_notification_listener()
        logger.info("redis_notification_listener_started")
    except Exception as e:
        logger.error("redis_notification_listener_failed", error=str(e))


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("shutting_down_crewai_platform")

    # Stop Redis notification listener
    try:
        from .websocket.redis_listener import stop_notification_listener
        await stop_notification_listener()
        logger.info("redis_notification_listener_stopped")
    except Exception as e:
        logger.error("redis_notification_listener_stop_failed", error=str(e))

    # Using SQLAlchemy engine pool; no explicit close required here.
    # Redis client is managed as a process-global; no explicit close on shutdown.


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    Returns service status and database connectivity
    """
    health_status = {
        "status": "healthy",
        "service": "crewai-platform-backend",
        "version": "1.0.0",
        "checks": {}
    }

    # Check database connection
    try:
        from .db import check_db_health
        db_healthy = await check_db_health()
        health_status["checks"]["database"] = "healthy" if db_healthy else "unhealthy"
    except Exception as e:
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Redis connection
    try:
        from .db.redis import check_redis_health
        redis_healthy = await check_redis_health()
        health_status["checks"]["redis"] = "healthy" if redis_healthy else "unhealthy"
    except Exception as e:
        health_status["checks"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(status_code=status_code, content=health_status)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Automation Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include API routers
from .api.v1 import api_router

app.include_router(api_router, prefix="/api/v1")


# ===== WEBSOCKET ROUTES (Phase 004) =====

# WebSocket endpoint for execution output streaming
@app.websocket("/ws/executions/{execution_id}/stream")
async def websocket_execution_stream(
    websocket: WebSocket,
    execution_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for streaming execution output in real-time.

    Features:
    - JWT authentication via query parameter
    - Replays last 100 buffered lines on connection
    - Streams live execution events from Redis pub/sub
    - Events: execution.started, execution.output, execution.progress, execution.completed, execution.error

    Usage:
        ws://localhost:8000/ws/executions/{execution_id}/stream?token={jwt_token}
    """
    from .websocket.execution_stream import stream_execution_output
    await stream_execution_output(websocket, execution_id, token)


# WebSocket endpoint for queue position updates
@app.websocket("/ws/executions/{execution_id}/queue")
async def websocket_queue_updates(
    websocket: WebSocket,
    execution_id: str,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for streaming queue position updates.

    Features:
    - JWT authentication via query parameter
    - Real-time queue position and estimated wait time
    - Closes when execution starts or fails

    Usage:
        ws://localhost:8000/ws/executions/{execution_id}/queue?token={jwt_token}
    """
    from .websocket.queue_updates import stream_queue_updates
    await stream_queue_updates(websocket, execution_id, token)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
