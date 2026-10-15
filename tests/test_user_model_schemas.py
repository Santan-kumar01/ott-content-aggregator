from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import Boolean, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.models.user import User
from src.schemas.user import Token, TokenPayload, UserCreate, UserRead


# ---------------------------------------------------------------------------
# User Model Tests
# ---------------------------------------------------------------------------


def test_user_model_table_definition():
    assert User.__tablename__ == "users"
    assert "users" in Base.metadata.tables

    columns = User.__table__.columns

    # Verify column existence
    assert "id" in columns
    assert "email" in columns
    assert "username" in columns
    assert "hashed_password" in columns
    assert "is_active" in columns
    assert "is_superuser" in columns
    assert "created_at" in columns

    # Verify column constraints and types
    assert columns["id"].primary_key is True
    assert isinstance(columns["id"].type, Integer)

    assert columns["email"].unique is True
    assert columns["email"].index is True
    assert columns["email"].nullable is False
    assert isinstance(columns["email"].type, String)
    assert columns["email"].type.length == 255

    assert columns["username"].index is True
    assert columns["username"].nullable is False
    assert isinstance(columns["username"].type, String)

    assert columns["hashed_password"].nullable is False
    assert isinstance(columns["hashed_password"].type, String)

    assert columns["is_active"].nullable is False
    assert isinstance(columns["is_active"].type, Boolean)
    assert columns["is_active"].default.arg is True

    assert columns["is_superuser"].nullable is False
    assert isinstance(columns["is_superuser"].type, Boolean)
    assert columns["is_superuser"].default.arg is False

    assert columns["created_at"].nullable is False
    assert isinstance(columns["created_at"].type, DateTime)


@pytest.mark.anyio
async def test_user_model_async_persistence():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="$2b$12$somevalidhashsample1234567890",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None

        # Query user back from database
        result = await session.execute(
            select(User).where(User.email == "test@example.com")
        )
        queried_user = result.scalar_one()
        assert queried_user.id == user.id
        assert queried_user.username == "testuser"

    await engine.dispose()


# ---------------------------------------------------------------------------
# UserCreate Schema Tests
# ---------------------------------------------------------------------------


def test_user_create_valid():
    user_in = UserCreate(
        email="test@example.com",
        username="johndoe",
        password="MySecretPassword123!",
    )
    assert user_in.email == "test@example.com"
    assert user_in.username == "johndoe"
    assert user_in.password == "MySecretPassword123!"


def test_user_create_invalid_email():
    invalid_emails = [
        "notanemail",
        "missingatsign.com",
        "@missinguser.com",
        "user@.com",
        "",
    ]
    for email in invalid_emails:
        with pytest.raises(ValidationError):
            UserCreate(
                email=email,
                username="validuser",
                password="validpassword123",
            )


def test_user_create_password_min_length():
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            username="validuser",
            password="short",  # < 8 characters
        )


def test_user_create_password_max_length():
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            username="validuser",
            password="a" * 73,  # > 72 characters
        )


def test_user_create_password_utf8_boundary():
    # 20 emojis = 80 bytes in UTF-8
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            username="validuser",
            password="🔒" * 20,
        )

    # 18 emojis = 72 bytes in UTF-8 -> succeeds
    user = UserCreate(
        email="test@example.com",
        username="validuser",
        password="🔒" * 18,
    )
    assert len(user.password.encode("utf-8")) == 72


def test_user_create_missing_fields():
    with pytest.raises(ValidationError):
        UserCreate(email="test@example.com", username="validuser")  # missing password

    with pytest.raises(ValidationError):
        UserCreate(username="validuser", password="validpassword123")  # missing email


# ---------------------------------------------------------------------------
# UserRead Schema Tests
# ---------------------------------------------------------------------------


def test_user_read_valid_from_dict():
    now = datetime.now(timezone.utc)
    user_data = {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
    }
    user_read = UserRead.model_validate(user_data)
    assert user_read.id == 1
    assert user_read.email == "test@example.com"
    assert user_read.username == "testuser"
    assert user_read.is_active is True
    assert user_read.is_superuser is False
    assert user_read.created_at == now

    # Ensure hashed_password is not present in dumped data or model fields
    dumped = user_read.model_dump()
    assert "hashed_password" not in dumped
    assert "password" not in dumped
    assert not hasattr(user_read, "hashed_password")


def test_user_read_never_exposes_hashed_password():
    now = datetime.now(timezone.utc)

    class MockUserORM:
        id = 42
        email = "secure@example.com"
        username = "secureuser"
        hashed_password = "$2b$12$SuperSecretHashedPasswordNeverLeakMe"
        is_active = True
        is_superuser = False
        created_at = now

    mock_user = MockUserORM()
    user_read = UserRead.model_validate(mock_user)

    dumped = user_read.model_dump()
    assert "hashed_password" not in dumped
    assert not hasattr(user_read, "hashed_password")
    assert user_read.email == "secure@example.com"
    assert user_read.id == 42


# ---------------------------------------------------------------------------
# Token & TokenPayload Schema Tests
# ---------------------------------------------------------------------------


def test_token_schema_default_and_custom_type():
    token1 = Token(access_token="sample.jwt.token")
    assert token1.access_token == "sample.jwt.token"
    assert token1.token_type == "bearer"

    token2 = Token(access_token="sample.jwt.token", token_type="Bearer")
    assert token2.token_type == "Bearer"


def test_token_payload_schema():
    payload = TokenPayload(sub="123", exp=1700000000, iat=1699990000)
    assert payload.sub == "123"
    assert payload.exp == 1700000000
    assert payload.iat == 1699990000


def test_token_payload_coerces_int_subject_to_str():
    payload = TokenPayload(sub=456)
    assert payload.sub == "456"
    assert isinstance(payload.sub, str)


def test_token_payload_ignores_extra_claims():
    data = {
        "sub": "789",
        "exp": 1700000000,
        "custom_claim": "custom_value",
    }
    payload = TokenPayload.model_validate(data)
    assert payload.sub == "789"
    assert payload.exp == 1700000000
