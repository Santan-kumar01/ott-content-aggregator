from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.endpoints.auth import get_current_user
from src.core.database import get_db
from src.models.user import User
from src.schemas.title import TitleCreate, TitleRead, TitleUpdate
from src.services import catalog_service

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
    return await catalog_service.create_title(db, data)


@router.get("", response_model=list[TitleRead])
async def list_titles(
    db: DBSession,
    genre: str | None = None,
    platform: str | None = None,
    release_year: int | None = Query(
        default=None, ge=1888, le=2100
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    return await catalog_service.list_titles(
        db,
        genre=genre,
        platform=platform,
        release_year=release_year,
        skip=skip,
        limit=limit,
    )


@router.get("/{title_id}", response_model=TitleRead)
async def get_title(title_id: int, db: DBSession):
    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")
    return title


@router.put("/{title_id}", response_model=TitleRead)
async def update_title(
    title_id: int,
    data: TitleUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")
    return await catalog_service.update_title(db, title, data)


@router.delete("/{title_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_title(
    title_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    title = await catalog_service.get_title(db, title_id)
    if title is None:
        raise HTTPException(status_code=404, detail="Title not found")
    await catalog_service.delete_title(db, title)
