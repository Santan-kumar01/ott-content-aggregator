from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard FastAPI-compatible error response."""

    detail: str | dict | list = Field(
        description="Human-readable error detail or validation information."
    )
