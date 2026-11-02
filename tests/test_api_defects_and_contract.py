from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base, get_db
from src.main import app
from src.models.title import Title
from src.schemas.title import TitleCreate, TitleUpdate
from src.schemas.user import UserCreate
from src.services import auth_service, catalog_service
from fastapi import HTTPException


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
            "email": "tester@example.com",
            "username": "tester",
            "password": "StrongPassword123!",
        },
    )
    assert reg_res.status_code == 201

    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry_details",
        new=AsyncMock(return_value=(1, 4, 60)),
    ):
        login_res = await client.post(
            "/api/v1/auth/login",
            data={"username": "tester@example.com", "password": "StrongPassword123!"},
        )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# HTTP Method Contract Tests (PATCH vs PUT)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_patch_partial_update_single_field(
    client: AsyncClient, auth_headers: dict[str, str]
):
    """Verify PATCH updates only the supplied fields and preserves all other fields."""
    # Create initial title
    create_payload = {
        "name": "The Matrix",
        "description": "A computer hacker learns about the true nature of reality",
        "content_type": "movie",
        "release_year": 1999,
        "genre": "Sci-Fi",
        "platform": "HBO Max",
    }
    create_res = await client.post(
        "/api/v1/titles",
        json=create_payload,
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    # PATCH only the platform field
    patch_res = await client.patch(
        f"/api/v1/titles/{title_id}",
        json={"platform": "Netflix"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()
    assert patched_data["platform"] == "Netflix"
    # Unchanged fields remain preserved
    assert patched_data["name"] == "The Matrix"
    assert patched_data["description"] == create_payload["description"]
    assert patched_data["release_year"] == 1999
    assert patched_data["genre"] == "Sci-Fi"
    assert patched_data["content_type"] == "movie"


@pytest.mark.anyio
async def test_put_method_returns_405_method_not_allowed(
    client: AsyncClient, auth_headers: dict[str, str]
):
    """Verify PUT is rejected with 405 Method Not Allowed in favor of standard PATCH."""
    put_res = await client.put(
        "/api/v1/titles/1",
        json={"name": "Replaced Name"},
        headers=auth_headers,
    )
    assert put_res.status_code == 405


@pytest.mark.anyio
async def test_patch_nonexistent_title_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
):
    """Verify PATCH on nonexistent title returns 404 Not Found."""
    patch_res = await client.patch(
        "/api/v1/titles/99999",
        json={"name": "Nonexistent"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 404
    assert patch_res.json()["detail"] == "Title not found"


@pytest.mark.anyio
async def test_patch_invalid_payload_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
):
    """Verify PATCH with invalid values returns 422 Unprocessable Entity."""
    # Create title first
    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Arrival",
            "content_type": "movie",
            "release_year": 2016,
            "genre": "Sci-Fi",
            "platform": "Hulu",
        },
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    # Invalid release year (< 1888)
    res_bad_year = await client.patch(
        f"/api/v1/titles/{title_id}",
        json={"release_year": 1800},
        headers=auth_headers,
    )
    assert res_bad_year.status_code == 422

    # Invalid content_type (not movie or show)
    res_bad_type = await client.patch(
        f"/api/v1/titles/{title_id}",
        json={"content_type": "documentary"},
        headers=auth_headers,
    )
    assert res_bad_type.status_code == 422


# ---------------------------------------------------------------------------
# Path Parameter Validation Tests (Positive IDs)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_path_id_validation_rejects_non_positive_ids(
    client: AsyncClient, auth_headers: dict[str, str]
):
    """Verify non-positive title IDs (0, -1) are rejected with 422 validation error."""
    # GET with 0
    res_get_zero = await client.get("/api/v1/titles/0")
    assert res_get_zero.status_code == 422

    # GET with negative ID
    res_get_neg = await client.get("/api/v1/titles/-5")
    assert res_get_neg.status_code == 422

    # PATCH with 0
    res_patch_zero = await client.patch(
        "/api/v1/titles/0",
        json={"name": "Zero ID"},
        headers=auth_headers,
    )
    assert res_patch_zero.status_code == 422

    # DELETE with 0
    res_del_zero = await client.delete(
        "/api/v1/titles/0",
        headers=auth_headers,
    )
    assert res_del_zero.status_code == 422


# ---------------------------------------------------------------------------
# Database Transaction Rollback Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_catalog_service_create_rollback_on_commit_error():
    """Verify create_title rolls back the transaction if commit fails."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit.side_effect = RuntimeError("Database connection broken")

    data = TitleCreate(
        name="Test Movie",
        content_type="movie",
        release_year=2020,
        genre="Action",
        platform="Prime",
    )

    with pytest.raises(RuntimeError, match="Database connection broken"):
        await catalog_service.create_title(mock_session, data)

    mock_session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_catalog_service_update_rollback_on_commit_error():
    """Verify update_title rolls back the transaction if commit fails."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit.side_effect = RuntimeError("Commit failure")

    mock_title = Title(
        id=1,
        name="Old Name",
        content_type="movie",
        release_year=2020,
        genre="Drama",
        platform="Netflix",
    )
    data = TitleUpdate(name="New Name")

    with pytest.raises(RuntimeError, match="Commit failure"):
        await catalog_service.update_title(mock_session, mock_title, data)

    mock_session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_catalog_service_delete_rollback_on_commit_error():
    """Verify delete_title rolls back the transaction if commit fails."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.commit.side_effect = RuntimeError("Delete commit failure")

    mock_title = Title(
        id=1,
        name="To Delete",
        content_type="movie",
        release_year=2020,
        genre="Drama",
        platform="Netflix",
    )

    with pytest.raises(RuntimeError, match="Delete commit failure"):
        await catalog_service.delete_title(mock_session, mock_title)

    mock_session.rollback.assert_awaited_once()


@pytest.mark.anyio
async def test_auth_service_register_user_rollback_on_integrity_error():
    """Verify register_user rolls back session and raises HTTP 400 on IntegrityError."""
    mock_session = AsyncMock(spec=AsyncSession)
    # Simulate get_user_by_email returning None (race condition where check passed)
    with patch("src.services.auth_service.get_user_by_email", return_value=None):
        # Simulate commit failing due to concurrent unique constraint violation
        mock_session.commit.side_effect = IntegrityError("Unique violation", params=None, orig=Exception())

        data = UserCreate(
            email="concurrent@example.com",
            username="concurrent",
            password="StrongPassword123!",
        )

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.register_user(mock_session, data)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Email already registered"
        mock_session.rollback.assert_awaited_once()
