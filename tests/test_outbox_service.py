from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base
from src.models.outbox_event import OutboxEvent
from src.services.outbox_service import (
    CATALOG_INVALIDATION_EVENT,
    process_outbox_batch,
)


@pytest.fixture
async def outbox_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        yield factory
    finally:
        await engine.dispose()


async def create_event(factory, **overrides):
    values = {
        "event_type": CATALOG_INVALIDATION_EVENT,
        "payload": {"title_id": 101, "operation": "create"},
        "status": "pending",
        "attempts": 0,
    }
    values.update(overrides)

    async with factory() as db:
        event = OutboxEvent(**values)
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event.id


@pytest.mark.anyio
async def test_outbox_event_is_processed_after_successful_invalidation(
    outbox_session_factory,
):
    event_id = await create_event(outbox_session_factory)

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(return_value=True),
    ) as invalidate:
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
        )

    assert processed == 1
    invalidate.assert_awaited_once_with()

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "processed"
        assert event.attempts == 1
        assert event.lock_token is None
        assert event.locked_at is None
        assert event.processed_at is not None
        assert event.last_error is None


@pytest.mark.anyio
async def test_outbox_event_returns_to_pending_after_redis_failure(
    outbox_session_factory,
):
    event_id = await create_event(outbox_session_factory)

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(return_value=False),
    ):
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
            max_attempts=3,
        )

    assert processed == 0

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "pending"
        assert event.attempts == 1
        assert event.lock_token is None
        assert event.last_error == "Redis invalidation was unavailable"


@pytest.mark.anyio
async def test_outbox_event_fails_after_maximum_attempts(
    outbox_session_factory,
):
    event_id = await create_event(
        outbox_session_factory,
        attempts=2,
    )

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(return_value=False),
    ):
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
            max_attempts=3,
        )

    assert processed == 0

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "failed"
        assert event.attempts == 3
        assert event.lock_token is None
        assert event.last_error == "Redis invalidation was unavailable"


@pytest.mark.anyio
async def test_expired_lease_can_be_reclaimed(
    outbox_session_factory,
):
    old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    event_id = await create_event(
        outbox_session_factory,
        status="processing",
        attempts=1,
        locked_at=old_time,
        lock_token="old-worker-token",
    )

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(return_value=True),
    ):
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
            lease_seconds=30,
        )

    assert processed == 1

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "processed"
        assert event.attempts == 2
        assert event.lock_token is None


@pytest.mark.anyio
async def test_unsupported_event_type_is_terminally_failed(
    outbox_session_factory,
):
    event_id = await create_event(
        outbox_session_factory,
        event_type="unknown.event",
    )

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(),
    ) as invalidate:
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
        )

    assert processed == 0
    invalidate.assert_not_awaited()

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "failed"
        assert "Unsupported event type" in event.last_error


@pytest.mark.anyio
async def test_stale_worker_cannot_overwrite_new_worker_claim(
    outbox_session_factory,
):
    event_id = await create_event(outbox_session_factory)

    async def reclaim_event():
        # Simulate another worker taking ownership while the first
        # worker is performing the Redis invalidation.
        async with outbox_session_factory() as db:
            from sqlalchemy import update

            await db.execute(
                update(OutboxEvent)
                .where(OutboxEvent.id == event_id)
                .values(
                    status="processing",
                    lock_token="new-worker-token",
                    locked_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()

        return True

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(side_effect=reclaim_event),
    ):
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
        )

    assert processed == 0

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "processing"
        assert event.lock_token == "new-worker-token"
        assert event.processed_at is None


@pytest.mark.anyio
async def test_processing_event_with_null_lease_can_be_reclaimed(
    outbox_session_factory,
):
    event_id = await create_event(
        outbox_session_factory,
        status="processing",
        attempts=1,
        locked_at=None,
        lock_token="stale-worker-token",
    )

    with patch(
        "src.services.outbox_service.cache_service.invalidate_catalog",
        new=AsyncMock(return_value=True),
    ) as invalidate:
        processed = await process_outbox_batch(
            session_factory=outbox_session_factory,
            lease_seconds=30,
        )

    assert processed == 1
    invalidate.assert_awaited_once_with()

    async with outbox_session_factory() as db:
        event = await db.get(OutboxEvent, event_id)
        assert event.status == "processed"
        assert event.attempts == 2
        assert event.lock_token is None
        assert event.locked_at is None
