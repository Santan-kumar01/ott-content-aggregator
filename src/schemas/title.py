
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TitleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(
        default=None, max_length=2000
    )
    content_type: Literal["movie", "show"]
    release_year: int = Field(ge=1888, le=2100)
    genre: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=100)


class TitleUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=200
    )
    description: str | None = Field(
        default=None, max_length=2000
    )
    content_type: Literal["movie", "show"] | None = None
    release_year: int | None = Field(
        default=None, ge=1888, le=2100
    )
    genre: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    platform: str | None = Field(
        default=None, min_length=1, max_length=100
    )


class TitleRead(BaseModel):
    id: int
    name: str
    description: str | None
    content_type: str
    release_year: int
    genre: str
    platform: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTitleRead(BaseModel):
    items: list[TitleRead]
    total: int
    skip: int
    limit: int
    has_next: bool
