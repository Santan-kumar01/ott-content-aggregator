import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db, settings
from src.schemas.title import TitleRead
from src.schemas.voice import TranscriptionResponse, VoiceSearchResponse
from src.services import cache_service, catalog_service
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


async def _read_and_validate_audio_file(file: UploadFile) -> tuple[bytes, str]:
    """Validate and buffer an uploaded audio file.

    Enforces non-empty filename, size boundaries, and audio magic-byte signatures.
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

    return audio_bytes, file.filename


def _handle_transcription_exception(exc: BaseException) -> None:
    """Map transcription exceptions to standard, secure HTTP responses without leaking credentials."""
    # Never swallow control-flow, cancellation, or existing HTTP exceptions
    if isinstance(exc, (HTTPException, asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
        raise exc

    if isinstance(exc, TranscriptionConfigurationError):
        logger.error("Voice transcription failed: missing server-side configuration.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice transcription service is currently unavailable due to missing server configuration.",
        ) from None
    elif isinstance(exc, TranscriptionAuthenticationError):
        logger.error("Voice transcription failed: upstream authentication error.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication failed with the upstream transcription provider.",
        ) from None
    elif isinstance(exc, TranscriptionRateLimitError):
        logger.warning("Voice transcription failed: upstream rate limit reached.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Voice transcription rate limit or quota exceeded. Please try again later.",
        ) from None
    elif isinstance(exc, TranscriptionTimeoutError):
        logger.warning("Voice transcription failed: upstream provider timed out.")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Voice transcription request timed out with the upstream provider.",
        ) from None
    elif isinstance(exc, TranscriptionConnectionError):
        logger.warning("Voice transcription failed: unable to connect to upstream provider.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to connect to the upstream transcription provider.",
        ) from None
    elif isinstance(exc, TranscriptionInvalidAudioError):
        logger.info("Voice transcription rejected invalid audio: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio payload rejected by transcription service.",
        ) from None
    elif isinstance(exc, TranscriptionResponseError):
        logger.error("Voice transcription upstream returned empty or invalid text.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream transcription provider returned an empty or invalid response.",
        ) from None
    elif isinstance(exc, TranscriptionError):
        logger.error("Voice transcription encountered unexpected provider error.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An error occurred while communicating with the transcription provider.",
        ) from None
    else:
        logger.error("Unexpected error during voice transcription: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An error occurred while communicating with the transcription provider.",
        ) from None


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

    Preserves exact backward compatibility with the Task 3 endpoint contract.
    """
    audio_bytes, filename = await _read_and_validate_audio_file(file)

    try:
        transcription_text = await transcription_service.transcribe(
            audio_data=audio_bytes,
            filename=filename,
        )
        return TranscriptionResponse(text=transcription_text)
    except Exception as exc:
        _handle_transcription_exception(exc)


@router.post(
    "/search",
    response_model=VoiceSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Voice catalog search",
    description=(
        "Accepts an uploaded audio query (WAV, MP3, M4A, FLAC, OGG, or WebM), "
        "transcribes the speech using Groq, deterministically parses the intent and filters, "
        "and queries the catalog for matching titles."
    ),
)
async def voice_search_endpoint(
    file: Annotated[UploadFile, File(description="Audio query file to search catalog.")],
    db: Annotated[AsyncSession, Depends(get_db)],
    transcription_service: Annotated[GroqTranscriptionService, Depends(get_transcription_service)],
    query_parser: Annotated[QueryParserService, Depends(get_query_parser_service)],
    skip: int = Query(default=0, ge=0, description="Number of matching titles to skip."),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of titles to return."),
) -> VoiceSearchResponse:
    """Execute end-to-end voice search across the title catalog.

    Transcribes the uploaded audio query, deterministically extracts search filters and intent,
    and returns matching catalog titles with streaming platform availability.
    """
    audio_bytes, filename = await _read_and_validate_audio_file(file)

    try:
        transcription_text = await transcription_service.transcribe(
            audio_data=audio_bytes,
            filename=filename,
        )
    except Exception as exc:
        _handle_transcription_exception(exc)

    # Handle empty or whitespace-only transcript safely
    if not transcription_text or not transcription_text.strip():
        empty_query = query_parser.parse("")
        return VoiceSearchResponse(
            transcription=transcription_text or "",
            parsed_query=empty_query,
            titles=[],
            count=0,
            total=0,
        )

    parsed = query_parser.parse(transcription_text)

    # If parsed intent is empty or no valid search criteria, return empty result safely
    if parsed.intent == "empty":
        return VoiceSearchResponse(
            transcription=transcription_text,
            parsed_query=parsed,
            titles=[],
            count=0,
            total=0,
        )

    filters = parsed.to_catalog_filters()

    # Query catalog using existing catalog service with caching
    cached = None
    try:
        cached = await cache_service.get_catalog_list(
            genre=filters.get("genre"),
            platform=filters.get("platform"),
            search=filters.get("search"),
            release_year=filters.get("release_year"),
            skip=skip,
            limit=limit,
        )
    except Exception as cache_err:
        logger.warning("Cache lookup failed during voice search: %s", type(cache_err).__name__)
        cached = None

    if cached is not None:
        title_reads = [TitleRead.model_validate(c) for c in cached]
    else:
        try:
            db_titles = await catalog_service.list_titles(
                db=db,
                genre=filters.get("genre"),
                platform=filters.get("platform"),
                search=filters.get("search"),
                release_year=filters.get("release_year"),
                skip=skip,
                limit=limit,
            )
            title_reads = [TitleRead.model_validate(t) for t in db_titles]
        except Exception as db_exc:
            logger.error("Catalog search failed during voice search: %s", type(db_exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while querying the catalog.",
            ) from None

        try:
            serialized = [t.model_dump(mode="json") for t in title_reads]
            await cache_service.set_catalog_list(
                data=serialized,
                genre=filters.get("genre"),
                platform=filters.get("platform"),
                search=filters.get("search"),
                release_year=filters.get("release_year"),
                skip=skip,
                limit=limit,
            )
        except Exception as cache_write_err:
            logger.warning("Failed to populate catalog cache in voice search: %s", type(cache_write_err).__name__)

    # Apply content_type filtering if explicitly specified in voice query (e.g. "movies" or "shows")
    if parsed.content_type:
        title_reads = [
            t
            for t in title_reads
            if t.content_type.lower() == parsed.content_type.lower()
        ]

    return VoiceSearchResponse(
        transcription=transcription_text,
        parsed_query=parsed,
        titles=title_reads,
        count=len(title_reads),
        total=len(title_reads),
    )
