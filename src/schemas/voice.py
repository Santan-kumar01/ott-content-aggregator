from pydantic import BaseModel, Field

from src.schemas.query import ParsedQuery
from src.schemas.title import TitleRead


class TranscriptionResponse(BaseModel):
    """Response payload containing the transcribed text from uploaded audio."""

    text: str = Field(..., description="Normalized transcribed text from the audio input.")


class VoiceSearchResponse(BaseModel):
    """Response payload for voice catalog search combining transcription, parsed query, and catalog results."""

    transcription: str = Field(
        ...,
        description="Raw transcribed text from the audio input.",
    )
    parsed_query: ParsedQuery = Field(
        ...,
        description="Structured representation of the parsed search query.",
    )
    titles: list[TitleRead] = Field(
        default_factory=list,
        description="Matching catalog titles found for the query.",
    )
    count: int = Field(
        default=0,
        description="Number of matching titles returned in this response.",
    )
    total: int = Field(
        default=0,
        description="Total number of matching titles found.",
    )
