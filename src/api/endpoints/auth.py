from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import (
    create_access_token,
    decode_access_token,
    oauth2_scheme,
    verify_password,
)
from src.models.user import User
from src.schemas.user import Token, UserCreate, UserRead
from src.services import auth_service

router = APIRouter(tags=["Authentication"])

DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DBSession,
) -> User:
    """Dependency that decodes bearer token and retrieves the authenticated user."""
    payload = decode_access_token(token)
    token_sub = payload.get("sub")
    if not token_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user: User | None = None
    if "@" in token_sub:
        user = await auth_service.get_user_by_email(db, token_sub)
    elif token_sub.isdigit():
        user = await db.get(User, int(token_sub))
    else:
        user = await auth_service.get_user_by_email(db, token_sub)

    if user is None:
        result = await db.scalars(
            select(User).where(User.username == token_sub)
        )
        user = result.first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(data: UserCreate, db: DBSession):
    """Register a new user account."""
    return await auth_service.register_user(db, data)


@router.post(
    "/login",
    response_model=Token,
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession,
):
    """Authenticate credentials and return a signed JWT access token."""
    user = await auth_service.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )

    # Support login with username as fallback if not matched by email
    if not user and "@" not in form_data.username:
        result = await db.scalars(
            select(User).where(User.username == form_data.username)
        )
        candidate = result.first()
        if candidate and verify_password(form_data.password, candidate.hashed_password):
            user = candidate

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserRead,
)
async def get_me(current_user: CurrentUser):
    """Retrieve profile information for the currently authenticated user."""
    return current_user
