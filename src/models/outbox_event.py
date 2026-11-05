from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    payload: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lock_token: Mapped[UUID | None] = mapped_column(
        String(36), nullable=True
    )
