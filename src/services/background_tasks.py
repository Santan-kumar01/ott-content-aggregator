from datetime import datetime, timezone
import logging
from typing import Any

from src.core.database import SessionLocal
from src.models.title import Title
from src.services import cache_service, catalog_service
from src.services.external_provider_service import (
    ExternalProviderError,
    fetch_external_title_metadata,
)

logger = logging.getLogger("src.services.background_tasks")

# Thread-safe in-memory task registry providing observability for background jobs.
# Note: FastAPI BackgroundTasks runs within the application process. Tasks do not survive
# process termination or unexpected server crashes (unlike durable brokers like Celery/RabbitMQ).
_task_registry: dict[str, dict[str, Any]] = {}


def register_background_task(task_id: str, title_id: int) -> dict[str, Any]:
    """Register a new background task in the pending state."""
    record = {
        "task_id": task_id,
        "title_id": title_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "completed_at": None,
        "result": None,
        "error": None,
    }
    _task_registry[task_id] = record
    return record


def get_background_task_status(task_id: str) -> dict[str, Any] | None:
    """Retrieve observable status and result of a background task."""
    return _task_registry.get(task_id)


def record_task_status(
    task_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Update background task status, outcome, or error message."""
    if task_id in _task_registry:
        _task_registry[task_id]["status"] = status
        _task_registry[task_id]["result"] = result
        _task_registry[task_id]["error"] = error
        if status in ("completed", "failed"):
            _task_registry[task_id]["completed_at"] = datetime.now(timezone.utc)


async def sync_title_from_external_provider_task(
    task_id: str,
    title_id: int,
    external_id: str | None = None,
    provider: str | None = None,
) -> None:
    """Asynchronous background task to sync title metadata from an external provider.

    Opens an isolated PostgreSQL session (never reusing request sessions),
    fetches external metadata via non-blocking HTTP, updates title fields,
    commits the transaction, and invalidates the Redis catalog cache post-commit.
    """
    record_task_status(task_id, "in_progress")
    logger.info(
        "Starting background sync for title ID %d (task %s)",
        title_id,
        task_id,
    )

    # Always acquire an isolated, fresh database session inside background tasks
    async with SessionLocal() as db:
        try:
            # 1. Verify title exists in the database
            title = await catalog_service.get_title(db, title_id)
            if title is None:
                err_msg = f"Title ID {title_id} not found in database."
                logger.warning("Background sync aborted: %s", err_msg)
                record_task_status(task_id, "failed", error=err_msg)
                return

            # 2. Fetch metadata from external provider via async HTTP
            lookup_id = external_id or str(title.id)
            metadata = await fetch_external_title_metadata(
                lookup_id, provider=provider
            )

            # 3. Update title fields if provided by external source
            synced_fields = []
            if metadata.description:
                title.description = metadata.description
                synced_fields.append("description")
            if metadata.genre:
                title.genre = metadata.genre
                synced_fields.append("genre")
            if metadata.platform:
                title.platform = metadata.platform
                synced_fields.append("platform")
            if metadata.release_year:
                title.release_year = metadata.release_year
                synced_fields.append("release_year")

            # 4. Commit database transaction
            await db.commit()
            await db.refresh(title)

            # 5. Invalidate Redis catalog cache only after successful commit
            await cache_service.invalidate_catalog(title_id=title_id)

            # 6. Record observable task success
            result_data = {
                "title_id": title.id,
                "name": title.name,
                "synced_fields": synced_fields,
                "external_id": metadata.external_id,
            }
            record_task_status(task_id, "completed", result=result_data)
            logger.info(
                "Background sync succeeded for title ID %d (task %s, synced: %s)",
                title_id,
                task_id,
                synced_fields,
            )

        except ExternalProviderError as exc:
            await db.rollback()
            err_msg = f"External provider failure: {exc}"
            logger.warning(
                "Background sync failed for title ID %d (task %s): %s",
                title_id,
                task_id,
                exc,
            )
            record_task_status(task_id, "failed", error=err_msg)

        except Exception as exc:
            await db.rollback()
            err_msg = f"Unexpected error during sync: {exc}"
            logger.exception(
                "Background sync encountered error for title ID %d (task %s)",
                title_id,
                task_id,
            )
            record_task_status(task_id, "failed", error=err_msg)
