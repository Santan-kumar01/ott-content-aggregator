import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.cache import check_redis_health, get_redis_client, redis_delete, redis_get
from src.core.database import Base, get_db
from src.main import app
from src.models.title import Title
from src.services.cache_service import (
    CATALOG_GENERATION_KEY,
    build_catalog_params_hash,
    get_catalog_generation,
)


@pytest.fixture
async def live_redis_check():
    """Verify live Redis instance is available before running integration tests."""
    status = await check_redis_health()
    if status != "connected":
        pytest.skip("Live Redis service on localhost:6379 is not reachable")
    yield


@pytest.fixture
async def redis_integration_client(live_redis_check):
    """Create test client with isolated SQLite database and real Redis cache."""
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

    # Clean up test generation and keys
    client = get_redis_client()
    if client:
        await client.incr(CATALOG_GENERATION_KEY)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as test_client:
            yield test_client, session_factory
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.fixture
async def redis_auth_headers(redis_integration_client) -> dict[str, str]:
    """Register and authenticate user for write operations in integration tests."""
    client, _ = redis_integration_client
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "redistester@example.com",
            "username": "redistester",
            "password": "StrongPassword123!",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "redistester", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ===========================================================================
# LIVE REDIS INTEGRATION TESTS
# ===========================================================================


@pytest.mark.anyio
async def test_real_redis_connectivity(live_redis_check):
    """Verify live Redis client can connect and ping."""
    client = get_redis_client()
    assert client is not None
    pong = await client.ping()
    assert pong is True


@pytest.mark.anyio
async def test_real_redis_ttl_expiration(live_redis_check):
    """Verify keys in real Redis expire naturally based on configured TTL."""
    client = get_redis_client()
    test_key = "test:ttl_expiration_key"
    await client.set(test_key, "expiring_payload", ex=1)

    # Check key exists and has TTL <= 1
    ttl = await client.ttl(test_key)
    assert 0 < ttl <= 1
    val = await client.get(test_key)
    assert val == "expiring_payload"

    # Wait for TTL expiration
    await asyncio.sleep(1.2)
    expired_val = await client.get(test_key)
    assert expired_val is None


@pytest.mark.anyio
async def test_real_redis_catalog_cache_hit_and_miss(
    redis_integration_client,
    redis_auth_headers: dict[str, str],
):
    """Verify real Redis stores cached response on miss and serves it on subsequent hit."""
    client, session_factory = redis_integration_client

    # 1. Create a title in database via API
    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Interstellar",
            "description": "Space exploration epic",
            "content_type": "movie",
            "release_year": 2014,
            "genre": "Sci-Fi",
            "platform": "Prime",
        },
        headers=redis_auth_headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    # 2. First GET request (Cache Miss -> DB query -> Cache Populated in Redis)
    gen = await get_catalog_generation()
    assert gen is not None
    res1 = await client.get("/api/v1/titles?search=Interstellar")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) == 1
    assert data1[0]["name"] == "Interstellar"

    # Verify key was written into real Redis
    param_hash = build_catalog_params_hash(search="Interstellar")
    expected_key = f"catalog:v{gen}:list:{param_hash}"
    cached_raw = await redis_get(expected_key)
    assert cached_raw is not None
    cached_json = json.loads(cached_raw)
    assert len(cached_json) == 1
    assert cached_json[0]["name"] == "Interstellar"

    # 3. Direct DB update without API (bypasses cache invalidation to PROVE cache hit)
    async with session_factory() as session:
        await session.execute(
            update(Title)
            .where(Title.id == title_id)
            .values(name="Secretly Modified in DB")
        )
        await session.commit()

    # 4. Second GET request (MUST BE A CACHE HIT returning 'Interstellar' from Redis!)
    res2 = await client.get("/api/v1/titles?search=Interstellar")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2) == 1
    # If it was a cache miss, it would return "Secretly Modified in DB".
    # Because it is a verified cache hit, it returns "Interstellar"!
    assert data2[0]["name"] == "Interstellar"


@pytest.mark.anyio
async def test_real_redis_paginated_caching_metadata(
    redis_integration_client,
    redis_auth_headers: dict[str, str],
):
    """Verify paginated responses preserve all metadata fields in real Redis cache."""
    client, _ = redis_integration_client

    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Dune Part Two",
            "description": "Arrakis destiny",
            "content_type": "movie",
            "release_year": 2024,
            "genre": "Sci-Fi",
            "platform": "Max",
        },
        headers=redis_auth_headers,
    )
    assert create_res.status_code == 201

    res = await client.get("/api/v1/titles/paginated?search=Dune&skip=0&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert "has_next" in data
    assert data["total"] == 1
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert data["has_next"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Dune Part Two"


@pytest.mark.anyio
async def test_real_redis_invalidation_on_create_patch_delete(
    redis_integration_client,
    redis_auth_headers: dict[str, str],
):
    """Verify live Redis invalidation increments generation on create, PATCH, and delete."""
    client, _ = redis_integration_client

    # 1. Warm cache with initial listing
    res_init = await client.get("/api/v1/titles")
    assert res_init.status_code == 200
    gen_before = await get_catalog_generation()

    # 2. CREATE title -> verify generation increments
    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Oppenheimer",
            "description": "Atomic bomb drama",
            "content_type": "movie",
            "release_year": 2023,
            "genre": "Biography",
            "platform": "Peacock",
        },
        headers=redis_auth_headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    gen_after_create = await get_catalog_generation()
    assert gen_after_create > gen_before

    # Check listing immediately reflects Oppenheimer
    res_list = await client.get("/api/v1/titles?search=Oppenheimer")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 3. PATCH title -> verify generation increments
    patch_res = await client.patch(
        f"/api/v1/titles/{title_id}",
        json={"name": "Oppenheimer IMAX Edition"},
        headers=redis_auth_headers,
    )
    assert patch_res.status_code == 200
    gen_after_patch = await get_catalog_generation()
    assert gen_after_patch > gen_after_create

    # Check single title endpoint reflects update
    get_res = await client.get(f"/api/v1/titles/{title_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Oppenheimer IMAX Edition"

    # 4. DELETE title -> verify generation increments and title is gone
    del_res = await client.delete(
        f"/api/v1/titles/{title_id}",
        headers=redis_auth_headers,
    )
    assert del_res.status_code == 204
    gen_after_delete = await get_catalog_generation()
    assert gen_after_delete > gen_after_patch

    # Check listing no longer contains title
    res_after_del = await client.get("/api/v1/titles?search=Oppenheimer")
    assert res_after_del.status_code == 200
    assert len(res_after_del.json()) == 0

    # Check GET /titles/{id} returns 404
    get_404 = await client.get(f"/api/v1/titles/{title_id}")
    assert get_404.status_code == 404
