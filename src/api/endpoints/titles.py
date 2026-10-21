from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.user import User
from src.schemas.title import (
    PaginatedTitleRead,
    TitleCreate,
    TitleRead,
    TitleUpdate,
)
from src.services import catalog_service

router = APIRouter(
    prefix="/titles",
    tags=["Catalog"],
)

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=TitleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a catalog title",
    description=(
        "Add a movie or show to the catalog. "
        "Authentication is required."
    ),
    responses={
        401: {"description": "Authentication is required"},
        422: {"description": "Invalid title data"},
    },
)
async def create_title(
    data: TitleCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    return await catalog_service.create_title(db, data)


@router.get(
    "",
    response_model=list[TitleRead],
    summary="List and search catalog titles",
    description=(
        "Retrieve catalog titles with optional case-insensitive "
        "search, genre, platform, and release-year filters. "
        "Supports sorting and offset-based pagination. "
        "Returns a list without pagination metadata."
    ),
)
async def list_titles(
    db: DBSession,
    genre: str | None = Query(
        default=None,
        description="Filter titles by genre.",
    ),
    platform: str | None = Query(
        default=None,
        description="Filter titles by streaming platform.",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description=(
            "Case-insensitive partial match in title name "
            "or description."
        ),
        examples=["inception"],
    ),
    release_year: int | None = Query(
        default=None,
        ge=1888,
        le=2100,
        description="Filter by release year (1888–2100).",
    ),
    sort_by: Literal[
        "name", "release_year", "created_at"
    ] | None = Query(
        default=None,
        description="Optional field used to sort titles.",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="asc",
        description="Sort direction: ascending or descending.",
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of matching titles to skip.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of titles to return (1–100).",
    ),
):
    return await catalog_service.list_titles(
        db,
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/paginated",
    response_model=PaginatedTitleRead,
    summary="List catalog titles with pagination metadata",
    description=(
        "Retrieve filtered and sorted catalog titles along with "
        "the total number of matching records and a has_next flag."
    ),
)
async def list_titles_paginated(
    db: DBSession,
    genre: str | None = Query(
        default=None,
        description="Filter titles by genre.",
    ),
    platform: str | None = Query(
        default=None,
        description="Filter titles by streaming platform.",
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description=(
            "Case-insensitive partial match in title name "
            "or description."
        ),
        examples=["inception"],
    ),
    release_year: int | None = Query(
        default=None,
        ge=1888,
        le=2100,
        description="Filter by release year (1888–2100).",
    ),
    sort_by: Literal[
        "name", "release_year", "created_at"
    ] | None = Query(
        default=None,
        description="Optional field used to sort titles.",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        default="asc",
        description="Sort direction: ascending or descending.",
    ),
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of matching titles to skip.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of titles to return (1–100).",
    ),
):
    items, total = await catalog_service.list_titles_paginated(
        db,
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_next": skip + len(items) < total,
    }


@router.get(
    "/{title_id}",
    response_model=TitleRead,
    summary="Get a catalog title",
    description="Retrieve a single title by its ID.",
    responses={
        404: {"description": "Title not found"},
    },
)
async def get_title(title_id: int, db: DBSession):
    title = await catalog_service.get_title(db, title_id)

    if title is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Title not found",
        )

    return title


@router.put(
    "/{title_id}",
    response_model=TitleRead,
    summary="Update a catalog title",
    description="Update an existing title. Authentication is required.",
    responses={
        401: {"description": "Authentication is required"},
        404: {"description": "Title not found"},
        422: {"description": "Invalid title data"},
    },
)
async def update_title(
    title_id: int,
    data: TitleUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.get_title(db, title_id)

    if title is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Title not found",
        )

    return await catalog_service.update_title(db, title, data)


@router.delete(
    "/{title_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a catalog title",
    description="Delete an existing title. Authentication is required.",
    responses={
        401: {"description": "Authentication is required"},
        404: {"description": "Title not found"},
    },
)
async def delete_title(
    title_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.get_title(db, title_id)

    if title is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Title not found",
        )

    await catalog_service.delete_title(db, title)
