from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    """Optional payload to customize title synchronization."""
    external_id: str | None = Field(
        default=None,
        description="External provider identifier for the title.",
        examples=["ext-movie-12345"],
    )
    provider: str | None = Field(
        default=None,
        description="Name of the streaming provider (e.g., netflix, prime).",
        examples=["netflix"],
    )


class SyncTaskResponse(BaseModel):
    """Response returned immediately when a background sync task is queued."""
    task_id: str = Field(description="Unique identifier for the background task.")
    title_id: int = Field(description="ID of the catalog title being synced.")
    status: Literal["queued", "in_progress", "completed", "failed"] = "queued"
    message: str = Field(description="Informational message about task status.")


class SyncTaskStatus(BaseModel):
    """Status details of a queued, executing, or completed background task."""
    task_id: str
    title_id: int
    status: Literal["pending", "in_progress", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class ExternalTitleMetadata(BaseModel):
    """Validated schema for external provider title metadata."""
    external_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    content_type: Literal["movie", "show"] | None = None
    release_year: int | None = Field(default=None, ge=1888, le=2100)
    genre: str | None = Field(default=None, max_length=100)
    platform: str | None = Field(default=None, max_length=100)
    extra_metadata: dict[str, Any] | None = None
