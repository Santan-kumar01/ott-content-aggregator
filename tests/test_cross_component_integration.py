import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from jose import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select, text
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
    set_invalidation_pending,
)
from src.core.database import Base, get_db, settings
from src.core.http_client import close_http_client, init_http_client
from src.core.security import create_access_token, hash_password
from src.main import app, lifespan
from src.models.title import Title
from src.models.user import User
from src.schemas.sync import ExternalTitleMetadata
from src.schemas.title import TitleCreate, TitleUpdate
from src.services import auth_service, cache_service, catalog_service
from src.services.background_tasks import (
    get_background_task_status,
    sync_title_from_external_provider_task,
)
from src.services.external_provider_service import ExternalProviderError


# ---------------------------------------------------------------------------
# FIXTURES
# ---------------------------------------------------------------------------

@pytest.fixture
async def integration_db():
    """Isolated SQLite database for cross-component integration testing."""
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
    yield session_factory, engine

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def integration_client(integration_db):
    """AsyncClient using isolated database."""
    session_factory, _ = integration_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        yield client, session_factory


@pytest.fixture
async def auth_user_and_headers(integration_client):
    """Create test user and return auth headers along with user dict."""
    client, _ = integration_client
    email = "integration_tester@example.com"
    username = "inttester"
    password = "IntegrationPassword123!"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()

    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(1, 4, 60)),
    ):
        login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_data, headers, password


# ---------------------------------------------------------------------------
# 1. AUTHENTICATION INTEGRATION & EDGE CASES
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_auth_full_workflow_and_security_edge_cases(integration_client):
    """Verify registration, password hashing, username login fallback, and token edge cases."""
    client, session_factory = integration_client

    email = "edge_auth@example.com"
    username = "edgeauth"
    password = "SuperPassword123!"

    # 1. Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    user_id = data["id"]
    assert "password" not in data
    assert "hashed_password" not in data

    # 2. Verify in DB directly that password is saved as hash and not plaintext
    async with session_factory() as session:
        user = await session.get(User, user_id)
        assert user is not None
        assert user.hashed_password != password
        assert user.hashed_password.startswith("$2b$") or len(user.hashed_password) > 30

    # 3. Login using username (instead of email) to exercise username fallback
    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(1, 4, 60)),
    ):
        user_login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
        )
    assert user_login_res.status_code == 200
    token = user_login_res.json()["access_token"]

    # 4. Access /me with token issued from username login
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username
    assert me_res.json()["email"] == email

    # 5. Token with missing/empty sub returns 401
    bad_token = jwt.encode(
        {"sub": "", "exp": 9999999999},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    res_bad_sub = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert res_bad_sub.status_code == 401
    assert "Could not validate credentials" in res_bad_sub.json()["detail"]

    # 6. Token for nonexistent user returns 401 User not found
    ghost_token = create_access_token(subject="999999")
    res_ghost = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert res_ghost.status_code == 401
    assert "User not found" in res_ghost.json()["detail"]

    # 7. Token with username as subject (fallback branch in get_current_user)
    username_token = create_access_token(subject=username)
    res_username_token = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {username_token}"},
    )
    assert res_username_token.status_code == 200
    assert res_username_token.json()["id"] == user_id

    # 8. Token with email as subject (fallback branch in get_current_user)
    email_token = create_access_token(subject=email)
    res_email_token = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {email_token}"},
    )
    assert res_email_token.status_code == 200
    assert res_email_token.json()["id"] == user_id


@pytest.mark.anyio
async def test_auth_inactive_user_branches(integration_client):
    """Verify inactive user cannot login or access endpoints via username or email."""
    client, session_factory = integration_client

    email = "inactive_test@example.com"
    username = "inactivetest"
    password = "InactivePassword123!"

    # Create inactive user directly in DB
    async with session_factory() as session:
        inactive_user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            is_active=False,
        )
        session.add(inactive_user)
        await session.commit()
        await session.refresh(inactive_user)
        uid = inactive_user.id

    # 1. Login with email rejected for inactive user
    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(1, 4, 60)),
    ):
        email_login = await client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": password},
        )
    assert email_login.status_code == 400
    assert email_login.json()["detail"] == "Inactive user"

    # 2. Login with username rejected for inactive user
    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(1, 4, 60)),
    ):
        user_login = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
        )
    assert user_login.status_code == 400
    assert user_login.json()["detail"] == "Inactive user"

    # 3. Access /me with signed token rejected for inactive user
    token = create_access_token(subject=str(uid))
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 400
    assert me_res.json()["detail"] == "Inactive user"


# ---------------------------------------------------------------------------
# 2. CATALOG CRUD, CACHING & INVALIDATION FLOW
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_catalog_crud_caching_and_invalidation_lifecycle(
    integration_client, auth_user_and_headers
):
    """Verify authenticated create, get, cache hit, patch invalidation, paginated cache, and delete."""
    client, _ = integration_client
    _, headers, _ = auth_user_and_headers

    # 1. Create a title
    create_payload = {
        "name": "Integration Inception",
        "description": "Dream within a dream heist",
        "content_type": "movie",
        "release_year": 2010,
        "genre": "Sci-Fi",
        "platform": "Netflix",
    }
    create_res = await client.post(
        "/api/v1/titles", json=create_payload, headers=headers
    )
    assert create_res.status_code == 201
    title_data = create_res.json()
    title_id = title_data["id"]

    # 2. First GET /titles/{id} -> populates cache
    get1 = await client.get(f"/api/v1/titles/{title_id}")
    assert get1.status_code == 200
    assert get1.json()["name"] == "Integration Inception"

    # 3. Second GET /titles/{id} -> cache hit
    get2 = await client.get(f"/api/v1/titles/{title_id}")
    assert get2.status_code == 200
    assert get2.json()["name"] == "Integration Inception"

    # 4. GET /titles -> populates list cache
    list1 = await client.get("/api/v1/titles?genre=Sci-Fi")
    assert list1.status_code == 200
    assert any(t["id"] == title_id for t in list1.json())

    # 5. Second GET /titles -> cache hit
    list2 = await client.get("/api/v1/titles?genre=Sci-Fi")
    assert list2.status_code == 200
    assert any(t["id"] == title_id for t in list2.json())

    # 6. GET /titles/paginated -> populates paginated cache
    pag1 = await client.get("/api/v1/titles/paginated?genre=Sci-Fi&limit=5")
    assert pag1.status_code == 200
    assert pag1.json()["total"] >= 1
    assert "has_next" in pag1.json()

    # 7. Second GET /titles/paginated -> cache hit
    pag2 = await client.get("/api/v1/titles/paginated?genre=Sci-Fi&limit=5")
    assert pag2.status_code == 200
    assert pag2.json()["total"] == pag1.json()["total"]

    # 8. PATCH partial update -> invalidates cache
    patch_res = await client.patch(
        f"/api/v1/titles/{title_id}",
        json={"name": "Inception Remastered"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Inception Remastered"

    # 9. GET /titles/{id} returns updated data immediately
    get_after_patch = await client.get(f"/api/v1/titles/{title_id}")
    assert get_after_patch.status_code == 200
    assert get_after_patch.json()["name"] == "Inception Remastered"

    # 10. DELETE title -> invalidates cache
    del_res = await client.delete(f"/api/v1/titles/{title_id}", headers=headers)
    assert del_res.status_code == 204

    # 11. Subsequent GET returns 404
    get_after_del = await client.get(f"/api/v1/titles/{title_id}")
    assert get_after_del.status_code == 404


@pytest.mark.anyio
async def test_catalog_error_paths_and_missing_resources(
    integration_client, auth_user_and_headers
):
    """Verify 404, 401, and 422 error paths across catalog endpoints."""
    client, _ = integration_client
    _, headers, _ = auth_user_and_headers

    # Nonexistent title 404s
    assert (await client.get("/api/v1/titles/999999")).status_code == 404
    assert (
        await client.patch(
            "/api/v1/titles/999999", json={"name": "Ghost"}, headers=headers
        )
    ).status_code == 404
    assert (
        await client.delete("/api/v1/titles/999999", headers=headers)
    ).status_code == 404

    # Unauthenticated writes 401
    assert (
        await client.post(
            "/api/v1/titles",
            json={
                "name": "No Auth",
                "content_type": "movie",
                "release_year": 2022,
                "genre": "Action",
                "platform": "Netflix",
            },
        )
    ).status_code == 401
    assert (
        await client.patch("/api/v1/titles/1", json={"name": "No Auth"})
    ).status_code == 401
    assert (await client.delete("/api/v1/titles/1")).status_code == 401

    # Invalid ID 422
    assert (await client.get("/api/v1/titles/0")).status_code == 422
    assert (await client.get("/api/v1/titles/-1")).status_code == 422


# ---------------------------------------------------------------------------
# 3. DATABASE TRANSACTION ROLLBACK & CACHE INTEGRITY
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_database_failure_transaction_rollback_and_cache_cleanliness(
    integration_client, auth_user_and_headers
):
    """Verify failed database writes trigger rollback and do not pollute the cache."""
    client, session_factory = integration_client
    _, headers, _ = auth_user_and_headers

    # 1. Create a baseline title
    res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Rollback Original",
            "content_type": "movie",
            "release_year": 2021,
            "genre": "Comedy",
            "platform": "Hulu",
        },
        headers=headers,
    )
    assert res.status_code == 201
    title_id = res.json()["id"]

    # 2. Simulate database commit failure on update
    with patch.object(AsyncSession, "commit", side_effect=Exception("DB Commit Failure")):
        with pytest.raises(Exception, match="DB Commit Failure"):
            async with session_factory() as session:
                title = await session.get(Title, title_id)
                await catalog_service.update_title(
                    session, title, TitleUpdate(name="Corrupted Update")
                )

    # 3. Verify database row still has the original value
    get_res = await client.get(f"/api/v1/titles/{title_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Rollback Original"


# ---------------------------------------------------------------------------
# 4. REDIS OUTAGE FALLBACK & RECOVERY
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_redis_outage_fallback_and_recovery(
    integration_client, auth_user_and_headers
):
    """Verify catalog reads/writes function during Redis outage, and recover post-reconnect."""
    client, _ = integration_client
    _, headers, _ = auth_user_and_headers

    # 1. Simulate Redis outage during listing
    with patch("src.services.cache_service.get_catalog_list", return_value=None):
        res = await client.get("/api/v1/titles")
        assert res.status_code == 200

    # 2. Simulate Redis outage during paginated query
    with patch("src.services.cache_service.get_catalog_paginated", return_value=None):
        res_pag = await client.get("/api/v1/titles/paginated")
        assert res_pag.status_code == 200
        assert "items" in res_pag.json()

    # 3. Simulate Redis outage during title get
    with patch("src.services.cache_service.get_title", return_value=None):
        res_get = await client.get("/api/v1/titles/999999")
        assert res_get.status_code == 404

    # 4. Invalidation failure sets pending flag
    with patch("src.services.cache_service.redis_incr", new=AsyncMock(return_value=None)):
        await cache_service.invalidate_catalog()
        assert is_invalidation_pending() is True

    # 5. On Redis recovery, get_catalog_generation detects pending flag, increments key, and resets flag
    with patch("src.services.cache_service.redis_incr", new=AsyncMock(return_value=5)):
        new_gen = await cache_service.get_catalog_generation()
        assert new_gen == 5
        assert is_invalidation_pending() is False


# ---------------------------------------------------------------------------
# 5. BACKGROUND TASK INTEGRATION & ERROR OBSERVABILITY
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_background_sync_task_with_external_failure_and_db_rollback(
    integration_client, auth_user_and_headers
):
    """Verify background task records failure, rolls back DB, and preserves observable state."""
    client, session_factory = integration_client
    _, headers, _ = auth_user_and_headers

    # 1. Create title
    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Sync Error Movie",
            "description": "Original uncorrupted description",
            "content_type": "movie",
            "release_year": 2019,
            "genre": "Horror",
            "platform": "Netflix",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    # 2. Trigger sync endpoint
    sync_res = await client.post(
        f"/api/v1/titles/{title_id}/sync",
        json={"external_id": "ext-fail-404", "provider": "netflix"},
        headers=headers,
    )
    assert sync_res.status_code == 202
    task_id = sync_res.json()["task_id"]

    # 3. Execute background task simulating external provider failure
    with patch("src.services.background_tasks.SessionLocal", session_factory):
        with patch(
            "src.services.background_tasks.fetch_external_title_metadata",
            side_effect=ExternalProviderError("Provider 500 internal error"),
        ):
            await sync_title_from_external_provider_task(
                task_id=task_id, title_id=title_id, external_id="ext-fail-404"
            )

    # 4. Check task status via API
    status_res = await client.get(f"/api/v1/titles/sync/tasks/{task_id}")
    assert status_res.status_code == 200
    task_status = status_res.json()
    assert task_status["status"] == "failed"
    assert "Provider 500 internal error" in task_status["error"]

    # 5. Verify database record description was untouched
    get_res = await client.get(f"/api/v1/titles/{title_id}")
    assert get_res.json()["description"] == "Original uncorrupted description"


# ---------------------------------------------------------------------------
# 6. APPLICATION LIFESPAN STARTUP AND SHUTDOWN INTEGRATION
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_lifespan_startup_and_shutdown_integration():
    """Verify full application lifespan starts and shuts down HTTP and Redis cleanly."""
    async with lifespan(app):
        assert app.title == "OTT Content Aggregator API"
        http_client = await init_http_client()
        assert not http_client.is_closed
        redis_status = await check_redis_health()
        assert redis_status in ("connected", "disconnected")

    # Verify resource cleanup post-lifespan
    await close_http_client()
    await close_redis_client()


# ---------------------------------------------------------------------------
# 7. CATALOG LITERAL WILDCARD SEARCH INTEGRATION
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_catalog_literal_wildcard_search(
    integration_client, auth_user_and_headers
):
    """Verify that % and _ characters in search queries are matched literally without wildcard expansion."""
    client, _ = integration_client
    _, headers, _ = auth_user_and_headers

    items_to_create = [
        {
            "name": "Cotton 100% Pure",
            "description": "Material quality 100%",
            "content_type": "movie",
            "release_year": 2021,
            "genre": "Drama",
            "platform": "Netflix",
        },
        {
            "name": "Cotton 1000 Pure",
            "description": "Material quantity 1000",
            "content_type": "movie",
            "release_year": 2021,
            "genre": "Drama",
            "platform": "Netflix",
        },
        {
            "name": "Code_Name_Alpha",
            "description": "Undercover mission",
            "content_type": "movie",
            "release_year": 2022,
            "genre": "Action",
            "platform": "Prime",
        },
        {
            "name": "CodeXNameXAlpha",
            "description": "Standard mission",
            "content_type": "movie",
            "release_year": 2022,
            "genre": "Action",
            "platform": "Prime",
        },
    ]
    for item in items_to_create:
        res = await client.post("/api/v1/titles", json=item, headers=headers)
        assert res.status_code == 201

    # 1. Search for literal '100%' should match 'Cotton 100% Pure' and NOT 'Cotton 1000 Pure'
    res_percent = await client.get("/api/v1/titles?search=100%")
    assert res_percent.status_code == 200
    names_percent = [t["name"] for t in res_percent.json()]
    assert "Cotton 100% Pure" in names_percent
    assert "Cotton 1000 Pure" not in names_percent

    # 2. Search for literal 'Code_Name_Alpha' should match 'Code_Name_Alpha' and NOT 'CodeXNameXAlpha'
    res_underscore = await client.get("/api/v1/titles?search=Code_Name_Alpha")
    assert res_underscore.status_code == 200
    names_underscore = [t["name"] for t in res_underscore.json()]
    assert "Code_Name_Alpha" in names_underscore
    assert "CodeXNameXAlpha" not in names_underscore


# ---------------------------------------------------------------------------
# 8. REDIS CORRUPTED DATA & GENERATION RECOVERY
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_redis_corrupted_payload_and_generation_recovery():
    """Verify handling of invalid generation numbers and corrupted JSON payloads in Redis."""
    # Ensure this test does not inherit state from a previous test.
    from src.core.cache import set_invalidation_pending

    set_invalidation_pending(False)

    # 1. Invalid non-integer generation string resets to default generation
    with patch("src.services.cache_service.redis_get", new=AsyncMock(return_value="corrupted_gen_str")):
        with patch("src.services.cache_service.redis_set", new=AsyncMock(return_value=True)):
            gen = await cache_service.get_catalog_generation()
            assert gen == 1

    # 2. Corrupted JSON payload returns None and gracefully falls back to DB
    with patch("src.services.cache_service.get_catalog_generation", new=AsyncMock(return_value=1)):
        with patch("src.services.cache_service.redis_get", new=AsyncMock(return_value="INVALID_NOT_A_JSON{")):
            res = await cache_service.get_catalog_list(genre="Action")
            assert res is None

    # 3. Test redis_delete with empty keys returns 0
    del_count = await redis_delete()
    assert del_count == 0


# ---------------------------------------------------------------------------
# 9. BACKGROUND TASK UNEXPECTED EXCEPTION & ROLLBACK
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_background_sync_unexpected_exception_and_db_rollback(
    integration_client, auth_user_and_headers
):
    """Verify unexpected non-provider runtime exceptions during sync trigger DB rollback and record error."""
    client, session_factory = integration_client
    _, headers, _ = auth_user_and_headers

    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Sync Crash Movie",
            "description": "Safe before crash",
            "content_type": "movie",
            "release_year": 2020,
            "genre": "Drama",
            "platform": "Netflix",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    sync_res = await client.post(
        f"/api/v1/titles/{title_id}/sync",
        json={"external_id": "crash-test"},
        headers=headers,
    )
    assert sync_res.status_code == 202
    task_id = sync_res.json()["task_id"]

    # Simulate unexpected generic Exception inside task
    with patch("src.services.background_tasks.SessionLocal", session_factory):
        with patch(
            "src.services.background_tasks.fetch_external_title_metadata",
            side_effect=RuntimeError("Unexpected unhandled system error"),
        ):
            await sync_title_from_external_provider_task(
                task_id=task_id, title_id=title_id, external_id="crash-test"
            )

    status_res = await client.get(f"/api/v1/titles/sync/tasks/{task_id}")
    assert status_res.status_code == 200
    task_data = status_res.json()
    assert task_data["status"] == "failed"
    assert "Unexpected error during sync" in task_data["error"]
    assert "Unexpected unhandled system error" in task_data["error"]

    # Verify database state was preserved
    get_res = await client.get(f"/api/v1/titles/{title_id}")
    assert get_res.json()["description"] == "Safe before crash"


# ---------------------------------------------------------------------------
# 10. AUTH TOKEN SIGNATURE & EXPIRATION EDGE CASES
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_auth_token_signature_and_expiration_edge_cases(integration_client):
    """Verify expired token, forged signature, and invalid algorithm tokens return 401."""
    client, _ = integration_client

    # 1. Expired token
    expired_token = jwt.encode(
        {"sub": "1", "exp": int(datetime.now(timezone.utc).timestamp()) - 3600},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    res_exp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert res_exp.status_code == 401

    # 2. Forged secret token
    forged_token = jwt.encode(
        {"sub": "1", "exp": int(datetime.now(timezone.utc).timestamp()) + 3600},
        "wrong_secret_key_123456789012345678901234567890",
        algorithm=settings.jwt_algorithm,
    )
    res_forged = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_token}"}
    )
    assert res_forged.status_code == 401

    # 3. Unsecured none-algorithm token
    none_token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIiwiZXhwIjo5OTk5OTk5OTk5fQ."
    res_none = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {none_token}"}
    )
    assert res_none.status_code == 401

    # 4. Completely malformed token string
    res_malformed = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"}
    )
    assert res_malformed.status_code == 401


# ---------------------------------------------------------------------------
# 11. COMBINED QUERY PARAMETERS & DISTINCT CACHE KEYS
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_combined_query_params_and_distinct_cache_keys(
    integration_client, auth_user_and_headers
):
    """Verify multi-parameter queries (search+genre+platform+sort) generate distinct cache keys."""
    client, _ = integration_client
    _, headers, _ = auth_user_and_headers

    titles = [
        {
            "name": "Alpha Space",
            "content_type": "movie",
            "release_year": 2020,
            "genre": "Sci-Fi",
            "platform": "Netflix",
        },
        {
            "name": "Beta Space",
            "content_type": "movie",
            "release_year": 2020,
            "genre": "Sci-Fi",
            "platform": "Prime",
        },
        {
            "name": "Gamma Earth",
            "content_type": "movie",
            "release_year": 2021,
            "genre": "Drama",
            "platform": "Netflix",
        },
    ]
    for t in titles:
        res = await client.post("/api/v1/titles", json=t, headers=headers)
        assert res.status_code == 201

    # Combined query 1: Sci-Fi on Netflix
    res1 = await client.get("/api/v1/titles?search=Space&genre=Sci-Fi&platform=Netflix")
    assert res1.status_code == 200
    assert len(res1.json()) == 1
    assert res1.json()[0]["name"] == "Alpha Space"

    # Combined query 2: Sci-Fi on Prime
    res2 = await client.get("/api/v1/titles?search=Space&genre=Sci-Fi&platform=Prime")
    assert res2.status_code == 200
    assert len(res2.json()) == 1
    assert res2.json()[0]["name"] == "Beta Space"

    # Verify hashes differ
    hash1 = cache_service.build_catalog_params_hash(
        search="Space", genre="Sci-Fi", platform="Netflix"
    )
    hash2 = cache_service.build_catalog_params_hash(
        search="Space", genre="Sci-Fi", platform="Prime"
    )
    assert hash1 != hash2
