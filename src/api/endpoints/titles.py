from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
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
from src.services import cache_service, catalog_service

router = APIRouter(prefix="/titles", tags=["Catalog"])

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=TitleRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_title(
    data: TitleCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.create_title(db, data)
    await cache_service.invalidate_catalog()
    return title


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
    cached = await cache_service.get_catalog_list(
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    if cached is not None:
        return cached

    titles = await catalog_service.list_titles(
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
    serialized = [
        TitleRead.model_validate(t).model_dump(mode="json") for t in titles
    ]
    await cache_service.set_catalog_list(
        data=serialized,
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    return titles


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
    cached = await cache_service.get_catalog_paginated(
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    if cached is not None:
        return cached

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

    response_payload = {
        "items": [
            TitleRead.model_validate(t).model_dump(mode="json") for t in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_next": skip + len(items) < total,
    }
    await cache_service.set_catalog_paginated(
        data=response_payload,
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    return response_payload


@router.get("/{title_id}", response_model=TitleRead)
async def get_title(
    title_id: Annotated[int, Path(gt=0, description="The ID of the title to retrieve")],
    db: DBSession,
):
    cached = await cache_service.get_title(title_id)
    if cached is not None:
        return cached

    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")

    serialized = TitleRead.model_validate(title).model_dump(mode="json")
    await cache_service.set_title(title_id, serialized)
    return title


@router.patch("/{title_id}", response_model=TitleRead)
async def update_title(
    title_id: Annotated[int, Path(gt=0, description="The ID of the title to update")],
    data: TitleUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")
    updated_title = await catalog_service.update_title(db, title, data)
    await cache_service.invalidate_catalog(title_id=title_id)
    return updated_title


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_title(
    title_id: Annotated[int, Path(gt=0, description="The ID of the title to delete")],
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")
    await catalog_service.delete_title(db, title)
    await cache_service.invalidate_catalog(title_id=title_id)
