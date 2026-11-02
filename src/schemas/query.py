from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParsedQuery(BaseModel):
    """Structured representation of a natural language query for catalog search."""

    model_config = ConfigDict(frozen=True)

    raw_query: str = Field(
        ...,
        description="Original query string provided as input.",
    )
    cleaned_query: str = Field(
        ...,
        description="Cleaned, normalized query string with command prefixes and trailing noise stripped.",
    )
    search_query: str | None = Field(
        default=None,
        description="Title or text keywords suitable for passing to catalog search.",
    )
    genre: str | None = Field(
        default=None,
        description="Normalized genre name if detected in the query.",
    )
    platform: str | None = Field(
        default=None,
        description="Streaming platform if detected in the query (e.g. Netflix, Prime).",
    )
    release_year: int | None = Field(
        default=None,
        description="Release year if explicitly specified in the query.",
    )
    content_type: str | None = Field(
        default=None,
        description="Detected media content type ('movie' or 'show') if specified.",
    )
    is_similarity: bool = Field(
        default=False,
        description="True if the user requested titles similar to a target title.",
    )
    similar_to: str | None = Field(
        default=None,
        description="Target title referenced for similarity recommendation, if applicable.",
    )
    intent: str = Field(
        default="search",
        description="Primary query intent: 'search', 'genre_search', 'similar', 'browse', or 'empty'.",
    )

    def to_catalog_filters(self) -> dict[str, Any]:
        """Convert parsed query to keyword arguments compatible with catalog_service.list_titles()."""
        filters: dict[str, Any] = {}
        if self.search_query:
            filters["search"] = self.search_query
        if self.genre:
            filters["genre"] = self.genre
        if self.platform:
            filters["platform"] = self.platform
        if self.release_year is not None:
            filters["release_year"] = self.release_year
        return filters

