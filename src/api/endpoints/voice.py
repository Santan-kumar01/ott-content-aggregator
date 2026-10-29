import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.core.database import settings
from src.schemas.voice import TranscriptionResponse
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

logger = logging.getLogger("src.api.endpoints.voice")

router = APIRouter(prefix="/voice", tags=["Voice"])

CHUNK_SIZE = 64 * 1024  # 64 KB streaming chunk size


HTTP_413_TOO_LARGE = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", None) or 413


def is_valid_audio_payload(data: bytes) -> bool:
    """Inspect magic numbers/file signatures to verify recognized audio format.

    Validates audio without relying solely on client-supplied extension or MIME type.
    Supports WAV, MP3 (with ID3 tag or sync word), OGG, FLAC, MP4/M4A, WebM/Matroska, and AAC.
    """
    if len(data) < 4:
        return False

    # 1. WAV: starts with 'RIFF' and bytes 8..12 are 'WAVE'
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return True

    # 2. OGG container (Vorbis / Opus)
    if data.startswith(b"OggS"):
        return True

    # 3. FLAC
    if data.startswith(b"fLaC"):
        return True

    # 4. MP3 with ID3v2 container
    if data.startswith(b"ID3"):
        return True

    # 5. MP3 raw sync word (MPEG audio frame sync: 11 bits set = 0xFF followed by 0xE0 mask)
    if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return True

    # 6. MP4 / M4A: ISO base media file format containing 'ftyp' in header
    if len(data) >= 12 and b"ftyp" in data[:16]:
        return True

    # 7. WebM / Matroska: EBML ID \x1a\x45\xdf\xa3
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    return False


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe uploaded audio file",
    description=(
        "Accepts an uploaded audio file (WAV, MP3, M4A, FLAC, OGG, or WebM) "
        "and returns the normalized transcription text via Groq Speech-to-Text."
    ),
)
async def transcribe_audio_endpoint(
    file: Annotated[UploadFile, File(description="Audio file to transcribe.")],
    transcription_service: Annotated[GroqTranscriptionService, Depends(get_transcription_service)],
) -> TranscriptionResponse:
    """Validate and transcribe an uploaded audio file.

    Enforces size boundaries, verifies audio format header signatures,
    and maps upstream provider exceptions to clear, safe HTTP responses.
    """
    if not file or not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a valid filename.",
        )

    max_size = getattr(settings, "max_voice_upload_bytes", 10 * 1024 * 1024)
    chunks: list[bytes] = []
    total_size = 0

    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_size:
                raise HTTPException(
                    status_code=HTTP_413_TOO_LARGE,
                    detail=f"Audio file exceeds the maximum allowed size of {max_size} bytes.",
                )
            chunks.append(chunk)
    finally:
        await file.close()

    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty.",
        )

    audio_bytes = b"".join(chunks)

    # Validate header signature / magic bytes
    if not is_valid_audio_payload(audio_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported or invalid audio format. Supported formats include WAV, MP3, M4A, FLAC, OGG, and WebM.",
        )

    try:
        transcription_text = await transcription_service.transcribe(
            audio_data=audio_bytes,
            filename=file.filename,
        )
        return TranscriptionResponse(text=transcription_text)

    except TranscriptionConfigurationError:
        logger.error("Voice transcription failed: missing server-side configuration.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transcription service is currently unavailable due to missing server configuration.",
        ) from None

    except TranscriptionAuthenticationError:
        logger.error("Voice transcription failed: upstream authentication error.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication failed with the upstream transcription provider.",
        ) from None

    except TranscriptionRateLimitError:
        logger.warning("Voice transcription failed: upstream rate limit reached.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Voice transcription rate limit or quota exceeded. Please try again later.",
        ) from None

    except TranscriptionTimeoutError:
        logger.warning("Voice transcription failed: upstream provider timed out.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Voice transcription request timed out with the upstream provider.",
        ) from None

    except TranscriptionConnectionError:
        logger.warning("Voice transcription failed: unable to connect to upstream provider.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to the upstream transcription provider.",
        ) from None

    except TranscriptionInvalidAudioError as err:
        logger.info("Voice transcription rejected invalid audio: %s", type(err).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio payload rejected by transcription service.",
        ) from None

    except TranscriptionResponseError:
        logger.error("Voice transcription upstream returned empty or invalid text.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream transcription provider returned an empty or invalid response.",
        ) from None

    except TranscriptionError:
        logger.error("Voice transcription encountered unexpected provider error.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An error occurred while communicating with the transcription provider.",
        ) from None
