
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from src.api.endpoints.auth import router as auth_router
from src.api.endpoints.titles import router as titles_router
from src.core.database import Base, engine
from src.models.title import Title  # Registers the model
from src.models.user import User  # Registers the model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Temporary development setup.
    # Alembic migrations will replace create_all.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

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
    return {"status": "healthy", "database": "connected"}
