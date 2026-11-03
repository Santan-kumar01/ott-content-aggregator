import io
import os
from unittest.mock import AsyncMock, MagicMock, patch

import groq
import httpx
import pytest

from src.core.database import settings
from src.services.transcription_service import (
    DEFAULT_TRANSCRIPTION_MODEL,
    GroqTranscriptionService,
    TranscriptionAuthenticationError,
    TranscriptionConfigurationError,
    TranscriptionConnectionError,
    TranscriptionError,
    TranscriptionInvalidAudioError,
    TranscriptionRateLimitError,
    TranscriptionResponseError,
    TranscriptionTimeoutError,
    transcribe_audio,
)


@pytest.fixture
def anyio_backend():
    """Ensure anyio tests run with asyncio backend."""
    return "asyncio"


@pytest.fixture
def mock_groq_client():
    """Create a mock AsyncGroq client with mocked audio.transcriptions."""
    client = MagicMock(spec=groq.AsyncGroq)
    client.audio = MagicMock()
    client.audio.transcriptions = MagicMock()
    client.audio.transcriptions.create = AsyncMock()
    return client


# ===========================================================================
# 1. Configuration & Missing API Key Tests
# ===========================================================================


@pytest.mark.anyio
async def test_missing_api_key_raises_configuration_error():
    """Verify missing GROQ_API_KEY raises TranscriptionConfigurationError."""
    with patch.dict(os.environ, {"GROQ_API_KEY": ""}), \
         patch.object(settings, "groq_api_key", None):
        service = GroqTranscriptionService(api_key=None)
        with pytest.raises(TranscriptionConfigurationError) as exc_info:
            await service.transcribe(b"RIFFaudio_content")

        assert "GROQ_API_KEY is not configured" in str(exc_info.value)


# ===========================================================================
# 2. Successful Transcription Tests
# ===========================================================================


@pytest.mark.anyio
async def test_successful_transcription_mocked_response(mock_groq_client):
    """Verify successful transcription returns expected text using mocked Groq response."""
    mock_response = MagicMock()
    mock_response.text = "  Inception  "
    mock_groq_client.audio.transcriptions.create.return_value = mock_response

    service = GroqTranscriptionService(api_key="gsk_test_key_12345", client=mock_groq_client)
    result = await service.transcribe(b"RIFFdummydata", filename="sample.wav")

    assert result == "Inception"
    mock_groq_client.audio.transcriptions.create.assert_awaited_once_with(
        file=("sample.wav", b"RIFFdummydata"),
        model=DEFAULT_TRANSCRIPTION_MODEL,
    )


@pytest.mark.anyio
async def test_successful_transcription_with_language_and_prompt(mock_groq_client):
    """Verify language and prompt parameters are forwarded to Groq API."""
    mock_response = MagicMock()
    mock_response.text = "Interstellar"
    mock_groq_client.audio.transcriptions.create.return_value = mock_response

    service = GroqTranscriptionService(api_key="gsk_test_key_12345", client=mock_groq_client)
    result = await service.transcribe(
        b"RIFFdummydata",
        filename="test.wav",
        language="en",
        prompt="Movie titles",
    )

    assert result == "Interstellar"
    mock_groq_client.audio.transcriptions.create.assert_awaited_once_with(
        file=("test.wav", b"RIFFdummydata"),
        model=DEFAULT_TRANSCRIPTION_MODEL,
        language="en",
        prompt="Movie titles",
    )


@pytest.mark.anyio
async def test_transcribe_accepts_file_like_object(mock_groq_client):
    """Verify service correctly accepts and reads BytesIO / file-like audio."""
    mock_response = MagicMock()
    mock_response.text = "The Dark Knight"
    mock_groq_client.audio.transcriptions.create.return_value = mock_response

    audio_stream = io.BytesIO(b"RIFFbytesio_audio_bytes")
    audio_stream.name = "audio_stream.wav"

    service = GroqTranscriptionService(api_key="gsk_test_key_12345", client=mock_groq_client)
    result = await service.transcribe(audio_stream)

    assert result == "The Dark Knight"
    mock_groq_client.audio.transcriptions.create.assert_awaited_once_with(
        file=("audio_stream.wav", b"RIFFbytesio_audio_bytes"),
        model=DEFAULT_TRANSCRIPTION_MODEL,
    )


# ===========================================================================
# 3. Empty or Invalid Transcription Response Tests
# ===========================================================================


@pytest.mark.anyio
@pytest.mark.parametrize("empty_text", ["", "   ", None, "\n\t"])
async def test_empty_transcription_response_raises_error(mock_groq_client, empty_text):
    """Verify empty or whitespace-only response text raises TranscriptionResponseError."""
    mock_response = MagicMock()
    mock_response.text = empty_text
    mock_groq_client.audio.transcriptions.create.return_value = mock_response

    service = GroqTranscriptionService(api_key="gsk_test_key_12345", client=mock_groq_client)
    with pytest.raises(TranscriptionResponseError) as exc_info:
        await service.transcribe(b"RIFFaudio")

    assert "Empty or invalid transcription response" in str(exc_info.value)


# ===========================================================================
# 4. Authentication Failure Tests
# ===========================================================================


@pytest.mark.anyio
async def test_authentication_failure_raises_authentication_error(mock_groq_client):
    """Verify HTTP 401 AuthenticationError from Groq raises TranscriptionAuthenticationError."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/audio/transcriptions")
    resp = httpx.Response(401, request=req)
    mock_groq_client.audio.transcriptions.create.side_effect = groq.AuthenticationError(
        message="Invalid API Key",
        response=resp,
        body={"error": {"message": "Invalid API Key", "type": "invalid_request_error"}},
    )

    service = GroqTranscriptionService(api_key="gsk_invalid_key", client=mock_groq_client)
    with pytest.raises(TranscriptionAuthenticationError) as exc_info:
        await service.transcribe(b"RIFFdummydata")

    assert "Groq authentication failed" in str(exc_info.value)
    assert "gsk_invalid_key" not in str(exc_info.value)


# ===========================================================================
# 5. Rate-Limit Failure Tests
# ===========================================================================


@pytest.mark.anyio
async def test_rate_limit_failure_raises_rate_limit_error(mock_groq_client):
    """Verify HTTP 429 RateLimitError from Groq raises TranscriptionRateLimitError."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/audio/transcriptions")
    resp = httpx.Response(429, request=req)
    mock_groq_client.audio.transcriptions.create.side_effect = groq.RateLimitError(
        message="Rate limit reached for requests",
        response=resp,
        body={"error": {"message": "Rate limit reached", "type": "rate_limit_error"}},
    )

    service = GroqTranscriptionService(api_key="gsk_valid_key", client=mock_groq_client)
    with pytest.raises(TranscriptionRateLimitError) as exc_info:
        await service.transcribe(b"RIFFdummydata")

    assert "rate limit" in str(exc_info.value).lower()


# ===========================================================================
# 6. Network & Timeout Failure Tests
# ===========================================================================


@pytest.mark.anyio
async def test_network_failure_raises_connection_error(mock_groq_client):
    """Verify network connection failures raise TranscriptionConnectionError."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/audio/transcriptions")
    mock_groq_client.audio.transcriptions.create.side_effect = groq.APIConnectionError(
        request=req,
        message="Connection refused",
    )

    service = GroqTranscriptionService(api_key="gsk_valid_key", client=mock_groq_client)
    with pytest.raises(TranscriptionConnectionError) as exc_info:
        await service.transcribe(b"RIFFdummydata")

    assert "Unable to connect" in str(exc_info.value)


@pytest.mark.anyio
async def test_timeout_failure_raises_timeout_error(mock_groq_client):
    """Verify request timeouts raise TranscriptionTimeoutError."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/audio/transcriptions")
    mock_groq_client.audio.transcriptions.create.side_effect = groq.APITimeoutError(request=req)

    service = GroqTranscriptionService(api_key="gsk_valid_key", client=mock_groq_client)
    with pytest.raises(TranscriptionTimeoutError) as exc_info:
        await service.transcribe(b"RIFFdummydata")

    assert "timed out" in str(exc_info.value).lower()


# ===========================================================================
# 7. Audio Validation Tests
# ===========================================================================


@pytest.mark.anyio
async def test_empty_audio_bytes_raises_invalid_audio_error():
    """Verify passing empty bytes raises TranscriptionInvalidAudioError."""
    service = GroqTranscriptionService(api_key="gsk_valid_key")
    with pytest.raises(TranscriptionInvalidAudioError) as exc_info:
        await service.transcribe(b"")

    assert "empty" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_none_audio_data_raises_invalid_audio_error():
    """Verify passing None raises TranscriptionInvalidAudioError."""
    service = GroqTranscriptionService(api_key="gsk_valid_key")
    with pytest.raises(TranscriptionInvalidAudioError) as exc_info:
        await service.transcribe(None)

    assert "must not be none" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_nonexistent_audio_file_path_raises_invalid_audio_error():
    """Verify nonexistent file path raises TranscriptionInvalidAudioError."""
    service = GroqTranscriptionService(api_key="gsk_valid_key")
    with pytest.raises(TranscriptionInvalidAudioError) as exc_info:
        await service.transcribe("nonexistent_path_file.wav")

    assert "not found" in str(exc_info.value).lower()


# ===========================================================================
# 8. Module-level Convenience Helper Tests
# ===========================================================================


@pytest.mark.anyio
async def test_transcribe_audio_convenience_function():
    """Verify module-level transcribe_audio helper forwards calls correctly."""
    mock_service = MagicMock(spec=GroqTranscriptionService)
    mock_service.transcribe = AsyncMock(return_value="Dunkirk")

    result = await transcribe_audio(
        b"RIFFaudio_bytes",
        filename="dunkirk.wav",
        language="en",
        service=mock_service,
    )

    assert result == "Dunkirk"
    mock_service.transcribe.assert_awaited_once_with(
        audio_data=b"RIFFaudio_bytes",
        filename="dunkirk.wav",
        language="en",
        prompt=None,
    )

@pytest.mark.anyio
async def test_sync_stream_read_failure_raises_invalid_audio_error():
    """Verify synchronous stream read failures are normalized."""
    class BrokenStream:
        def read(self):
            raise OSError("Stream read failed")

    service = GroqTranscriptionService(api_key="gsk_valid_key")

    with pytest.raises(TranscriptionInvalidAudioError) as exc_info:
        await service.transcribe(BrokenStream())

    assert "failed to read audio stream" in str(exc_info.value).lower()


@pytest.mark.anyio
async def test_async_stream_read_failure_raises_invalid_audio_error():
    """Verify asynchronous stream read failures are normalized."""
    class BrokenAsyncStream:
        async def read(self):
            raise OSError("Async stream read failed")

    service = GroqTranscriptionService(api_key="gsk_valid_key")

    with pytest.raises(TranscriptionInvalidAudioError) as exc_info:
        await service.transcribe(BrokenAsyncStream())

    assert "failed to read audio stream" in str(exc_info.value).lower()
