import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base, SessionLocal, get_db
from src.core.http_client import (
    close_http_client,
    get_http_client,
    init_http_client,
    sanitize_url,
)
from src.main import app
from src.models.title import Title
from src.schemas.sync import ExternalTitleMetadata
from src.services.background_tasks import (
    get_background_task_status,
    register_background_task,
    sync_title_from_external_provider_task,
)
from src.services.external_provider_service import (
    ExternalProviderError,
    ExternalProviderNotFoundError,
    ExternalProviderTimeoutError,
    ExternalProviderValidationError,
    fetch_external_title_metadata,
)


# ===========================================================================
# 1. URL SANITIZATION & HTTP CLIENT LIFECYCLE TESTS (UNIT)
# ===========================================================================


def test_sanitize_url_masks_sensitive_tokens_and_passwords():
    """Verify API keys, tokens, and credentials in URLs are masked for logs."""
    url_with_api_key = "https://api.provider.com/v1/titles?api_key=secretkey123&provider=netflix"
    sanitized = sanitize_url(url_with_api_key)
    assert "secretkey123" not in sanitized
    assert "api_key=***" in sanitized
    assert "provider=netflix" in sanitized

    url_with_token = "https://partner.ott.com/sync?token=mysecretjwttoken456"
    assert "mysecretjwttoken456" not in sanitize_url(url_with_token)
    assert "token=***" in sanitize_url(url_with_token)

    url_with_credentials = "https://user:password123@api.ott.com/titles"
    assert "password123" not in sanitize_url(url_with_credentials)
    assert "user:***@" in sanitize_url(url_with_credentials)

    assert sanitize_url("") == ""


@pytest.mark.anyio
async def test_http_client_init_and_close():
    """Verify shared async HTTP client initializes and closes cleanly."""
    client = await init_http_client()
    assert client is not None
    assert isinstance(client, httpx.AsyncClient)
    assert not client.is_closed

    await close_http_client()
    assert client.is_closed


# ===========================================================================
# 2. EXTERNAL PROVIDER ASYNC HTTP SERVICE TESTS (MOCKED HTTPX)
# ===========================================================================


@pytest.mark.anyio
async def test_fetch_external_metadata_success():
    """Verify successful external HTTP response parses and validates schema."""
    mock_payload = {
        "external_id": "ext-101",
        "name": "Interstellar Enhanced",
        "description": "Christopher Nolan space odyssey with IMAX audio",
        "content_type": "movie",
        "release_year": 2014,
        "genre": "Sci-Fi",
        "platform": "Prime Video",
        "extra_metadata": {"imdb_rating": 8.7, "duration_minutes": 169},
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    metadata = await fetch_external_title_metadata("ext-101", client=mock_client)
    assert isinstance(metadata, ExternalTitleMetadata)
    assert metadata.external_id == "ext-101"
    assert metadata.name == "Interstellar Enhanced"
    assert metadata.release_year == 2014
    assert metadata.genre == "Sci-Fi"
    assert metadata.platform == "Prime Video"


@pytest.mark.anyio
async def test_fetch_external_metadata_404_raises_not_found():
    """Verify HTTP 404 from external service raises ExternalProviderNotFoundError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response

    with pytest.raises(ExternalProviderNotFoundError) as exc_info:
        await fetch_external_title_metadata("nonexistent-id", client=mock_client)
    assert "not found on external provider" in str(exc_info.value)


@pytest.mark.anyio
async def test_fetch_external_metadata_server_error_retries_and_raises():
    """Verify 500 server error executes bounded retries and raises ExternalProviderError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_client.get.return_value = mock_response

    with patch("asyncio.sleep", new=AsyncMock()):  # Speed up retries
        with pytest.raises(ExternalProviderError) as exc_info:
            await fetch_external_title_metadata("error-id", client=mock_client)
        assert "server error" in str(exc_info.value).lower()
        # Initial attempt + 2 retries = 3 total attempts
        assert mock_client.get.call_count == 3


@pytest.mark.anyio
async def test_fetch_external_metadata_timeout_retries_and_raises():
    """Verify HTTP timeout executes bounded retries and raises ExternalProviderTimeoutError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Read timed out")

    with patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(ExternalProviderTimeoutError) as exc_info:
            await fetch_external_title_metadata("timeout-id", client=mock_client)
        assert "timed out" in str(exc_info.value).lower()
        assert mock_client.get.call_count == 3


@pytest.mark.anyio
async def test_fetch_external_metadata_connect_error_retries_and_raises():
    """Verify network connection failure retries and raises ExternalProviderError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("Failed to resolve host")

    with patch("asyncio.sleep", new=AsyncMock()):
        with pytest.raises(ExternalProviderError) as exc_info:
            await fetch_external_title_metadata("connect-fail-id", client=mock_client)
        assert "connect" in str(exc_info.value).lower()
        assert mock_client.get.call_count == 3


@pytest.mark.anyio
async def test_fetch_external_metadata_malformed_json_raises_validation_error():
    """Verify malformed non-JSON payload raises ExternalProviderValidationError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(ExternalProviderValidationError) as exc_info:
        await fetch_external_title_metadata("bad-json", client=mock_client)
    assert "malformed json" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_fetch_external_metadata_invalid_schema_raises_validation_error():
    """Verify valid JSON missing required fields raises ExternalProviderValidationError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    # Missing required 'name' field
    mock_response.json.return_value = {"external_id": "ext-123"}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(ExternalProviderValidationError) as exc_info:
        await fetch_external_title_metadata("missing-name", client=mock_client)
    assert "schema validation failed" in str(exc_info.value).lower()


# ===========================================================================
# 3. BACKGROUND PROCESSING & SYNC ENDPOINT TESTS
# ===========================================================================


@pytest.fixture
async def sync_client():
    """Create test client with isolated SQLite database and mocked Redis."""
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
    with patch("src.services.background_tasks.SessionLocal", session_factory):
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
async def sync_auth_headers(sync_client) -> dict[str, str]:
    """Register and authenticate user for write operations."""
    client, _ = sync_client
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "synctester@example.com",
            "username": "synctester",
            "password": "StrongPassword123!",
        },
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "synctester", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_sync_endpoint_unauthenticated_rejected(sync_client):
    """Verify POST /api/v1/titles/{id}/sync requires authentication."""
    client, _ = sync_client
    res = await client.post("/api/v1/titles/1/sync")
    assert res.status_code == 401


@pytest.mark.anyio
async def test_sync_endpoint_nonexistent_title_returns_404(
    sync_client,
    sync_auth_headers: dict[str, str],
):
    """Verify syncing a non-existent title returns 404 before queueing."""
    client, _ = sync_client
    res = await client.post(
        "/api/v1/titles/999999/sync",
        headers=sync_auth_headers,
    )
    assert res.status_code == 404
    assert "Title not found" in res.json()["detail"]


@pytest.mark.anyio
async def test_sync_endpoint_queues_background_task_returns_202(
    sync_client,
    sync_auth_headers: dict[str, str],
):
    """Verify POST /api/v1/titles/{id}/sync returns HTTP 202 with task_id."""
    client, _ = sync_client

    # 1. Create a title in DB
    create_res = await client.post(
        "/api/v1/titles",
        json={
            "name": "Sync Test Movie",
            "description": "Initial description",
            "content_type": "movie",
            "release_year": 2020,
            "genre": "Drama",
            "platform": "Netflix",
        },
        headers=sync_auth_headers,
    )
    assert create_res.status_code == 201
    title_id = create_res.json()["id"]

    # 2. Trigger sync with mocked external metadata
    mock_metadata = ExternalTitleMetadata(
        external_id="ext-movie-999",
        name="Sync Test Movie Updated",
        description="Updated description from provider",
        content_type="movie",
        release_year=2020,
        genre="Drama/Thriller",
        platform="Netflix",
    )
    with patch(
        "src.services.background_tasks.fetch_external_title_metadata",
        new=AsyncMock(return_value=mock_metadata),
    ):
        sync_res = await client.post(
            f"/api/v1/titles/{title_id}/sync",
            json={"external_id": "ext-movie-999", "provider": "netflix"},
            headers=sync_auth_headers,
        )
        assert sync_res.status_code == 202
        data = sync_res.json()
        assert data["status"] == "queued"
        assert data["title_id"] == title_id
        assert "task_id" in data
        assert len(data["task_id"]) > 10

        # 3. Verify task status endpoint
        task_id = data["task_id"]
        status_res = await client.get(f"/api/v1/titles/sync/tasks/{task_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["task_id"] == task_id
        assert status_data["title_id"] == title_id
        assert status_data["status"] in ("pending", "in_progress", "completed")


@pytest.mark.anyio
async def test_get_sync_task_status_unknown_task_returns_404(sync_client):
    """Verify requesting an unknown background task ID returns HTTP 404."""
    client, _ = sync_client
    res = await client.get("/api/v1/titles/sync/tasks/unknown-uuid-0000")
    assert res.status_code == 404
    assert "Background task not found" in res.json()["detail"]


# ===========================================================================
# 4. BACKGROUND TASK EXECUTION & DATABASE ISOLATION TESTS
# ===========================================================================


@pytest.mark.anyio
async def test_background_sync_task_execution_updates_db_and_invalidates_cache(
    sync_client,
):
    """Verify background task updates PostgreSQL, marks completion, and invalidates cache."""
    _, session_factory = sync_client

    # 1. Seed title in database
    async with session_factory() as session:
        title = Title(
            name="Matrix Resurrection",
            description="Old description",
            content_type="movie",
            release_year=2021,
            genre="Action",
            platform="HBO Max",
        )
        session.add(title)
        await session.commit()
        await session.refresh(title)
        title_id = title.id

    # 2. Mock external provider metadata
    mock_metadata = ExternalTitleMetadata(
        external_id="ext-matrix-4",
        name="Matrix Resurrection",
        description="Enriched synopsis from streaming metadata provider",
        release_year=2021,
        genre="Sci-Fi",
        platform="Max",
    )

    task_id = "test-task-exec-1"
    register_background_task(task_id, title_id)

    # Patch SessionLocal so background task uses our test session factory
    with patch("src.services.background_tasks.SessionLocal", session_factory):
        with patch(
            "src.services.background_tasks.fetch_external_title_metadata",
            new=AsyncMock(return_value=mock_metadata),
        ):
            with patch(
                "src.services.cache_service.invalidate_catalog",
                new=AsyncMock(return_value=True),
            ) as mock_inval:
                await sync_title_from_external_provider_task(
                    task_id=task_id,
                    title_id=title_id,
                    external_id="ext-matrix-4",
                )

                # Verify task completed
                task_status = get_background_task_status(task_id)
                assert task_status is not None
                assert task_status["status"] == "completed"
                assert task_status["result"]["title_id"] == title_id
                assert "description" in task_status["result"]["synced_fields"]

                # Verify cache invalidation was triggered post-commit
                mock_inval.assert_awaited_once_with(title_id=title_id)

    # 3. Verify PostgreSQL title record was actually updated
    async with session_factory() as session:
        updated = await session.get(Title, title_id)
        assert updated is not None
        assert updated.description == "Enriched synopsis from streaming metadata provider"
        assert updated.genre == "Sci-Fi"
        assert updated.platform == "Max"


@pytest.mark.anyio
async def test_background_sync_task_handles_external_failure_gracefully(
    sync_client,
):
    """Verify background task handles external HTTP error, rolls back DB, and records failure."""
    _, session_factory = sync_client

    async with session_factory() as session:
        title = Title(
            name="Unchanged Movie",
            description="Original description",
            content_type="movie",
            release_year=2022,
            genre="Comedy",
            platform="Netflix",
        )
        session.add(title)
        await session.commit()
        await session.refresh(title)
        title_id = title.id

    task_id = "test-task-failure-1"
    register_background_task(task_id, title_id)

    with patch("src.services.background_tasks.SessionLocal", session_factory):
        with patch(
            "src.services.background_tasks.fetch_external_title_metadata",
            side_effect=ExternalProviderTimeoutError("External service timeout"),
        ):
            await sync_title_from_external_provider_task(
                task_id=task_id,
                title_id=title_id,
            )

            # Verify task marked as failed with descriptive error
            status = get_background_task_status(task_id)
            assert status is not None
            assert status["status"] == "failed"
            assert "External service timeout" in status["error"]

    # Verify database was NOT corrupted
    async with session_factory() as session:
        persisted = await session.get(Title, title_id)
        assert persisted is not None
        assert persisted.description == "Original description"
        assert persisted.genre == "Comedy"


@pytest.mark.anyio
async def test_background_sync_task_nonexistent_title_records_failure():
    """Verify background task records failure when target title is missing from DB."""
    task_id = "test-task-missing-title"
    register_background_task(task_id, 999999)

    mock_session = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__.return_value = mock_session
    mock_session_ctx.__aexit__.return_value = None

    with patch(
        "src.services.background_tasks.SessionLocal",
        return_value=mock_session_ctx,
    ):
        with patch(
            "src.services.catalog_service.get_title",
            new=AsyncMock(return_value=None),
        ):
            await sync_title_from_external_provider_task(
                task_id=task_id,
                title_id=999999,
            )

            status = get_background_task_status(task_id)
            assert status is not None
            assert status["status"] == "failed"
            assert "not found in database" in status["error"]
