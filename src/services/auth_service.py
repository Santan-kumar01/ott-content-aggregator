from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password, verify_password
from src.models.user import User
from src.schemas.user import UserCreate


async def get_user_by_email(
    db: AsyncSession, email: str
) -> User | None:
    """Find a user by email address."""
    if not email or not isinstance(email, str):
        return None

    query = select(User).where(User.email == email)
    result = await db.scalars(query)
    return result.first()


async def register_user(
    db: AsyncSession, data: UserCreate
) -> User:
    """Register a new user, hashing their password and rejecting duplicate emails."""
    existing_user = await get_user_by_email(db, data.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> User | None:
    """Authenticate a user by verifying their email and password."""
    if not email or not password:
        return None

    user = await get_user_by_email(db, email)
    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
