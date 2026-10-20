
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.title import Title
from src.schemas.title import TitleCreate, TitleUpdate


def _build_title_filters(
    search: str | None,
    genre: str | None,
    platform: str | None,
    release_year: int | None,
):
    filters = []

    if search:
        escaped_search = (
            search.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        search_pattern = f"%{escaped_search}%"
        filters.append(
            or_(
                Title.name.ilike(search_pattern, escape="\\"),
                Title.description.ilike(search_pattern, escape="\\"),
            )
        )

    if genre:
        filters.append(Title.genre.ilike(genre))

    if platform:
        filters.append(Title.platform.ilike(platform))

    if release_year is not None:
        filters.append(Title.release_year == release_year)

    return filters


def _apply_title_sorting(
    query,
    sort_by: str | None,
    sort_order: str,
):
    if sort_by is None:
        return query.order_by(Title.id)

    sort_column = {
        "name": Title.name,
        "release_year": Title.release_year,
        "created_at": Title.created_at,
    }[sort_by]
    primary_order = (
        sort_column.asc() if sort_order == "asc" else sort_column.desc()
    )
    return query.order_by(primary_order, Title.id.asc())


async def create_title(
    db: AsyncSession,
    data: TitleCreate,
) -> Title:
    title = Title(**data.model_dump())
    db.add(title)
    await db.commit()
    await db.refresh(title)
    return title


async def list_titles(
    db: AsyncSession,
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> list[Title]:
    query = select(Title)
    filters = _build_title_filters(
        search, genre, platform, release_year
    )
    if filters:
        query = query.where(*filters)

    query = _apply_title_sorting(query, sort_by, sort_order)
    query = query.offset(skip).limit(limit)

    result = await db.scalars(query)
    return list(result.all())


async def list_titles_paginated(
    db: AsyncSession,
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Title], int]:
    filters = _build_title_filters(
        search, genre, platform, release_year
    )

    count_query = select(func.count()).select_from(Title)

    if filters:
        count_query = count_query.where(*filters)

    total = await db.scalar(count_query)

    query = select(Title)

    if filters:
        query = query.where(*filters)

    query = _apply_title_sorting(query, sort_by, sort_order)
    query = query.offset(skip).limit(limit)

    result = await db.scalars(query)
    items = list(result.all())

    return items, total or 0


async def get_title(
    db: AsyncSession,
    title_id: int,
) -> Title | None:
    return await db.get(Title, title_id)


async def update_title(
    db: AsyncSession,
    title: Title,
    data: TitleUpdate,
) -> Title:
    for field, value in data.model_dump(
        exclude_unset=True
    ).items():
        setattr(title, field, value)

    await db.commit()
    await db.refresh(title)
    return title


async def delete_title(
    db: AsyncSession,
    title: Title,
) -> None:
    await db.delete(title)
    await db.commit()