from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base, get_db
from src.core.security import create_access_token, hash_password
from src.main import app
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

    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(1, 4, 60)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def session_factory():
    """Provide a direct session maker for creating pre-seeded test fixtures."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    yield factory
    await engine.dispose()


# ---------------------------------------------------------------------------
# Registration API Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_user_api_success(client: AsyncClient):
    payload = {
        "email": "alice@example.com",
        "username": "alice",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["username"] == "alice"
    assert data["is_active"] is True
    assert data["is_superuser"] is False
    assert "id" in data
    assert "created_at" in data

    # Verify hashed_password and plaintext password are never exposed
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.anyio
async def test_register_user_api_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "username": "user1",
        "password": "SecurePassword123!",
    }
    # Initial registration
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Duplicate registration
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Email already registered"


@pytest.mark.anyio
async def test_register_user_api_validation_errors(client: AsyncClient):
    # Invalid email
    res1 = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "username": "user", "password": "Password123!"},
    )
    assert res1.status_code == 422

    # Password too short
    res2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "username": "user", "password": "short"},
    )
    assert res2.status_code == 422


# ---------------------------------------------------------------------------
# Login API Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_login_api_success(client: AsyncClient):
    with patch("src.api.endpoints.auth.redis_incr_with_expiry_details", new=AsyncMock(return_value=(1, 4, 60))):
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "bob@example.com",
                "username": "bob",
                "password": "BobPassword123!",
            },
        )

        # Login using OAuth2 form data
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "bob@example.com", "password": "BobPassword123!"},
        )

        assert login_response.status_code == 200
        assert login_response.headers["RateLimit-Limit"] == "5"
        assert login_response.headers["RateLimit-Remaining"] == "4"
        assert login_response.headers["RateLimit-Reset"] == "60"
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert isinstance(token_data["access_token"], str)


@pytest.mark.anyio
async def test_login_api_invalid_password(client: AsyncClient):
    with patch("src.api.endpoints.auth.redis_incr_with_expiry_details", new=AsyncMock(return_value=(1, 4, 60))):
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "carol@example.com",
                "username": "carol",
                "password": "CarolPassword123!",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "carol@example.com", "password": "WrongPassword999!"},
        )

        assert login_response.status_code == 401
        assert login_response.headers["RateLimit-Limit"] == "5"
        assert login_response.headers["RateLimit-Remaining"] == "4"
        assert login_response.headers["RateLimit-Reset"] == "60"
        assert login_response.json()["detail"] == "Incorrect email or password"


@pytest.mark.anyio
async def test_login_api_unknown_email(client: AsyncClient):
    with patch("src.api.endpoints.auth.redis_incr_with_expiry_details", new=AsyncMock(return_value=(1, 4, 60))):
        login_response = await client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "AnyPassword123!"},
        )

        assert login_response.status_code == 401
        assert login_response.headers["RateLimit-Limit"] == "5"
        assert login_response.headers["RateLimit-Remaining"] == "4"
        assert login_response.headers["RateLimit-Reset"] == "60"
        assert login_response.json()["detail"] == "Incorrect email or password"


    # ---------------------------------------------------------------------------
    # /me Endpoint Tests
    # ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_me_valid_token(client: AsyncClient):
    # Register
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "dave@example.com",
            "username": "dave",
            "password": "DavePassword123!",
        },
    )
    user_id = reg_res.json()["id"]

    # Login to obtain token
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "dave@example.com", "password": "DavePassword123!"},
    )
    token = login_res.json()["access_token"]

    # Access /me with bearer token
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == "dave@example.com"
    assert me_data["username"] == "dave"
    assert me_data["is_active"] is True
    assert "hashed_password" not in me_data
    assert "password" not in me_data


@pytest.mark.anyio
async def test_get_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.or.tampered.token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.anyio
async def test_get_me_missing_token(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication token is missing"


@pytest.mark.anyio
async def test_inactive_user_rejected_on_login_and_me(client: AsyncClient):
    # Create engine and session to seed an inactive user
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with factory() as session:
        inactive_user = User(
            email="inactive@example.com",
            username="inactive",
            hashed_password=hash_password("Password123!"),
            is_active=False,
        )
        session.add(inactive_user)
        await session.commit()
        await session.refresh(inactive_user)
        inactive_user_id = inactive_user.id

    async def override_get_db_inactive():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db_inactive

    try:
        # Inactive user cannot login
        login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@example.com", "password": "Password123!"},
        )
        assert login_res.status_code == 400
        assert login_res.json()["detail"] == "Inactive user"

        # Inactive user cannot access /me even with validly signed token
        token = create_access_token(subject=str(inactive_user_id))
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 400
        assert me_res.json()["detail"] == "Inactive user"
    finally:
        await engine.dispose()



def test_authentication_error_responses_openapi_documentation():
    """Verify authentication endpoints document their error response schemas."""
    schema = app.openapi()
    paths = schema["paths"]

    expected_responses = {
        ("/api/v1/auth/register", "post"): ["400", "422"],
        ("/api/v1/auth/login", "post"): ["400", "401", "422"],
        ("/api/v1/auth/me", "get"): ["400", "401"],
    }

    for (path, method), status_codes in expected_responses.items():
        operation = paths[path][method]

        for status_code in status_codes:
            response = operation["responses"][status_code]
            response_schema = response["content"]["application/json"]["schema"]

            assert response_schema["$ref"] == (
                "#/components/schemas/ErrorResponse"
            ), f"{method.upper()} {path} response {status_code}"

@pytest.mark.anyio
async def test_login_api_rate_limit_exceeded(client: AsyncClient):
    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(6, 0, 45)),
    ) as mock_rate_limit:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "WrongPassword123!"},
        )

    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many login attempts. Please try again later."
    )
    assert response.headers["Retry-After"] == "45"
    assert response.headers["RateLimit-Limit"] == "5"
    assert response.headers["RateLimit-Remaining"] == "0"
    assert response.headers["RateLimit-Reset"] == "45"
    mock_rate_limit.assert_awaited_once()


@pytest.mark.anyio
async def test_login_api_returns_503_when_redis_unavailable(
    client: AsyncClient,
):
    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=None),
    ):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "AnyPassword123!"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Login service temporarily unavailable"
    assert response.headers["Retry-After"] == "60"
