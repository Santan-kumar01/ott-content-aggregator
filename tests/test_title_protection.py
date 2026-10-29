from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base, get_db
from src.core.security import create_access_token, hash_password
from src.main import app
from src.models.title import Title
from src.models.user import User


@pytest.fixture
async def client():
    """Create an async test client with an in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Helper fixture to register a test user and obtain a valid Authorization bearer header."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "creator@example.com",
            "username": "creator",
            "password": "StrongPassword123!",
        },
    )
    assert reg_res.status_code == 201

    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry",
        new=AsyncMock(return_value=1),
    ):
        login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": "creator@example.com", "password": "StrongPassword123!"},
        )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Public Read Endpoints Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_public_read_endpoints_accessible_without_auth(client: AsyncClient):
    # GET /api/v1/titles must be accessible without any Authorization header
    response = await client.get("/api/v1/titles")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # GET /api/v1/titles/{title_id} must be accessible without any Authorization header
    response_single = await client.get("/api/v1/titles/999")
    # Returns 404 (Not Found) rather than 401 (Unauthorized)
    assert response_single.status_code == 404
    assert response_single.json()["detail"] == "Title not found"


# ---------------------------------------------------------------------------
# Unauthenticated Write Endpoints Tests (Must Return HTTP 401)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_title_unauthenticated_rejected(client: AsyncClient):
    title_payload = {
        "name": "Inception",
        "content_type": "movie",
        "release_year": 2010,
        "genre": "Sci-Fi",
        "platform": "Netflix",
    }
    # No Authorization header
    res_no_auth = await client.post("/api/v1/titles", json=title_payload)
    assert res_no_auth.status_code == 401
    assert res_no_auth.json()["detail"] == "Authentication token is missing"

    # Invalid Authorization header
    res_bad_auth = await client.post(
        "/api/v1/titles",
        json=title_payload,
        headers={"Authorization": "Bearer invalid.token.signature"},
    )
    assert res_bad_auth.status_code == 401
    assert res_bad_auth.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_update_title_unauthenticated_rejected(client: AsyncClient):
    update_payload = {"name": "Updated Title Name"}

    # No Authorization header
    res_no_auth = await client.patch("/api/v1/titles/1", json=update_payload)
    assert res_no_auth.status_code == 401
    assert res_no_auth.json()["detail"] == "Authentication token is missing"

    # Invalid Authorization header
    res_bad_auth = await client.patch(
        "/api/v1/titles/1",
        json=update_payload,
        headers={"Authorization": "Bearer invalid.token.signature"},
    )
    assert res_bad_auth.status_code == 401
    assert res_bad_auth.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_delete_title_unauthenticated_rejected(client: AsyncClient):
    # No Authorization header
    res_no_auth = await client.delete("/api/v1/titles/1")
    assert res_no_auth.status_code == 401
    assert res_no_auth.json()["detail"] == "Authentication token is missing"

    # Invalid Authorization header
    res_bad_auth = await client.delete(
        "/api/v1/titles/1",
        headers={"Authorization": "Bearer invalid.token.signature"},
    )
    assert res_bad_auth.status_code == 401
    assert res_bad_auth.json()["detail"] == "Could not validate credentials"


# ---------------------------------------------------------------------------
# Authenticated Write Endpoints Tests (Must Succeed)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_authenticated_title_crud_lifecycle(
    client: AsyncClient, auth_headers: dict[str, str]
):
    # 1. CREATE title with authenticated credentials
    create_payload = {
        "name": "Interstellar",
        "description": "Exploration of a wormhole near Saturn",
        "content_type": "movie",
        "release_year": 2014,
        "genre": "Sci-Fi",
        "platform": "Paramount+",
    }
    create_res = await client.post(
        "/api/v1/titles",
        json=create_payload,
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "Interstellar"
    assert created_data["genre"] == "Sci-Fi"
    title_id = created_data["id"]

    # 2. Public READ of newly created title
    get_res = await client.get(f"/api/v1/titles/{title_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Interstellar"

    # 3. UPDATE title with authenticated credentials
    update_payload = {
        "name": "Interstellar (Updated Edition)",
        "genre": "Adventure",
    }
    update_res = await client.patch(
        f"/api/v1/titles/{title_id}",
        json=update_payload,
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Interstellar (Updated Edition)"
    assert updated_data["genre"] == "Adventure"
    assert updated_data["platform"] == "Paramount+"

    # 4. DELETE title with authenticated credentials
    delete_res = await client.delete(
        f"/api/v1/titles/{title_id}",
        headers=auth_headers,
    )
    assert delete_res.status_code == 204

    # 5. Confirm deletion via public read
    check_deleted = await client.get(f"/api/v1/titles/{title_id}")
    assert check_deleted.status_code == 404
