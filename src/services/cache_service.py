import hashlib
import json
import logging
from typing import Any

from src.core.cache import (
    is_invalidation_pending,
    redis_delete,
    redis_get,
    redis_incr,
    redis_set,
    set_invalidation_pending,
)
from src.core.database import settings

logger = logging.getLogger("src.services.cache_service")

CATALOG_GENERATION_KEY = "catalog:generation"
DEFAULT_GENERATION = 1


def build_catalog_params_hash(
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> str:
    """Build a deterministic SHA-256 hash of normalized catalog query parameters.

    Ensures that identical parameter sets produce identical cache keys,
    while variations in filters, sorting, search, or pagination produce distinct keys.
    """
    canonical_dict = {
        "genre": genre.strip().lower() if genre else None,
        "limit": limit,
        "platform": platform.strip().lower() if platform else None,
        "release_year": release_year,
        "search": search.strip().lower() if search else None,
        "skip": skip,
        "sort_by": sort_by.strip().lower() if sort_by else None,
        "sort_order": sort_order.strip().lower() if sort_order else "asc",
    }
    canonical_json = json.dumps(
        canonical_dict, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


async def get_catalog_generation() -> int | None:
    """Retrieve the current catalog cache generation version.

    If an invalidation was previously pending due to a Redis outage,
    this function attempts to re-synchronize by incrementing the generation.
    Returns None if Redis is unreachable, triggering safe cache bypass.
    """
    if is_invalidation_pending():
        new_gen = await redis_incr(CATALOG_GENERATION_KEY)
        if new_gen is not None:
            set_invalidation_pending(False)
            logger.info(
                "Pending invalidation recovered: bumped generation to %d",
                new_gen,
            )
            return new_gen
        # Redis is still unreachable
        return None

    val = await redis_get(CATALOG_GENERATION_KEY)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            logger.warning(
                "Invalid generation value '%s' in Redis. Resetting to 1.",
                val,
            )
            await redis_set(CATALOG_GENERATION_KEY, str(DEFAULT_GENERATION))
            return DEFAULT_GENERATION

    # Key does not exist yet. Attempt initialization.
    success = await redis_set(
        CATALOG_GENERATION_KEY, str(DEFAULT_GENERATION)
    )
    if success:
        return DEFAULT_GENERATION

    # Redis is unreachable
    return None


def get_ttl() -> int:
    """Get configured cache TTL in seconds (default: 300)."""
    return getattr(settings, "cache_ttl_seconds", 300)


async def get_catalog_list(
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> list[dict[str, Any]] | None:
    """Get cached list of catalog titles, or None on miss or Redis unavailability."""
    generation = await get_catalog_generation()
    if generation is None:
        return None

    param_hash = build_catalog_params_hash(
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    key = f"catalog:v{generation}:list:{param_hash}"
    raw = await redis_get(key)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return None
    except Exception as exc:
        logger.warning("Corrupted cache payload at '%s': %s", key, exc)
        return None


async def set_catalog_list(
    data: list[dict[str, Any]],
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> bool:
    """Cache serialized catalog title list with configured TTL."""
    generation = await get_catalog_generation()
    if generation is None:
        return False

    param_hash = build_catalog_params_hash(
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    key = f"catalog:v{generation}:list:{param_hash}"
    try:
        raw = json.dumps(data)
        return await redis_set(key, raw, ex=get_ttl())
    except Exception as exc:
        logger.warning(
            "Failed to serialize catalog list for key '%s': %s", key, exc
        )
        return False


async def get_catalog_paginated(
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> dict[str, Any] | None:
    """Get cached paginated catalog response, or None on miss or Redis unavailability."""
    generation = await get_catalog_generation()
    if generation is None:
        return None

    param_hash = build_catalog_params_hash(
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    key = f"catalog:v{generation}:paginated:{param_hash}"
    raw = await redis_get(key)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return None
    except Exception as exc:
        logger.warning("Corrupted cache payload at '%s': %s", key, exc)
        return None


async def set_catalog_paginated(
    data: dict[str, Any],
    genre: str | None = None,
    platform: str | None = None,
    search: str | None = None,
    release_year: int | None = None,
    sort_by: str | None = None,
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 20,
) -> bool:
    """Cache serialized paginated catalog response with configured TTL."""
    generation = await get_catalog_generation()
    if generation is None:
        return False

    param_hash = build_catalog_params_hash(
        genre=genre,
        platform=platform,
        search=search,
        release_year=release_year,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    key = f"catalog:v{generation}:paginated:{param_hash}"
    try:
        raw = json.dumps(data)
        return await redis_set(key, raw, ex=get_ttl())
    except Exception as exc:
        logger.warning(
            "Failed to serialize paginated catalog for key '%s': %s",
            key,
            exc,
        )
        return False


async def get_title(title_id: int) -> dict[str, Any] | None:
    """Get single title from cache, or None on miss or Redis unavailability."""
    generation = await get_catalog_generation()
    if generation is None:
        return None

    key = f"catalog:v{generation}:title:{title_id}"
    raw = await redis_get(key)
    if raw is None:
        return None

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return None
    except Exception as exc:
        logger.warning("Corrupted cache payload at '%s': %s", key, exc)
        return None


async def set_title(title_id: int, data: dict[str, Any]) -> bool:
    """Cache single title data with configured TTL."""
    generation = await get_catalog_generation()
    if generation is None:
        return False

    key = f"catalog:v{generation}:title:{title_id}"
    try:
        raw = json.dumps(data)
        return await redis_set(key, raw, ex=get_ttl())
    except Exception as exc:
        logger.warning("Failed to serialize title for key '%s': %s", key, exc)
        return False


async def invalidate_catalog(title_id: int | None = None) -> bool:
    """Invalidate all catalog cache entries after a successful database commit.

    Uses a versioned namespace generation key that is atomically incremented.
    All previous query listings, paginated results, and title representations
    under the previous generation become immediately unreachable and expire naturally.
    """
    new_gen = await redis_incr(CATALOG_GENERATION_KEY)
    if new_gen is None:
        logger.warning(
            "Failed to increment catalog generation during invalidation: Redis is unreachable. "
            "Marking cache invalidation as pending."
        )
        set_invalidation_pending(True)
        return False

    set_invalidation_pending(False)
    logger.info("Catalog cache successfully invalidated (generation: %d)", new_gen)
    return True
