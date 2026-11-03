import asyncio
import logging
import os
from typing import Any, BinaryIO, Union

import groq
from groq import AsyncGroq

from src.core.database import settings

logger = logging.getLogger("src.services.transcription_service")

# Default model per Groq documentation
DEFAULT_TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
DEFAULT_TIMEOUT_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Custom Exception Hierarchy
# ---------------------------------------------------------------------------


class TranscriptionError(Exception):
    """Base exception for transcription service errors."""
    pass


class TranscriptionConfigurationError(TranscriptionError):
    """Raised when Groq API key or required configuration is missing or invalid."""
    pass


class TranscriptionAuthenticationError(TranscriptionError):
    """Raised when Groq API credentials fail authentication (HTTP 401)."""
    pass


class TranscriptionRateLimitError(TranscriptionError):
    """Raised when Groq rate limits or quota are exceeded (HTTP 429)."""
    pass


class TranscriptionTimeoutError(TranscriptionError):
    """Raised when request to Groq API times out."""
    pass


class TranscriptionConnectionError(TranscriptionError):
    """Raised when connection to Groq API fails."""
    pass


class TranscriptionInvalidAudioError(TranscriptionError):
    """Raised when audio payload or file format is empty or invalid (HTTP 400)."""
    pass


class TranscriptionResponseError(TranscriptionError):
    """Raised when Groq returns an empty, malformed, or invalid transcription response."""
    pass


# ---------------------------------------------------------------------------
# Service Implementation
# ---------------------------------------------------------------------------


AudioInputType = Union[bytes, BinaryIO, tuple[str, bytes], str, os.PathLike]


class GroqTranscriptionService:
    """Reusable service for transcribing audio via the official Groq Speech-to-Text API.

    Uses the asynchronous AsyncGroq client to prevent event loop blocking in FastAPI,
    applies safe error sanitization without logging credentials or audio payloads,
    and supports flexible audio input types.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        client: AsyncGroq | None = None,
    ) -> None:
        self._api_key = (
            api_key
            or getattr(settings, "groq_api_key", None)
            or os.getenv("GROQ_API_KEY")
        )
        if self._api_key:
            self._api_key = self._api_key.strip()

        self._model = (
            model
            or getattr(settings, "groq_transcription_model", None)
            or DEFAULT_TRANSCRIPTION_MODEL
        )
        self._timeout = (
            timeout
            or getattr(settings, "groq_timeout_seconds", None)
            or DEFAULT_TIMEOUT_SECONDS
        )
        self._client = client

    def get_client(self) -> AsyncGroq:
        """Retrieve or initialize the AsyncGroq client.

        Raises TranscriptionConfigurationError if GROQ_API_KEY is missing.
        """
        if self._client is not None:
            return self._client

        if not self._api_key:
            raise TranscriptionConfigurationError(
                "GROQ_API_KEY is not configured in the environment."
            )

        self._client = AsyncGroq(
            api_key=self._api_key,
            timeout=self._timeout,
        )
        return self._client

    async def _normalize_audio_input(
        self,
        audio_data: AudioInputType,
        filename: str = "audio.wav",
    ) -> tuple[str, bytes]:
        """Validate and convert various audio input formats into (filename, bytes)."""
        if audio_data is None:
            raise TranscriptionInvalidAudioError("Audio data must not be None.")

        # Handle file paths (str or PathLike)
        if isinstance(audio_data, (str, os.PathLike)):
            path = str(audio_data)
            if not os.path.isfile(path):
                raise TranscriptionInvalidAudioError(f"Audio file not found: {path}")
            try:
                with open(path, "rb") as f:
                    content = f.read()
            except Exception as e:
                raise TranscriptionInvalidAudioError(f"Failed to read audio file: {e}") from None

            if not content:
                raise TranscriptionInvalidAudioError("Audio file is empty.")
            return os.path.basename(path), content

        # Handle (filename, bytes) tuple
        if isinstance(audio_data, tuple):
            if len(audio_data) != 2:
                raise TranscriptionInvalidAudioError("Audio tuple must contain (filename, bytes).")
            name, content = audio_data
            if not content or not isinstance(content, bytes) or len(content) == 0:
                raise TranscriptionInvalidAudioError("Audio content in tuple is empty or invalid.")
            return name or filename, content

        # Handle raw bytes
        if isinstance(audio_data, bytes):
            if len(audio_data) == 0:
                raise TranscriptionInvalidAudioError("Audio data is empty.")
            return filename, audio_data

        # Handle file-like objects or UploadFile
        if hasattr(audio_data, "read"):
            try:
                read_result = audio_data.read()
                if asyncio.iscoroutine(read_result):
                    content = await read_result
                else:
                    content = read_result
            except Exception as exc:
                raise TranscriptionInvalidAudioError(
                    f"Failed to read audio stream: {type(exc).__name__}"
                ) from None

            if not content or not isinstance(content, bytes) or len(content) == 0:
                raise TranscriptionInvalidAudioError("Audio file content is empty.")

            detected_name = getattr(audio_data, "filename", None) or getattr(audio_data, "name", None)
            return (os.path.basename(detected_name) if detected_name else filename), content

        raise TranscriptionInvalidAudioError(
            f"Unsupported audio input type: {type(audio_data).__name__}"
        )

    async def transcribe(
        self,
        audio_data: AudioInputType,
        filename: str = "audio.wav",
        *,
        language: str | None = None,
        prompt: str | None = None,
    ) -> str:
        """Asynchronously transcribe audio using Groq Speech-to-Text.

        Args:
            audio_data: Audio payload as bytes, file-like object, path, or (filename, bytes) tuple.
            filename: Fallback filename used when sending multipart payload.
            language: Optional ISO-639-1 language code (e.g. 'en', 'hi').
            prompt: Optional context prompt to guide transcription style/terminology.

        Returns:
            The normalized transcription text.

        Raises:
            TranscriptionConfigurationError: If GROQ_API_KEY is missing.
            TranscriptionInvalidAudioError: If audio is empty or rejected as invalid format.
            TranscriptionAuthenticationError: If API credentials are unauthorized (401).
            TranscriptionRateLimitError: If API quota or rate limit is exceeded (429).
            TranscriptionTimeoutError: If the request times out.
            TranscriptionConnectionError: If network connectivity fails.
            TranscriptionResponseError: If the API returns an empty or invalid transcription.
            TranscriptionError: For other unexpected API or SDK errors.
        """
        # Validate and prepare audio data
        file_tuple = await self._normalize_audio_input(audio_data, filename=filename)

        # Retrieve client (verifies API key presence)
        client = self.get_client()

        request_kwargs: dict[str, Any] = {
            "file": file_tuple,
            "model": self._model,
        }
        if language:
            request_kwargs["language"] = language
        if prompt:
            request_kwargs["prompt"] = prompt

        logger.debug("Dispatching audio transcription request to Groq (model=%s)", self._model)

        try:
            response = await client.audio.transcriptions.create(**request_kwargs)
        except groq.AuthenticationError:
            logger.error("Groq authentication failure (HTTP 401). Check GROQ_API_KEY.")
            raise TranscriptionAuthenticationError(
                "Groq authentication failed. Please verify your GROQ_API_KEY."
            ) from None
        except groq.RateLimitError as err:
            logger.warning("Groq rate limit exceeded (HTTP 429).")
            raise TranscriptionRateLimitError(
                f"Groq rate limit or quota exceeded: {getattr(err, 'message', 'Rate limit hit')}"
            ) from None
        except (groq.APITimeoutError, asyncio.TimeoutError):
            logger.warning("Groq transcription request timed out.")
            raise TranscriptionTimeoutError(
                "Groq speech transcription request timed out."
            ) from None
        except groq.APIConnectionError:
            logger.warning("Connection failure to Groq API endpoints.")
            raise TranscriptionConnectionError(
                "Unable to connect to Groq API endpoints."
            ) from None
        except groq.BadRequestError as err:
            logger.warning("Groq rejected bad transcription request (HTTP 400).")
            raise TranscriptionInvalidAudioError(
                f"Invalid audio request: {getattr(err, 'message', 'Bad request')}"
            ) from None
        except groq.APIStatusError as err:
            logger.error("Groq API returned error status %s", err.status_code)
            raise TranscriptionError(
                f"Groq API error (status {err.status_code}): {getattr(err, 'message', 'API error')}"
            ) from None
        except groq.GroqError as err:
            logger.error("Groq SDK error: %s", type(err).__name__)
            raise TranscriptionError(f"Groq SDK error: {type(err).__name__}") from None
        except Exception as err:
            logger.error("Unexpected error during transcription: %s", type(err).__name__)
            raise TranscriptionError(f"Unexpected transcription error: {type(err).__name__}") from None

        # Validate response content
        text = getattr(response, "text", None)
        if text is None or not isinstance(text, str) or not text.strip():
            logger.warning("Groq returned empty or invalid transcription text.")
            raise TranscriptionResponseError(
                "Empty or invalid transcription response received from Groq API."
            )

        return text.strip()


# ---------------------------------------------------------------------------
# Module-level Convenience Functions
# ---------------------------------------------------------------------------

_default_service: GroqTranscriptionService | None = None


def get_transcription_service() -> GroqTranscriptionService:
    """Dependency provider for GroqTranscriptionService."""
    global _default_service
    if _default_service is None:
        _default_service = GroqTranscriptionService()
    return _default_service


async def transcribe_audio(
    audio_data: AudioInputType,
    filename: str = "audio.wav",
    *,
    language: str | None = None,
    prompt: str | None = None,
    service: GroqTranscriptionService | None = None,
) -> str:
    """Convenience helper to transcribe audio with the default or provided service."""
    svc = service or get_transcription_service()
    return await svc.transcribe(
        audio_data=audio_data,
        filename=filename,
        language=language,
        prompt=prompt,
    )

