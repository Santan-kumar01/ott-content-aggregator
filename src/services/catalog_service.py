
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.title import Title
from src.services.outbox_service import enqueue_catalog_invalidation
from src.schemas.title import TitleCreate, TitleUpdate


def _build_title_filters(
    search: str | None,
    genre: str | Sequence[str] | None,
    platform: str | Sequence[str] | None,
    release_year: int | None,
    content_type: str | None = None,
    release_year_from: int | None = None,
    release_year_to: int | None = None,
):
    filters = []

    if search:
        search = search.strip()

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
        genres = [genre] if isinstance(genre, str) else genre
        filters.append(or_(*(Title.genre.ilike(value) for value in genres)))

    if platform:
        platforms = [platform] if isinstance(platform, str) else platform
        filters.append(
            or_(*(Title.platform.ilike(value) for value in platforms))
        )

    if release_year is not None:
        filters.append(Title.release_year == release_year)

    if release_year_from is not None:
        filters.append(Title.release_year >= release_year_from)

    if release_year_to is not None:
        filters.append(Title.release_year <= release_year_to)

    if content_type is not None:
        filters.append(Title.content_type == content_type)

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
    try:
        await db.flush()
        enqueue_catalog_invalidation(db, title.id, "create")
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(title)
    return title


async def list_titles(
    db: AsyncSession,
    genre: str | Sequence[str] | None = None,
    platform: str | Sequence[str] | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = None,
    release_year_from: int | None = None,
    release_year_to: int | None = None,
) -> list[Title]:
    query = select(Title)
    filters = _build_title_filters(
        search,
        genre,
        platform,
        release_year,
        content_type,
        release_year_from,
        release_year_to,
    )
    if filters:
        query = query.where(*filters)

    query = _apply_title_sorting(query, sort_by, sort_order)
    query = query.offset(skip).limit(limit)

    result = await db.scalars(query)
    return list(result.all())


async def list_titles_paginated(
    db: AsyncSession,
    genre: str | Sequence[str] | None = None,
    platform: str | Sequence[str] | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = None,
    release_year_from: int | None = None,
    release_year_to: int | None = None,
) -> tuple[list[Title], int]:
    filters = _build_title_filters(
        search,
        genre,
        platform,
        release_year,
        content_type,
        release_year_from,
        release_year_to,
    )

    count_query = select(func.count()).select_from(Title)
    if filters:
        count_query = count_query.where(*filters)

    total = await db.scalar(count_query) or 0
    if total == 0 or skip >= total:
        return [], total

    query = select(Title)
    if filters:
        query = query.where(*filters)

    query = _apply_title_sorting(query, sort_by, sort_order)
    query = query.offset(skip).limit(limit)

    result = await db.scalars(query)
    items = list(result.all())

    return items, total


async def list_title_facets(
    db: AsyncSession,
    search: str | None = None,
    genre: str | Sequence[str] | None = None,
    platform: str | Sequence[str] | None = None,
    release_year: int | None = None,
    content_type: str | None = None,
    release_year_from: int | None = None,
    release_year_to: int | None = None,
) -> dict[str, list[dict[str, str | int]]]:
    genre_filters = _build_title_filters(
        search,
        None,
        platform,
        release_year,
        content_type,
        release_year_from,
        release_year_to,
    )
    platform_filters = _build_title_filters(
        search,
        genre,
        None,
        release_year,
        content_type,
        release_year_from,
        release_year_to,
    )

    genre_query = (
        select(Title.genre.label("value"), func.count(Title.id).label("count"))
        .where(*genre_filters)
        .group_by(Title.genre)
        .order_by(Title.genre)
    )
    platform_query = (
        select(
            Title.platform.label("value"),
            func.count(Title.id).label("count"),
        )
        .where(*platform_filters)
        .group_by(Title.platform)
        .order_by(Title.platform)
    )

    genre_result = await db.execute(genre_query)
    platform_result = await db.execute(platform_query)

    return {
        "genres": [
            {"value": row.value, "count": row.count}
            for row in genre_result
        ],
        "platforms": [
            {"value": row.value, "count": row.count}
            for row in platform_result
        ],
    }


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

    try:
        enqueue_catalog_invalidation(db, title.id, "update")
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(title)
    return title


async def delete_title(
    db: AsyncSession,
    title: Title,
) -> None:
    enqueue_catalog_invalidation(db, title.id, "delete")
    await db.delete(title)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
