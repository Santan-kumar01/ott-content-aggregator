import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from src.main import app


@pytest.fixture
def mock_database():
    """Mock database connection for isolated health probe tests."""
    mock_connection = AsyncMock()
    mock_connection.execute = AsyncMock(return_value=None)

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(
        return_value=mock_connection
    )
    mock_engine.connect.return_value.__aexit__ = AsyncMock(
        return_value=False
    )

    return mock_engine, mock_connection


@pytest.fixture
async def health_client():
    """Create an isolated HTTP client without running application lifespan."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.anyio
async def test_liveness_returns_alive_without_dependency_checks(
    health_client: AsyncClient,
):
    mock_engine = MagicMock()
    redis_check = AsyncMock()

    with (
        patch("src.main.engine", mock_engine),
        patch("src.main.check_redis_health", new=redis_check),
    ):
        response = await health_client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    mock_engine.connect.assert_not_called()
    redis_check.assert_not_called()


@pytest.mark.anyio
async def test_readiness_returns_200_when_all_dependencies_connected(
    health_client: AsyncClient,
    mock_database,
):
    mock_engine, _ = mock_database

    with (
        patch("src.main.engine", mock_engine),
        patch(
            "src.main.check_redis_health",
            new=AsyncMock(return_value="connected"),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
        "redis": "connected",
    }


@pytest.mark.anyio
async def test_readiness_returns_503_when_database_is_disconnected(
    health_client: AsyncClient,
    mock_database,
):
    mock_engine, mock_connection = mock_database
    mock_connection.execute.side_effect = RuntimeError(
        "Database connection failed"
    )

    with (
        patch("src.main.engine", mock_engine),
        patch(
            "src.main.check_redis_health",
            new=AsyncMock(return_value="connected"),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "disconnected",
        "redis": "connected",
    }


@pytest.mark.anyio
async def test_readiness_returns_503_when_redis_is_disconnected(
    health_client: AsyncClient,
    mock_database,
):
    mock_engine, _ = mock_database

    with (
        patch("src.main.engine", mock_engine),
        patch(
            "src.main.check_redis_health",
            new=AsyncMock(return_value="disconnected"),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "connected",
        "redis": "disconnected",
    }


@pytest.mark.anyio
async def test_readiness_returns_503_when_both_dependencies_fail(
    health_client: AsyncClient,
    mock_database,
):
    mock_engine, mock_connection = mock_database
    mock_connection.execute.side_effect = RuntimeError(
        "Database connection failed"
    )

    with (
        patch("src.main.engine", mock_engine),
        patch(
            "src.main.check_redis_health",
            new=AsyncMock(return_value="disconnected"),
        ),
    ):
        response = await health_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "disconnected",
        "redis": "disconnected",
    }


@pytest.mark.anyio
async def test_readiness_status_matches_response_body(
    health_client: AsyncClient,
    mock_database,
):
    mock_engine, _ = mock_database

    with (
        patch("src.main.engine", mock_engine),
        patch(
            "src.main.check_redis_health",
            new=AsyncMock(return_value="connected"),
        ),
    ):
        response = await health_client.get("/health/ready")

    data = response.json()

    assert (response.status_code == 200) == (
        data["status"] == "ready"
    )
