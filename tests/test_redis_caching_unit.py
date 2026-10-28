import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.cache import (
    check_redis_health,
    close_redis_client,
    get_redis_client,
    init_redis_client,
    is_invalidation_pending,
    redis_delete,
    redis_get,
    redis_incr,
    redis_set,
    sanitize_redis_url,
    set_invalidation_pending,
)
from src.core.database import Base, get_db, settings
from src.main import app
from src.services.cache_service import (
    build_catalog_params_hash,
    get_catalog_generation,
    get_catalog_list,
    get_catalog_paginated,
    get_title as get_cached_title,
    invalidate_catalog,
    set_catalog_list,
    set_catalog_paginated,
    set_title as set_cached_title,
)


# ===========================================================================
# 1. URL SANITIZATION & CONFIGURATION TESTS (UNIT)
# ===========================================================================


def test_sanitize_redis_url_masks_password():
    """Verify that credentials in Redis URLs are never exposed in logs."""
    url_with_pass = "redis://:supersecretpass@localhost:6379/0"
    sanitized = sanitize_redis_url(url_with_pass)
    assert "supersecretpass" not in sanitized
    assert ":***@" in sanitized

    url_with_user_pass = "redis://myuser:mypassword@redis-host:6379/1"
    sanitized_user = sanitize_redis_url(url_with_user_pass)
    assert "mypassword" not in sanitized_user
    assert "myuser:***@" in sanitized_user

    url_no_pass = "redis://localhost:6379/0"
    assert sanitize_redis_url(url_no_pass) == url_no_pass
    assert sanitize_redis_url("") == ""


# ===========================================================================
# 2. DETERMINISTIC CACHE KEY GENERATION TESTS (UNIT)
# ===========================================================================


def test_cache_key_hash_determinism():
    """Verify identical parameters always produce the exact same SHA-256 hash."""
    hash1 = build_catalog_params_hash(
        genre="Action",
        platform="Netflix",
        search="Inception",
        release_year=2010,
        sort_by="name",
        sort_order="asc",
        skip=0,
        limit=20,
    )
    hash2 = build_catalog_params_hash(
        genre="  action  ",
        platform="netflix",
        search=" inception ",
        release_year=2010,
        sort_by="name",
        sort_order="asc",
        skip=0,
        limit=20,
    )
    assert hash1 == hash2


def test_cache_key_sensitivity_to_each_parameter():
    """Verify changing any parameter produces a distinctly different hash."""
    base = build_catalog_params_hash(
        genre="Sci-Fi",
        platform="Prime",
        search="Matrix",
        release_year=1999,
        sort_by="release_year",
        sort_order="desc",
        skip=0,
        limit=20,
    )

    # Different search
    diff_search = build_catalog_params_hash(
        genre="Sci-Fi", platform="Prime", search="Matrix Reloaded", release_year=1999
    )
    assert diff_search != base

    # Different genre
    diff_genre = build_catalog_params_hash(
        genre="Drama", platform="Prime", search="Matrix", release_year=1999
    )
    assert diff_genre != base

    # Different platform
    diff_platform = build_catalog_params_hash(
        genre="Sci-Fi", platform="Netflix", search="Matrix", release_year=1999
    )
    assert diff_platform != base

    # Different year
    diff_year = build_catalog_params_hash(
        genre="Sci-Fi", platform="Prime", search="Matrix", release_year=2003
    )
    assert diff_year != base

    # Different sort field
    diff_sort = build_catalog_params_hash(
        genre="Sci-Fi", platform="Prime", search="Matrix", release_year=1999, sort_by="name"
    )
    assert diff_sort != base

    # Different sort order
    diff_order = build_catalog_params_hash(
        genre="Sci-Fi", platform="Prime", search="Matrix", release_year=1999, sort_order="asc"
    )
    assert diff_order != base

    # Different pagination skip
    diff_skip = build_catalog_params_hash(
        genre="Sci-Fi", platform="Prime", search="Matrix", release_year=1999, skip=10
    )
    assert diff_skip != base

    # Different pagination limit
    diff_limit = build_catalog_params_hash(
        genre="Sci-Fi", platform="Prime", search="Matrix", release_year=1999, limit=50
    )
    assert diff_limit != base


# ===========================================================================
# 3. REDIS OUTAGE TOLERANCE & FALLBACK TESTS (MOCK / UNIT)
# ===========================================================================


@pytest.mark.anyio
async def test_redis_get_handles_exceptions_gracefully():
    """Verify redis_get returns None and does not crash when Redis raises errors."""
    with patch("src.core.cache.get_redis_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.get.side_effect = RedisConnectionError("Connection refused")
        mock_client_factory.return_value = mock_client

        val = await redis_get("any:key")
        assert val is None


@pytest.mark.anyio
async def test_redis_set_handles_exceptions_gracefully():
    """Verify redis_set returns False and does not crash when Redis is down."""
    with patch("src.core.cache.get_redis_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.set.side_effect = RedisConnectionError("Connection timed out")
        mock_client_factory.return_value = mock_client

        success = await redis_set("any:key", "value", ex=60)
        assert success is False


@pytest.mark.anyio
async def test_redis_incr_handles_exceptions_gracefully():
    """Verify redis_incr returns None and does not crash when Redis is down."""
    with patch("src.core.cache.get_redis_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.incr.side_effect = RedisConnectionError("Cannot connect")
        mock_client_factory.return_value = mock_client

        result = await redis_incr("catalog:generation")
        assert result is None


@pytest.mark.anyio
async def test_invalidation_failure_marks_pending_state():
    """Verify that if Redis is unreachable during write invalidation, pending state is flagged."""
    set_invalidation_pending(False)
    with patch("src.services.cache_service.redis_incr", new=AsyncMock(return_value=None)):
        success = await invalidate_catalog()
        assert success is False
        assert is_invalidation_pending() is True

    # When Redis recovers, get_catalog_generation should re-sync and clear pending state
    with patch("src.services.cache_service.redis_incr", new=AsyncMock(return_value=42)):
        gen = await get_catalog_generation()
        assert gen == 42
        assert is_invalidation_pending() is False


@pytest.mark.anyio
async def test_health_check_endpoint_redis_connected(unit_client: AsyncClient):
    """Verify /health reports redis status accurately when connected."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_ctx.__aexit__.return_value = None
    mock_engine.connect.return_value = mock_ctx

    with patch("src.main.engine", mock_engine):
        with patch("src.main.check_redis_health", new=AsyncMock(return_value="connected")):
            res = await unit_client.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            assert data["redis"] == "connected"


@pytest.mark.anyio
async def test_health_check_endpoint_redis_disconnected_keeps_app_healthy(
    unit_client: AsyncClient,
):
    """Verify /health returns HTTP 200 and preserves database status when Redis is down."""
    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_ctx.__aexit__.return_value = None
    mock_engine.connect.return_value = mock_ctx

    with patch("src.main.engine", mock_engine):
        with patch("src.main.check_redis_health", new=AsyncMock(return_value="disconnected")):
            res = await unit_client.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert data["database"] == "connected"
            assert data["redis"] == "disconnected"


# ===========================================================================
# 4. FIXTURES & HTTP API TESTS WITH REDIS OUTAGE SIMULATION
# ===========================================================================


@pytest.fixture
async def unit_client():
    """Create isolated SQLite database client for caching unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.fixture
async def unit_auth_headers(unit_client: AsyncClient) -> dict[str, str]:
    """Register and login user for authenticated operations."""
    reg = await unit_client.post(
        "/api/v1/auth/register",
        json={
            "email": "cacheunit@example.com",
            "username": "cacheunit",
            "password": "StrongPassword123!",
        },
    )
    assert reg.status_code == 201

    login = await unit_client.post(
        "/api/v1/auth/login",
        data={"username": "cacheunit", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_catalog_get_falls_back_to_db_on_redis_outage(
    unit_client: AsyncClient,
    unit_auth_headers: dict[str, str],
):
    """Verify GET /api/v1/titles returns HTTP 200 from PostgreSQL when Redis fails."""
    # Create title in DB
    create_res = await unit_client.post(
        "/api/v1/titles",
        json={
            "name": "Outage Test",
            "description": "Works during Redis downtime",
            "content_type": "movie",
            "release_year": 2024,
            "genre": "Drama",
            "platform": "Netflix",
        },
        headers=unit_auth_headers,
    )
    assert create_res.status_code == 201

    # Simulate Redis being completely down
    with patch("src.core.cache.redis_get", new=AsyncMock(return_value=None)):
        with patch("src.core.cache.redis_set", new=AsyncMock(return_value=False)):
            res = await unit_client.get("/api/v1/titles?search=Outage")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["name"] == "Outage Test"


@pytest.mark.anyio
async def test_title_write_succeeds_even_if_redis_invalidation_fails(
    unit_client: AsyncClient,
    unit_auth_headers: dict[str, str],
):
    """Verify database write commits and succeeds (HTTP 201/200/204) even if Redis is down."""
    with patch("src.services.cache_service.invalidate_catalog", new=AsyncMock(return_value=False)):
        # POST succeeds
        post_res = await unit_client.post(
            "/api/v1/titles",
            json={
                "name": "Resilient Movie",
                "description": "Committed despite Redis outage",
                "content_type": "movie",
                "release_year": 2023,
                "genre": "Action",
                "platform": "Prime",
            },
            headers=unit_auth_headers,
        )
        assert post_res.status_code == 201
        title_id = post_res.json()["id"]

        # PATCH succeeds
        patch_res = await unit_client.patch(
            f"/api/v1/titles/{title_id}",
            json={"name": "Resilient Movie Updated"},
            headers=unit_auth_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["name"] == "Resilient Movie Updated"

        # DELETE succeeds
        del_res = await unit_client.delete(
            f"/api/v1/titles/{title_id}",
            headers=unit_auth_headers,
        )
        assert del_res.status_code == 204


@pytest.mark.anyio
async def test_failed_db_write_does_not_call_invalidation(
    unit_client: AsyncClient,
    unit_auth_headers: dict[str, str],
):
    """Verify that if a database transaction fails, cache invalidation is NOT called."""
    with patch("src.services.cache_service.invalidate_catalog") as mock_inval:
        # Invalid payload (e.g. invalid content_type) rejected before/during DB transaction
        bad_res = await unit_client.post(
            "/api/v1/titles",
            json={
                "name": "Bad Payload",
                "content_type": "invalid_type",
                "release_year": 2024,
                "genre": "Action",
                "platform": "Netflix",
            },
            headers=unit_auth_headers,
        )
        assert bad_res.status_code == 422
        mock_inval.assert_not_called()
