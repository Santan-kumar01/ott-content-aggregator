import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.core.security import verify_password
from src.schemas.user import UserCreate
from src.services.auth_service import (
    authenticate_user,
    get_user_by_email,
    register_user,
)


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite async database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# Registration Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_user_success(db_session: AsyncSession):
    user_in = UserCreate(
        email="newuser@example.com",
        username="newuser",
        password="MySecretPassword123!",
    )
    user = await register_user(db_session, user_in)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.username == "newuser"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.created_at is not None

    # Password must be hashed and never stored as plaintext
    assert user.hashed_password != "MySecretPassword123!"
    assert user.hashed_password.startswith("$2b$")
    assert verify_password("MySecretPassword123!", user.hashed_password) is True
    assert not hasattr(user, "password")

    # User must be queryable by email
    queried_user = await get_user_by_email(db_session, "newuser@example.com")
    assert queried_user is not None
    assert queried_user.id == user.id


@pytest.mark.anyio
async def test_register_user_duplicate_email(db_session: AsyncSession):
    user_in = UserCreate(
        email="duplicate@example.com",
        username="userone",
        password="ValidPassword123!",
    )
    await register_user(db_session, user_in)

    # Attempt to register with the exact same email
    duplicate_in = UserCreate(
        email="duplicate@example.com",
        username="usertwo",
        password="DifferentPassword123!",
    )

    with pytest.raises(HTTPException) as exc_info:
        await register_user(db_session, duplicate_in)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Email already registered"


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_authenticate_user_success(db_session: AsyncSession):
    user_in = UserCreate(
        email="login_user@example.com",
        username="loginuser",
        password="CorrectPassword123!",
    )
    created_user = await register_user(db_session, user_in)

    authenticated_user = await authenticate_user(
        db_session,
        email="login_user@example.com",
        password="CorrectPassword123!",
    )

    assert authenticated_user is not None
    assert authenticated_user.id == created_user.id
    assert authenticated_user.email == "login_user@example.com"
    assert authenticated_user.username == "loginuser"


@pytest.mark.anyio
async def test_authenticate_user_incorrect_password(db_session: AsyncSession):
    user_in = UserCreate(
        email="user_pwd_test@example.com",
        username="pwdtest",
        password="CorrectPassword123!",
    )
    await register_user(db_session, user_in)

    # Wrong password attempt
    result = await authenticate_user(
        db_session,
        email="user_pwd_test@example.com",
        password="WrongPassword999!",
    )

    assert result is None


@pytest.mark.anyio
async def test_authenticate_user_unknown_email(db_session: AsyncSession):
    result = await authenticate_user(
        db_session,
        email="doesnotexist@example.com",
        password="AnyPassword123!",
    )

    assert result is None


# ---------------------------------------------------------------------------
# get_user_by_email Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_user_by_email_found(db_session: AsyncSession):
    user_in = UserCreate(
        email="lookup@example.com",
        username="lookupuser",
        password="Password123!",
    )
    created_user = await register_user(db_session, user_in)

    found = await get_user_by_email(db_session, "lookup@example.com")
    assert found is not None
    assert found.id == created_user.id
    assert found.email == "lookup@example.com"


@pytest.mark.anyio
async def test_get_user_by_email_not_found(db_session: AsyncSession):
    found = await get_user_by_email(db_session, "missing@example.com")
    assert found is None


@pytest.mark.anyio
async def test_get_user_by_email_empty_or_invalid():
    # If no valid email string is provided, safely returns None without database querying
    assert await get_user_by_email(None, "") is None  # type: ignore
    assert await get_user_by_email(None, None) is None  # type: ignore


@pytest.mark.anyio
async def test_authenticate_user_empty_credentials():
    assert await authenticate_user(None, "", "password") is None  # type: ignore
    assert await authenticate_user(None, "user@example.com", "") is None  # type: ignore
