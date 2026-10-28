import asyncio
import os
import tempfile
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

from src.core.database import Base
from src.main import app, lifespan
import src.models


def test_app_import_and_openapi_generation_without_db():
    """Verify app imports and generates OpenAPI schema without needing a live DB."""
    schema = app.openapi()
    assert "paths" in schema
    assert "/api/v1/auth/register" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/auth/me" in schema["paths"]
    assert "/api/v1/titles" in schema["paths"]


@pytest.mark.anyio
async def test_lifespan_startup_and_shutdown_without_live_db():
    """Verify lifespan context starts and exits cleanly without attempting DB connection."""
    async with lifespan(app):
        # App is in running state
        assert app.title == "OTT Content Aggregator API"


def test_alembic_metadata_registration():
    """Verify Base.metadata has both users and titles tables registered."""
    table_names = set(Base.metadata.tables.keys())
    assert "users" in table_names
    assert "titles" in table_names


def test_migration_lifecycle_isolated_db():
    """Test full Alembic upgrade, schema verification, and downgrade on a disposable database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_alembic.db").replace("\\", "/")
        db_url = f"sqlite+aiosqlite:///{db_path}"

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        # 2. Inspect created schema using sync sqlite engine
        sync_engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(sync_engine)
        created_tables = set(inspector.get_table_names())

        assert "alembic_version" in created_tables
        assert "users" in created_tables
        assert "titles" in created_tables

        # Check users columns and indexes
        user_columns = {c["name"] for c in inspector.get_columns("users")}
        assert {"id", "email", "username", "hashed_password", "is_active", "is_superuser", "created_at"}.issubset(user_columns)

        user_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        assert "ix_users_email" in user_indexes
        assert "ix_users_username" in user_indexes

        # Check titles columns and indexes
        title_columns = {c["name"] for c in inspector.get_columns("titles")}
        assert {"id", "name", "description", "content_type", "release_year", "genre", "platform", "created_at"}.issubset(title_columns)

        title_indexes = {idx["name"] for idx in inspector.get_indexes("titles")}
        assert "ix_titles_name" in title_indexes
        assert "ix_titles_genre" in title_indexes
        assert "ix_titles_platform" in title_indexes

        sync_engine.dispose()

        # 3. Downgrade to base
        command.downgrade(alembic_cfg, "base")

        sync_engine2 = create_engine(f"sqlite:///{db_path}")
        inspector2 = inspect(sync_engine2)
        tables_after_downgrade = set(inspector2.get_table_names())
        assert "users" not in tables_after_downgrade
        assert "titles" not in tables_after_downgrade

        sync_engine2.dispose()

        # 4. Re-upgrade to head to ensure re-apply is clean
        command.upgrade(alembic_cfg, "head")
        sync_engine3 = create_engine(f"sqlite:///{db_path}")
        inspector3 = inspect(sync_engine3)
        assert "users" in set(inspector3.get_table_names())
        assert "titles" in set(inspector3.get_table_names())
        sync_engine3.dispose()


@pytest.mark.anyio
async def test_security_headers_middleware():
    """Verify production security headers are set on HTTP responses."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get("/")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.anyio
async def test_liveness_and_readiness_probes():
    """Verify /health/live and /health/ready probe endpoints."""
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Liveness probe returns 200 alive without database queries
        live_res = await client.get("/health/live")
        assert live_res.status_code == 200
        assert live_res.json() == {"status": "alive"}

        # Readiness probe reports database & redis status
        ready_res = await client.get("/health/ready")
        assert ready_res.status_code in (200, 503)
        data = ready_res.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
