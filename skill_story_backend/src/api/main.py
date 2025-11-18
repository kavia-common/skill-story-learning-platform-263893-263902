import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .modules.config import settings
from .modules.db import init_db, close_db
from .modules.errors import ApplicationError, ErrorCode
from .routers import auth, stories, profile, journal, progress, health

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("skill_story_backend")


openapi_tags = [
    {"name": "health", "description": "Service health and status endpoints."},
    {"name": "auth", "description": "User registration, login, JWT tokens, and identity."},
    {"name": "stories", "description": "Stories, episodes, and branching choices."},
    {"name": "progress", "description": "XP and story progression endpoints."},
    {"name": "profile", "description": "User profile endpoints."},
    {"name": "journal", "description": "Reflection journal endpoints."},
]


app = FastAPI(
    title="Skill Story LMS API",
    description="Backend API for interactive stories, XP tracking, and journaling.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)


# Basic rate limiting stub (no-op, placeholder for future)
@app.middleware("http")
async def rate_limit_stub(request: Request, call_next):
    # Placeholder for future token bucket/redis-based limiter
    response = await call_next(request)
    response.headers["X-RateLimit-Policy"] = "stub"
    return response


# Centralized error handling
@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError):
    logger.warning("ApplicationError", extra={"path": request.url.path, "code": exc.error_code.value})
    envelope = {
        "success": False,
        "error": {
            "code": exc.error_code.value,
            "message": exc.message,
            "details": exc.details,
        },
    }
    return JSONResponse(status_code=exc.status_code, content=envelope)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    envelope = {
        "success": False,
        "error": {
            "code": ErrorCode.INTERNAL_ERROR.value,
            "message": "An unexpected error occurred",
            "details": {},
        },
    }
    return JSONResponse(status_code=500, content=envelope)


# Startup/Shutdown events
@app.on_event("startup")
async def on_startup():
    logger.info(
        "Starting Skill Story LMS API",
        extra={
            "host": "0.0.0.0",
            "port": 3001,
            "db_driver": (settings.db_url().split('://', 1)[0] if settings.DATABASE_URL or settings.DB_HOST else None),
            "seed_deferred": settings.DB_SEED_DEFER,
            "db_retries": settings.DB_CONNECT_MAX_RETRIES,
            "db_backoff": settings.DB_CONNECT_BACKOFF_SECONDS,
        },
    )
    settings.validate()  # Validate envs early
    await init_db()  # Create tables and seed demo data


@app.on_event("shutdown")
async def on_shutdown():
    await close_db()
    logger.info("Stopped Skill Story LMS API")


# Register routers with /api prefix
app.include_router(health.router, prefix="")
app.include_router(auth.router, prefix="/api")
app.include_router(stories.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(journal.router, prefix="/api")


# PUBLIC_INTERFACE
@app.get(
    "/docs/websocket-help",
    tags=["health"],
    summary="WebSocket usage note",
    description="This API currently does not provide WebSocket endpoints. Future versions will document real-time endpoints here.",
)
async def websocket_usage_note():
    """Provide a placeholder docs route for WebSocket integration notes."""
    return {"success": True, "data": {"websocket": "No real-time endpoints yet"}}
