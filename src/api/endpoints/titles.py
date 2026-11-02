
import uuid
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.user import User
from src.schemas.error import ErrorResponse
from src.schemas.sync import SyncRequest, SyncTaskResponse, SyncTaskStatus
from src.schemas.title import PaginatedTitleRead, TitleCreate, TitleRead, TitleUpdate
from src.services import cache_service, catalog_service
from src.services.background_tasks import (
    get_background_task_status,
    register_background_task,
    sync_title_from_external_provider_task,
)

router = APIRouter(prefix="/titles", tags=["Catalog"])

DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "",
    response_model=TitleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a catalog title",
    description="Add a movie or show to the catalog. Authentication is required.",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication is required",
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid title data",
        },
    },
)
async def create_title(
    data: TitleCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.create_title(db, data)
    await cache_service.invalidate_catalog()
    return title


def _title_query_parameters(
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: Literal["name", "release_year", "created_at"] | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    skip: int = 0,
    limit: int = 20,
):
    return {
        "genre": genre,
        "platform": platform,
        "search": search,
        "release_year": release_year,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "",
    response_model=list[TitleRead],
    summary="List and search catalog titles",
    description=(
        "List catalog titles with optional genre, platform, release-year, "
        "and case-insensitive title-name search filters. Supports sorting "
        "and offset-based pagination."
    ),
)
async def list_titles(
    db: DBSession,
    genre: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Case-insensitive partial match against the title name.",
    ),
    release_year: int | None = Query(default=None, ge=1888, le=2100),
    sort_by: Literal["name", "release_year", "created_at"] | None = Query(
        default=None
    ),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    params = _title_query_parameters(
        genre, platform, search, release_year, sort_by, sort_order, skip, limit
    )
    cached = await cache_service.get_catalog_list(**params)
    if cached is not None:
        return cached

    titles = await catalog_service.list_titles(db, **params)
    serialized = [
        TitleRead.model_validate(title).model_dump(mode="json")
        for title in titles
    ]
    await cache_service.set_catalog_list(data=serialized, **params)
    return titles


@router.get(
    "/paginated",
    response_model=PaginatedTitleRead,
    summary="List catalog titles with pagination metadata",
    description=(
        "List catalog titles with optional filters and case-insensitive "
        "title-name search. Returns items, total matching records, skip, "
        "limit, and has_next to indicate whether another page is available."
    ),
)
async def list_titles_paginated(
    db: DBSession,
    genre: str | None = Query(default=None),
    platform: str | None = Query(default=None),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
        description="Case-insensitive partial match against the title name.",
    ),
    release_year: int | None = Query(default=None, ge=1888, le=2100),
    sort_by: Literal["name", "release_year", "created_at"] | None = Query(
        default=None
    ),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    params = _title_query_parameters(
        genre, platform, search, release_year, sort_by, sort_order, skip, limit
    )
    cached = await cache_service.get_catalog_paginated(**params)
    if cached is not None:
        return cached

    items, total = await catalog_service.list_titles_paginated(db, **params)
    response_payload = {
        "items": [
            TitleRead.model_validate(item).model_dump(mode="json")
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_next": skip + len(items) < total,
    }
    await cache_service.set_catalog_paginated(data=response_payload, **params)
    return response_payload


@router.get(
    "/sync/tasks/{task_id}",
    response_model=SyncTaskStatus,
    summary="Check background task status",
)
async def get_sync_task_status(
    task_id: Annotated[str, Path(description="The unique UUID of the background task")],
):
    task_info = get_background_task_status(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Background task not found")
    return task_info


@router.get(
    "/{title_id}",
    response_model=TitleRead,
    summary="Get a catalog title",
    responses={
        404: {"model": ErrorResponse, "description": "Title not found"},
    },
)
async def get_title(
    title_id: Annotated[int, Path(gt=0)],
    db: DBSession,
):
    cached = await cache_service.get_title(title_id)
    if cached is not None:
        return cached

    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Title not found",
        )

    serialized = TitleRead.model_validate(title).model_dump(mode="json")
    await cache_service.set_title(title_id, serialized)
    return title


@router.patch(
    "/{title_id}",
    response_model=TitleRead,
    summary="Update a catalog title",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication is required"},
        404: {"model": ErrorResponse, "description": "Title not found"},
        422: {"model": ErrorResponse, "description": "Invalid title data"},
    },
)
async def update_title(
    title_id: Annotated[int, Path(gt=0)],
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

    updated_title = await catalog_service.update_title(db, title, data)
    await cache_service.invalidate_catalog(title_id=title_id)
    return updated_title


@router.delete(
    "/{title_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a catalog title",
    description="Delete an existing title. Authentication is required.",
    responses={
        401: {"model": ErrorResponse, "description": "Authentication is required"},
        404: {"model": ErrorResponse, "description": "Title not found"},
    },
)
async def delete_title(
    title_id: Annotated[int, Path(gt=0)],
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
    await cache_service.invalidate_catalog(title_id=title_id)


@router.post(
    "/{title_id}/sync",
    response_model=SyncTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue background external metadata sync",
)
async def sync_title_metadata(
    title_id: Annotated[int, Path(gt=0)],
    background_tasks: BackgroundTasks,
    db: DBSession,
    current_user: CurrentUser,
    sync_data: SyncRequest | None = None,
):
    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")

    task_id = str(uuid.uuid4())
    register_background_task(task_id, title_id)
    background_tasks.add_task(
        sync_title_from_external_provider_task,
        task_id=task_id,
        title_id=title_id,
        external_id=sync_data.external_id if sync_data else None,
        provider=sync_data.provider if sync_data else None,
    )
    return {
        "task_id": task_id,
        "title_id": title_id,
        "status": "queued",
        "message": "Title synchronization queued in background",
    }
