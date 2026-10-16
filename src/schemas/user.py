from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=255)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 UTF-8 bytes")
        return v


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    exp: int | None = None
    iat: int | None = None

    @field_validator("sub", mode="before")
    @classmethod
    def convert_sub_to_str(cls, v: Any) -> str | None:
        if v is not None:
            return str(v)
        return None
