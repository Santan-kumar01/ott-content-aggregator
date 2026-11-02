import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.core.database import settings
from src.main import app
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
        1,       # AudioFormat (PCM)
        1,       # NumChannels (mono)
        16000,   # SampleRate
        32000,   # ByteRate (SampleRate * NumChannels * BitsPerSample/8)
        2,       # BlockAlign
        16,      # BitsPerSample
        b"data",
        len(payload),
    )
    return header + payload


@pytest.fixture
def mock_transcription_service():
    """Fixture providing a mock GroqTranscriptionService."""
    mock_svc = MagicMock(spec=GroqTranscriptionService)
    mock_svc.transcribe = AsyncMock(return_value="Inception")
    return mock_svc


@pytest.fixture
async def client(mock_transcription_service):
    """Async test client with dependency override for transcription service."""
    app.dependency_overrides[get_transcription_service] = lambda: mock_transcription_service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_transcription_service, None)


# ===========================================================================
# 1. Successful Upload and Transcription
# ===========================================================================


@pytest.mark.anyio
async def test_successful_audio_upload_and_transcription(client, mock_transcription_service):
    """Verify valid audio file upload returns 200 with transcribed text."""
    wav_bytes = make_valid_wav_bytes(200)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 200
    assert response.json() == {"text": "Inception"}
    mock_transcription_service.transcribe.assert_awaited_once()


# ===========================================================================
# 2. Empty Audio Upload
# ===========================================================================


@pytest.mark.anyio
async def test_empty_audio_upload_rejected(client):
    """Verify zero-byte audio file returns 400 Bad Request."""
    files = {"file": ("empty.wav", b"", "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


# ===========================================================================
# 3. Missing Filename or Invalid Upload
# ===========================================================================


@pytest.mark.anyio
async def test_missing_filename_rejected(client):
    """Verify upload with missing or blank filename returns 400 or 422."""
    wav_bytes = make_valid_wav_bytes(100)

    # Empty filename (FastAPI/Starlette multipart rejects as unprocessable entity)
    response_empty = await client.post(
        "/api/v1/voice/transcribe", files={"file": ("", wav_bytes, "audio/wav")}
    )
    assert response_empty.status_code in (400, 422)

    # Whitespace filename (endpoint validator rejects as bad request)
    response_whitespace = await client.post(
        "/api/v1/voice/transcribe", files={"file": ("   ", wav_bytes, "audio/wav")}
    )
    assert response_whitespace.status_code == 400
    assert "filename" in response_whitespace.json()["detail"].lower()


# ===========================================================================
# 4. Unsupported or Invalid Audio Input
# ===========================================================================


@pytest.mark.anyio
async def test_unsupported_audio_format_rejected(client):
    """Verify non-audio payload (e.g., text or corrupted bytes) returns 400 Bad Request."""
    fake_audio = b"This is plain text content pretending to be audio"
    files = {"file": ("fake.wav", fake_audio, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 400
    assert "unsupported or invalid audio format" in response.json()["detail"].lower()


# ===========================================================================
# 5. Missing Groq Server Configuration
# ===========================================================================


@pytest.mark.anyio
async def test_missing_groq_configuration_returns_503(client, mock_transcription_service):
    """Verify missing server-side API key returns 503 Service Unavailable."""
    mock_transcription_service.transcribe.side_effect = TranscriptionConfigurationError(
        "GROQ_API_KEY is not configured in the environment."
    )
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    assert "gsk" not in response.text


# ===========================================================================
# 6. Provider Rate-Limit Failure
# ===========================================================================


@pytest.mark.anyio
async def test_provider_rate_limit_failure_returns_429(client, mock_transcription_service):
    """Verify provider rate limit returns 429 Too Many Requests."""
    mock_transcription_service.transcribe.side_effect = TranscriptionRateLimitError(
        "Rate limit exceeded."
    )
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


# ===========================================================================
# 7. Provider Timeout
# ===========================================================================


@pytest.mark.anyio
async def test_provider_timeout_returns_504(client, mock_transcription_service):
    """Verify provider timeout returns 504 Gateway Timeout."""
    mock_transcription_service.transcribe.side_effect = TranscriptionTimeoutError(
        "Request timed out."
    )
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"].lower()


# ===========================================================================
# 8. Provider Connection Failure
# ===========================================================================


@pytest.mark.anyio
async def test_provider_connection_failure_returns_502(client, mock_transcription_service):
    """Verify connection failure to upstream provider returns 502 Bad Gateway."""
    mock_transcription_service.transcribe.side_effect = TranscriptionConnectionError(
        "Unable to connect to provider."
    )
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 502
    assert "unable to connect" in response.json()["detail"].lower()


# ===========================================================================
# 9. Unexpected Provider Error
# ===========================================================================


@pytest.mark.anyio
async def test_unexpected_provider_error_returns_502(client, mock_transcription_service):
    """Verify unexpected provider error returns 502 Bad Gateway."""
    mock_transcription_service.transcribe.side_effect = TranscriptionError(
        "Upstream internal error."
    )
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 502
    assert "error occurred while communicating" in response.json()["detail"].lower()


# ===========================================================================
# 10. Oversized Upload Rejection
# ===========================================================================


@pytest.mark.anyio
async def test_oversized_audio_upload_rejected(client):
    """Verify upload exceeding maximum configured size is rejected with 413."""
    with patch.object(settings, "max_voice_upload_bytes", 200):
        # Generate audio payload exceeding 200 bytes limit
        wav_bytes = make_valid_wav_bytes(300)
        files = {"file": ("large.wav", wav_bytes, "audio/wav")}

        response = await client.post("/api/v1/voice/transcribe", files=files)

        assert response.status_code == 413
        assert "exceeds the maximum allowed size" in response.json()["detail"].lower()


# ===========================================================================
# 11. Sensitive Provider Details Not Exposed
# ===========================================================================


@pytest.mark.anyio
async def test_sensitive_credentials_not_exposed_on_auth_failure(client, mock_transcription_service):
    """Verify upstream auth failure returns safe 502 without leaking secrets or headers."""
    mock_transcription_service.transcribe.side_effect = TranscriptionAuthenticationError(
        "Groq authentication failed. Secret key: gsk_super_secret_12345"
    )
    wav_bytes = make_valid_wav_bytes(100)
    files = {"file": ("query.wav", wav_bytes, "audio/wav")}

    response = await client.post("/api/v1/voice/transcribe", files=files)

    assert response.status_code == 502
    assert "gsk_super_secret_12345" not in response.text
    assert "Secret key" not in response.text
    assert "authentication failed" in response.json()["detail"].lower()


# ===========================================================================
# 12. OpenAPI Schema Presence
# ===========================================================================


def test_openapi_schema_contains_voice_transcribe_endpoint():
    """Verify endpoint is documented in the generated OpenAPI schema."""
    openapi = app.openapi()
    assert "/api/v1/voice/transcribe" in openapi["paths"]
    post_op = openapi["paths"]["/api/v1/voice/transcribe"]["post"]
    assert "Voice" in post_op["tags"]
    assert post_op["summary"] == "Transcribe uploaded audio file"
