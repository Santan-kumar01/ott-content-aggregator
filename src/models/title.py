
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class Title(Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    release_year: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    genre: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
