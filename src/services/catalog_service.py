
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.title import Title
from src.schemas.title import TitleCreate, TitleUpdate


async def create_title(
    db: AsyncSession, data: TitleCreate
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
    release_year: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Title]:
    query = select(Title)

    if genre:
        query = query.where(Title.genre.ilike(genre))

    if platform:
        query = query.where(Title.platform.ilike(platform))

    if release_year is not None:
        query = query.where(Title.release_year == release_year)

    query = query.order_by(Title.id).offset(skip).limit(limit)
    result = await db.scalars(query)
    return list(result.all())


async def get_title(
    db: AsyncSession, title_id: int
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
    db: AsyncSession, title: Title
) -> None:
    await db.delete(title)
    await db.commit()
