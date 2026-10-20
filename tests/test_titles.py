
from unittest.mock import AsyncMock, MagicMock

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
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


@pytest.mark.anyio
async def test_health_endpoint_returns_503_when_database_fails(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from src import main

    mock_connection = MagicMock()
    mock_connection.execute = AsyncMock(
        side_effect=RuntimeError("Database connection failed")
    )

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(
        return_value=mock_connection
    )
    mock_engine.connect.return_value.__aexit__ = AsyncMock(
        return_value=False
    )

    monkeypatch.setattr(main, "engine", mock_engine)

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "unhealthy",
            "database": "disconnected",
        }
    }


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


@pytest.mark.anyio
async def test_paginated_titles_empty_result(client: AsyncClient):
    response = await client.get("/api/v1/titles/paginated")

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 20
    assert data["has_next"] is False


@pytest.mark.anyio
async def test_paginated_titles_returns_total_and_has_next(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    titles = [
        {
            "name": f"Pagination Movie {i}",
            "description": "Pagination test",
            "content_type": "movie",
            "release_year": 2020 + i,
            "genre": "Drama",
            "platform": "Netflix",
        }
        for i in range(3)
    ]

    for title in titles:
        response = await client.post(
            "/api/v1/titles",
            json=title,
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated?skip=0&limit=2"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["skip"] == 0
    assert data["limit"] == 2
    assert data["has_next"] is True


@pytest.mark.anyio
async def test_paginated_titles_last_page_has_no_next(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    for i in range(2):
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": f"Last Page Movie {i}",
                "description": "Last page test",
                "content_type": "movie",
                "release_year": 2020,
                "genre": "Drama",
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated?skip=1&limit=1"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["has_next"] is False


@pytest.mark.anyio
async def test_paginated_titles_filters_by_genre(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    for name, genre in [
        ("Drama Movie", "Drama"),
        ("Comedy Movie", "Comedy"),
    ]:
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": name,
                "description": "Genre filter test",
                "content_type": "movie",
                "release_year": 2024,
                "genre": genre,
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated?genre=Drama"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["genre"] == "Drama"


@pytest.mark.anyio
async def test_paginated_titles_invalid_pagination_parameters(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/titles/paginated?skip=-1"
    )
    assert response.status_code == 422

    response = await client.get(
        "/api/v1/titles/paginated?limit=0"
    )
    assert response.status_code == 422

    response = await client.get(
        "/api/v1/titles/paginated?limit=101"
    )
    assert response.status_code == 422
