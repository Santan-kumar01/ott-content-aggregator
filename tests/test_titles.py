
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.database import Base, get_db
from src.main import app


@pytest.fixture
async def client():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
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
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a test user and return a valid access token."""
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "validation@example.com",
            "username": "validationuser",
            "password": "StrongPassword123!",
        },
    )
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "validation@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"


@pytest.mark.anyio
async def test_create_title_invalid_year(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "name": "Test Movie",
        "description": "Testing invalid year",
        "content_type": "movie",
        "release_year": 1700,
        "genre": "Drama",
        "platform": "Netflix",
    }

    response = await client.post(
        "/api/v1/titles",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.anyio
async def test_create_title_invalid_content_type(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "name": "Test Documentary",
        "description": "Testing invalid content type",
        "content_type": "documentary",
        "release_year": 2020,
        "genre": "Documentary",
        "platform": "Netflix",
    }

    response = await client.post(
        "/api/v1/titles",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.anyio
async def test_unknown_title_returns_404(client: AsyncClient):
    response = await client.get("/api/v1/titles/999999")

    assert response.status_code == 404
