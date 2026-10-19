
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text

from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.titles import router as titles_router
from src.core.database import Base, engine
from src.core.request_logging import RequestLoggingMiddleware
from src.models.title import Title  # Registers the model
from src.models.user import User  # Registers the model


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="OTT Content Aggregator API",
    description="Axlero Python Internship Project",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

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
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
            },
        ) from exc

    return {
        "status": "healthy",
        "database": "connected",
    }
