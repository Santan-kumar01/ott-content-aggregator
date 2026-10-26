
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.titles import router as titles_router
from src.core.cache import check_redis_health, close_redis_client, init_redis_client
from src.core.database import engine
from src.core.http_client import close_http_client, init_http_client
from src.models.title import Title  # Registers the model
from src.models.user import User  # Registers the model


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

app.include_router(titles_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")


@app.get("/")
async def root():
    return {
        "message": "OTT Content Aggregator API is running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    redis_status = await check_redis_health()
    return {
        "status": "healthy",
        "database": "connected",
        "redis": redis_status,
    }
