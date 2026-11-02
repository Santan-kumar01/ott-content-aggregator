"""Integration tests for the voice catalog search endpoint: POST /api/v1/voice/search.

Covers:
1. Successful transcription followed by catalog search.
2. Correct extraction and forwarding of search criteria.
3. No matching catalog results.
4. Empty and whitespace-only transcription handling.
5. Genre-search queries (e.g. "Find action movies").
6. Similarity-intent queries without inventing recommendation results.
7. Streaming platform and release year filtering via voice.
8. Audio upload validation (empty, invalid format, missing filename, oversized).
9. Upstream transcription provider failures (auth, timeout, rate limit, config, connection).
10. Catalog database failures (safe 500 without leaking credentials).
11. Backward compatibility of POST /api/v1/voice/transcribe.
"""

import asyncio
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.cache import get_redis_client
from src.core.database import Base, get_db
from src.main import app
from src.models.title import Title
from src.services.cache_service import CATALOG_GENERATION_KEY
from src.services.query_parser_service import (
    QueryParserService,
    get_query_parser_service,
)
from src.services.transcription_service import (
    GroqTranscriptionService,
    TranscriptionAuthenticationError,
    TranscriptionConfigurationError,
    TranscriptionConnectionError,
    TranscriptionError,
    TranscriptionInvalidAudioError,
    TranscriptionRateLimitError,
    TranscriptionResponseError,
    TranscriptionTimeoutError,
    get_transcription_service,
)


@pytest.fixture
def anyio_backend():
    """Ensure anyio tests run with asyncio backend."""
    return "asyncio"


def make_valid_wav_bytes(payload_length: int = 100) -> bytes:
    """Generate minimal valid 44-byte standard PCM WAV header followed by silent payload."""
    payload = b"\x00" * payload_length
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(payload),
        b"WAVE",
        b"fmt ",
        16,
        1,  # AudioFormat (PCM)
        1,  # NumChannels (mono)
        16000,  # SampleRate
        32000,  # ByteRate
        2,  # BlockAlign
        16,  # BitsPerSample
        b"data",
        len(payload),
    )
    return header + payload


@pytest.fixture
def mock_transcription_service():
    """Fixture providing a mock GroqTranscriptionService returning 'Inception' by default."""
    mock_svc = MagicMock(spec=GroqTranscriptionService)
    mock_svc.transcribe = AsyncMock(return_value="Show me Inception")
    return mock_svc


@pytest.fixture
def query_parser():
    """Real query parser service fixture."""
    return QueryParserService()


@pytest.fixture
async def client_and_db(mock_transcription_service, query_parser):
    """Isolated in-memory SQLite database and test client with seeded catalog data."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Seed catalog titles
    async with session_factory() as session:
        titles = [
            Title(
                name="Inception",
                description="Mind heist sci-fi thriller dreaming within dreams",
                content_type="movie",
                release_year=2010,
                genre="Sci-Fi",
                platform="Netflix",
            ),
            Title(
                name="Interstellar",
                description="A team of explorers travel through a wormhole in space",
                content_type="movie",
                release_year=2014,
                genre="Sci-Fi",
                platform="Prime",
            ),
            Title(
                name="The Dark Knight",
                description="Batman fights Joker in Gotham City",
                content_type="movie",
                release_year=2008,
                genre="Action",
                platform="HBO Max",
            ),
            Title(
                name="Die Hard",
                description="NYPD cop takes on terrorists in a skyscraper",
                content_type="movie",
                release_year=1988,
                genre="Action",
                platform="Netflix",
            ),
            Title(
                name="Friends",
                description="Six friends navigating life and love in Manhattan",
                content_type="show",
                release_year=1994,
                genre="Comedy",
                platform="Max",
            ),
            Title(
                name="Airplane!",
                description="Spoof comedy about an airplane crew struck by food poisoning",
                content_type="movie",
                release_year=1980,
                genre="Comedy",
                platform="Prime",
            ),
            Title(
                name="Breaking Bad",
                description="Chemistry teacher turns to methamphetamine manufacture",
                content_type="show",
                release_year=2008,
                genre="Drama",
                platform="Netflix",
            ),
        ]
        session.add_all(titles)
        await session.commit()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_transcription_service] = lambda: mock_transcription_service
    app.dependency_overrides[get_query_parser_service] = lambda: query_parser

    # Isolate Redis catalog generation between test cases when live Redis is present
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            await redis_client.incr(CATALOG_GENERATION_KEY)
        except Exception:
            pass

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            yield ac, session_factory
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


# ===========================================================================
# 1. Successful Transcription Followed by Catalog Search
# ===========================================================================


@pytest.mark.anyio
async def test_successful_voice_search(client_and_db, mock_transcription_service):
    """Verify speech upload transcribes, parses 'Show me Inception', and returns catalog title."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Show me Inception"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["transcription"] == "Show me Inception"
    assert data["parsed_query"]["search_query"] == "Inception"
    assert data["parsed_query"]["cleaned_query"] == "Inception"
    assert data["parsed_query"]["intent"] == "search"
    assert data["count"] == 1
    assert data["total"] == 1

    # Verify matching title attributes and provider availability
    title = data["titles"][0]
    assert title["name"] == "Inception"
    assert title["genre"] == "Sci-Fi"
    assert title["platform"] == "Netflix"
    assert title["release_year"] == 2010


# ===========================================================================
# 2. Correct Extraction and Forwarding of Search Query
# ===========================================================================


@pytest.mark.anyio
async def test_search_query_forwarding_complex_prompt(client_and_db, mock_transcription_service):
    """Verify conversational prefix 'I want to watch' is stripped and title is forwarded."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "I want to watch The Dark Knight"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("search.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["parsed_query"]["search_query"] == "The Dark Knight"
    assert data["count"] == 1
    assert data["titles"][0]["name"] == "The Dark Knight"
    assert data["titles"][0]["genre"] == "Action"
    assert data["titles"][0]["platform"] == "HBO Max"


# ===========================================================================
# 3. No Matching Catalog Results
# ===========================================================================


@pytest.mark.anyio
async def test_no_matching_catalog_results(client_and_db, mock_transcription_service):
    """Verify query with no catalog match returns empty titles list with 200 OK."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Search for NonexistentMovieXYZ"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["transcription"] == "Search for NonexistentMovieXYZ"
    assert data["parsed_query"]["search_query"] == "NonexistentMovieXYZ"
    assert data["titles"] == []
    assert data["count"] == 0
    assert data["total"] == 0


# ===========================================================================
# 4. Empty and Whitespace Transcription Handling
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("empty_transcript", ["", "   ", "\t\n"])
async def test_empty_transcription_returns_safe_empty_results(
    client_and_db, mock_transcription_service, empty_transcript
):
    """Verify empty/silent transcription is handled safely without querying DB or crashing."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = empty_transcript

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("silence.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["transcription"] == empty_transcript
    assert data["parsed_query"]["intent"] == "empty"
    assert data["titles"] == []
    assert data["count"] == 0
    assert data["total"] == 0


# ===========================================================================
# 5. Genre-Search Queries
# ===========================================================================


@pytest.mark.anyio
async def test_genre_search_query(client_and_db, mock_transcription_service):
    """Verify 'Find action movies' filters by genre without restricting search title."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Find action movies"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("genre.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["parsed_query"]["genre"] == "Action"
    assert data["parsed_query"]["search_query"] is None
    assert data["parsed_query"]["intent"] == "genre_search"

    # Both The Dark Knight and Die Hard are Action movies
    names = {t["name"] for t in data["titles"]}
    assert "The Dark Knight" in names
    assert "Die Hard" in names
    assert "Inception" not in names  # Sci-Fi
    assert data["count"] == 2


@pytest.mark.anyio
async def test_content_type_filtering_distinguishes_movies_and_shows(
    client_and_db, mock_transcription_service
):
    """Verify content_type (movie vs show) filters catalog results when requested."""
    client, _ = client_and_db

    # 1. Query for comedy SHOWS: should only return Friends (show), not Airplane! (movie)
    mock_transcription_service.transcribe.return_value = "Find comedy shows"
    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    res_shows = await client.post("/api/v1/voice/search", files=files)
    assert res_shows.status_code == 200
    data_shows = res_shows.json()
    assert data_shows["parsed_query"]["genre"] == "Comedy"
    assert data_shows["parsed_query"]["content_type"] == "show"
    names_shows = [t["name"] for t in data_shows["titles"]]
    assert "Friends" in names_shows
    assert "Airplane!" not in names_shows
    assert data_shows["count"] == 1

    # 2. Query for comedy MOVIES: should only return Airplane! (movie), not Friends (show)
    mock_transcription_service.transcribe.return_value = "Find comedy movies"
    res_movies = await client.post("/api/v1/voice/search", files=files)
    assert res_movies.status_code == 200
    data_movies = res_movies.json()
    assert data_movies["parsed_query"]["genre"] == "Comedy"
    assert data_movies["parsed_query"]["content_type"] == "movie"
    names_movies = [t["name"] for t in data_movies["titles"]]
    assert "Airplane!" in names_movies
    assert "Friends" not in names_movies
    assert data_movies["count"] == 1

    # 3. Query for generic comedy (no content_type): should return both Friends and Airplane!
    mock_transcription_service.transcribe.return_value = "Show me comedy"
    res_all = await client.post("/api/v1/voice/search", files=files)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["parsed_query"]["genre"] == "Comedy"
    assert data_all["parsed_query"]["content_type"] is None
    names_all = {t["name"] for t in data_all["titles"]}
    assert "Friends" in names_all
    assert "Airplane!" in names_all
    assert data_all["count"] == 2


# ===========================================================================
# 6. Similarity-Intent Queries (Without Inventing Fake Recommendations)
# ===========================================================================


@pytest.mark.anyio
async def test_similarity_intent_query(client_and_db, mock_transcription_service):
    """Verify 'Find movies like Interstellar' preserves title & similarity intent without fake recs."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Find movies like Interstellar"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("similar.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["parsed_query"]["search_query"] == "Interstellar"
    assert data["parsed_query"]["is_similarity"] is True
    assert data["parsed_query"]["similar_to"] == "Interstellar"
    assert data["parsed_query"]["content_type"] == "movie"
    assert data["parsed_query"]["intent"] == "similar"

    # Forwarded to catalog as search='Interstellar'
    assert data["count"] == 1
    assert data["titles"][0]["name"] == "Interstellar"
    assert data["titles"][0]["platform"] == "Prime"


# ===========================================================================
# 7. Platform and Release Year Extraction via Voice
# ===========================================================================


@pytest.mark.anyio
async def test_voice_search_with_platform_filter(client_and_db, mock_transcription_service):
    """Verify 'Watch Inception on Netflix' filters by both title and platform."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Watch Inception on Netflix"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["parsed_query"]["search_query"] == "Inception"
    assert data["parsed_query"]["platform"] == "Netflix"
    assert data["count"] == 1
    assert data["titles"][0]["name"] == "Inception"
    assert data["titles"][0]["platform"] == "Netflix"


# ===========================================================================
# 8. Audio Upload Validation
# ===========================================================================


@pytest.mark.anyio
async def test_search_empty_audio_upload_rejected(client_and_db):
    """Verify empty 0-byte upload to /search returns 400 Bad Request."""
    client, _ = client_and_db
    files = {"file": ("empty.wav", b"", "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_invalid_audio_format_rejected(client_and_db):
    """Verify corrupt/invalid audio payload returns 400 Bad Request."""
    client, _ = client_and_db
    files = {"file": ("bad.wav", b"NOT_REAL_AUDIO_DATA_PAYLOAD", "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 400
    assert "unsupported or invalid audio format" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_missing_filename_rejected(client_and_db):
    """Verify whitespace filename returns 400 Bad Request."""
    client, _ = client_and_db
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("   ", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 400


# ===========================================================================
# 9. Transcription Provider Failures
# ===========================================================================


@pytest.mark.anyio
async def test_search_missing_groq_configuration_returns_503(
    client_and_db, mock_transcription_service
):
    """Verify missing GROQ_API_KEY returns 503 Service Unavailable."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = TranscriptionConfigurationError("No key")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 503
    assert "currently unavailable" in response.json()["detail"]


@pytest.mark.anyio
async def test_search_provider_authentication_failure_returns_502(
    client_and_db, mock_transcription_service
):
    """Verify upstream auth failure returns 502 Bad Gateway without leaking keys."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = TranscriptionAuthenticationError("Bad key")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 502
    assert "authentication failed" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_provider_rate_limit_returns_429(
    client_and_db, mock_transcription_service
):
    """Verify rate limit returns 429 Too Many Requests."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = TranscriptionRateLimitError("Quota reached")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_provider_timeout_returns_504(
    client_and_db, mock_transcription_service
):
    """Verify provider timeout returns 504 Gateway Timeout."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = TranscriptionTimeoutError("Timed out")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_search_provider_connection_error_returns_502(
    client_and_db, mock_transcription_service
):
    """Verify network connection failure returns 502 Bad Gateway."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = TranscriptionConnectionError("Net down")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 502
    assert "unable to connect" in response.json()["detail"].lower()


# ===========================================================================
# 10. Catalog Service Failure
# ===========================================================================


@pytest.mark.anyio
async def test_search_catalog_failure_returns_safe_500(
    client_and_db, mock_transcription_service
):
    """Verify database/catalog failure returns 500 without leaking DB internals."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Show me Inception"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    with patch("src.services.cache_service.get_catalog_list", new=AsyncMock(return_value=None)), \
         patch("src.services.catalog_service.list_titles", side_effect=Exception("Database lock error")):
        response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 500
    assert response.json() == {"detail": "An error occurred while querying the catalog."}


# ===========================================================================
# 11. Backward Compatibility of POST /api/v1/voice/transcribe
# ===========================================================================


@pytest.mark.anyio
async def test_backward_compatibility_transcribe_endpoint(
    client_and_db, mock_transcription_service
):
    """Verify POST /api/v1/voice/transcribe remains completely unchanged in contract."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Inception"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 200
    assert response.json() == {"text": "Inception"}


# ===========================================================================
# 12. OpenAPI Schema Contains Both Voice Endpoints
# ===========================================================================


@pytest.mark.anyio
async def test_openapi_schema_contains_both_voice_endpoints(client_and_db):
    """Verify OpenAPI documentation accurately registers /transcribe and /search."""
    client, _ = client_and_db
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})

    assert "/api/v1/voice/transcribe" in paths
    assert "post" in paths["/api/v1/voice/transcribe"]
    assert "/api/v1/voice/search" in paths
    assert "post" in paths["/api/v1/voice/search"]


# ===========================================================================
# 13. Hardening & Fault Tolerance Scenarios (Task 6)
# ===========================================================================


@pytest.mark.anyio
async def test_voice_search_succeeds_even_when_cache_service_fails(
    client_and_db, mock_transcription_service, caplog
):
    """Verify search succeeds via database even if cache lookup or write throws an unhandled exception.

    Verifies:
    1. Cache-read failure falls back to PostgreSQL.
    2. Cache-write failure does not turn successful database results into HTTP 500.
    3. Successful database results are returned even when caching fails.
    4. Database query is executed exactly once (cache-write failure does not repeat query).
    5. Cache failures do not leak internal details to the client.
    6. Appropriate warning logs record the failure class name without sensitive credentials or transcripts.
    """
    import logging
    from src.services import catalog_service

    client, _ = client_and_db
    mock_transcription_service.transcribe.return_value = "Show me Inception"

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    real_list_titles = catalog_service.list_titles
    with patch(
        "src.services.cache_service.get_catalog_list",
        side_effect=ConnectionRefusedError("Redis connection refused to redis://:supersecret@127.0.0.1:6379/0"),
    ), patch(
        "src.services.cache_service.set_catalog_list",
        side_effect=TimeoutError("Redis write timed out after 2.0s"),
    ), patch(
        "src.services.catalog_service.list_titles",
        side_effect=real_list_titles,
    ) as spy_list_titles, patch(
        "src.api.endpoints.voice.logger.warning"
    ) as mock_logger_warning, caplog.at_level(logging.WARNING):
        response = await client.post("/api/v1/voice/search", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["titles"][0]["name"] == "Inception"

    # Verify database query was called exactly once and not repeated
    assert spy_list_titles.call_count == 1

    # Verify no cache error details leaked to client
    assert "redis" not in response.text.lower()
    assert "supersecret" not in response.text.lower()

    # Verify warning logs recorded the exception class names without sensitive credentials
    assert mock_logger_warning.call_count == 2
    warning_calls = [c.args for c in mock_logger_warning.call_args_list]
    warning_messages = [m % tuple(a) if a else m for m, *a in warning_calls]
    warning_text = " ".join(warning_messages) + " " + caplog.text
    assert "Cache lookup failed during voice search: ConnectionRefusedError" in warning_text
    assert "Failed to populate catalog cache in voice search: TimeoutError" in warning_text
    assert "supersecret" not in warning_text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("param", "val"),
    [
        ("skip", -1),
        ("limit", 0),
        ("limit", 101),
    ],
)
async def test_voice_search_invalid_pagination_parameters_rejected(
    client_and_db, param, val
):
    """Verify invalid pagination boundaries (skip < 0, limit < 1, limit > 100) return 422."""
    client, _ = client_and_db
    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post(f"/api/v1/voice/search?{param}={val}", files=files)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_voice_search_unexpected_transcription_exception_mapped_to_502(
    client_and_db, mock_transcription_service
):
    """Verify unhandled transcription exceptions are safely mapped to 502 without leaking stack traces."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = RuntimeError("Low-level network socket crashed")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 502
    assert "error occurred while communicating with the transcription provider" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_oversized_audio_upload_rejected_on_search(client_and_db):
    """Verify files exceeding 10 MB limit are rejected with HTTP 413 on /search."""
    client, _ = client_and_db
    # Create valid WAV header with 11 MB payload
    eleven_mb = 11 * 1024 * 1024
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + eleven_mb,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        16000,
        32000,
        2,
        16,
        b"data",
        eleven_mb,
    )
    oversized_data = header + b"\x00" * eleven_mb
    files = {"file": ("oversized.wav", oversized_data, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 413
    assert "exceeds the maximum allowed size" in response.json()["detail"].lower()


def test_transcription_exception_handler_control_flow_preservation():
    """Ensure control-flow exceptions (CancelledError, KeyboardInterrupt, HTTPException) are re-raised without swallowing."""
    from src.api.endpoints.voice import _handle_transcription_exception

    with pytest.raises(asyncio.CancelledError):
        _handle_transcription_exception(asyncio.CancelledError("task cancelled"))

    with pytest.raises(KeyboardInterrupt):
        _handle_transcription_exception(KeyboardInterrupt())

    with pytest.raises(SystemExit):
        _handle_transcription_exception(SystemExit(1))

    custom_http_err = HTTPException(status_code=403, detail="Forbidden")
    with pytest.raises(HTTPException) as exc_info:
        _handle_transcription_exception(custom_http_err)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden"


@pytest.mark.anyio
async def test_voice_search_cancellation_error_not_swallowed(
    client_and_db, mock_transcription_service
):
    """Verify asyncio.CancelledError propagates out of the endpoint rather than returning an HTTP 502."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = asyncio.CancelledError("Task cancelled by client")

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    # In Starlette middleware, an unswallowed BaseException causes the request task to cancel
    # rather than completing with an HTTP 502 error response.
    with pytest.raises((asyncio.CancelledError, RuntimeError)):
        await client.post("/api/v1/voice/search", files=files)


@pytest.mark.anyio
async def test_voice_search_http_exception_during_transcription_preserved(
    client_and_db, mock_transcription_service
):
    """Verify that an explicit HTTPException is preserved and not converted to a generic 502."""
    client, _ = client_and_db
    mock_transcription_service.transcribe.side_effect = HTTPException(
        status_code=403,
        detail="Audio transcription access forbidden for this account.",
    )

    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/search", files=files)
    assert response.status_code == 403
    assert "Audio transcription access forbidden" in response.json()["detail"]
