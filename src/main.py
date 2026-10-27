from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.titles import router as titles_router
from src.core.cache import check_redis_health, close_redis_client, init_redis_client
from src.core.database import engine, settings
from src.core.http_client import close_http_client, init_http_client
from src.models.title import Title  # Registers the model
from src.models.user import User  # Registers the model

logger = logging.getLogger("src.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Application startup: initialize Redis cache and shared HTTP client
    await init_redis_client()
    await init_http_client()
    try:
        yield
    finally:
        # Application shutdown: gracefully release HTTP, Redis, and database resources
        await close_http_client()
        await close_redis_client()
        await engine.dispose()


app = FastAPI(
    title="OTT Content Aggregator API",
    description="Axlero Python Internship Project",
    version="0.1.0",
    lifespan=lifespan,
)

# Optional CORS middleware with strictly validated origins (avoiding wildcard with credentials)
if settings.allowed_origins.strip():
    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(titles_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")


@app.get("/")
async def root():
    return {
        "message": "OTT Content Aggregator API is running",
        "docs": "/docs",
    }


@app.get("/health", summary="Overall health check")
async def health(response: Response):
    """Aggregate health check reporting PostgreSQL and Redis connectivity status."""
    db_status = "connected"
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning("Database health check ping failed: %s", exc)
        db_status = "disconnected"

    redis_status = await check_redis_health()

    if db_status != "connected":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = "unhealthy"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status,
    }


@app.get("/health/live", summary="Liveness probe")
async def liveness():
    """Basic liveness probe confirming the application process is running."""
    return {"status": "alive"}


@app.get("/health/ready", summary="Readiness probe")
async def readiness(response: Response):
    """Readiness probe checking that critical dependencies (DB & Redis) are ready."""
    db_ready = False
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        db_ready = True
    except Exception as exc:
        logger.warning("Readiness probe database check failed: %s", exc)
        db_ready = False

    redis_status = await check_redis_health()
    is_ready = db_ready and (redis_status == "connected")

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "database": "connected" if db_ready else "disconnected",
        "redis": redis_status,
    }
