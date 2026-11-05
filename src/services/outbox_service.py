import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database import SessionLocal
from src.models.outbox_event import OutboxEvent
from src.services import cache_service

logger = logging.getLogger("src.services.outbox_service")

CATALOG_INVALIDATION_EVENT = "catalog.invalidate"
DEFAULT_BATCH_SIZE = 50
DEFAULT_LEASE_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 10


def enqueue_catalog_invalidation(
    db: AsyncSession,
    title_id: int,
    operation: str,
) -> OutboxEvent:
    """Add an invalidation event to the caller's current transaction."""
    event = OutboxEvent(
        event_type=CATALOG_INVALIDATION_EVENT,
        payload={
            "title_id": title_id,
            "operation": operation,
        },
        status="pending",
        attempts=0,
    )
    db.add(event)
    return event


async def process_outbox_batch(
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
    batch_size: int = DEFAULT_BATCH_SIZE,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> int:
    """Claim and process durable events with ownership-token protection."""
    if batch_size < 1 or lease_seconds < 1 or max_attempts < 1:
        raise ValueError("Batch size, lease and max attempts must be positive")

    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(seconds=lease_seconds)

    async with session_factory() as db:
        await db.execute(
            update(OutboxEvent)
            .where(
                OutboxEvent.status == "processing",
                OutboxEvent.attempts >= max_attempts,
                OutboxEvent.locked_at.is_not(None),
                OutboxEvent.locked_at < stale_before,
            )
            .values(
                status="failed",
                locked_at=None,
                lock_token=None,
                last_error="Worker lease expired after maximum attempts",
            )
        )

        statement = (
            select(OutboxEvent)
            .where(
                OutboxEvent.attempts < max_attempts,
                or_(
                    OutboxEvent.status == "pending",
                    (
                        (OutboxEvent.status == "processing")
                        & or_(
                            OutboxEvent.locked_at.is_(None),
                            OutboxEvent.locked_at < stale_before,
                        )
                    ),
                ),
            )
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )

        result = await db.scalars(statement)
        events = list(result.all())

        if not events:
            await db.commit()
            return 0

        claims = []
        for event in events:
            token = str(uuid4())
            event.status = "processing"
            event.locked_at = now
            event.lock_token = token
            event.attempts += 1
            claims.append((event.id, token, event.attempts, event.event_type))

        await db.commit()

    processed = 0

    for event_id, token, attempts, event_type in claims:
        if event_type != CATALOG_INVALIDATION_EVENT:
            success = False
            error_message = f"Unsupported event type: {event_type}"
            terminal = True
        else:
            try:
                success = await cache_service.invalidate_catalog()
                error_message = "Redis invalidation was unavailable"
            except Exception as exc:
                logger.exception(
                    "Unexpected invalidation error for outbox event %s",
                    event_id,
                )
                success = False
                error_message = str(exc)

            terminal = attempts >= max_attempts

        completed_at = datetime.now(timezone.utc)

        async with session_factory() as db:
            values = (
                {
                    "status": "processed",
                    "processed_at": completed_at,
                    "locked_at": None,
                    "lock_token": None,
                    "last_error": None,
                }
                if success
                else {
                    "status": "failed" if terminal else "pending",
                    "locked_at": None,
                    "lock_token": None,
                    "last_error": error_message[:4000],
                }
            )

            result = await db.execute(
                update(OutboxEvent)
                .where(
                    OutboxEvent.id == event_id,
                    OutboxEvent.status == "processing",
                    OutboxEvent.lock_token == token,
                )
                .values(**values)
            )
            await db.commit()

            if result.rowcount == 1 and success:
                processed += 1
            elif result.rowcount == 0:
                logger.info(
                    "Outbox event %s is no longer owned by this worker",
                    event_id,
                )

    return processed


async def run_outbox_worker(
    stop_event,
    poll_interval: float = 2.0,
    session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
) -> None:
    """Poll the durable outbox until the application requests shutdown."""
    if poll_interval <= 0:
        raise ValueError("Poll interval must be positive")

    logger.info("Outbox worker started")

    try:
        while not stop_event.is_set():
            try:
                await process_outbox_batch(
                    session_factory=session_factory,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Outbox worker iteration failed")

            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=poll_interval,
                )
            except asyncio.TimeoutError:
                continue
    finally:
        logger.info("Outbox worker stopped")
