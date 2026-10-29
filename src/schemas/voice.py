from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Response payload containing the transcribed text from uploaded audio."""

    text: str = Field(..., description="Normalized transcribed text from the audio input.")
