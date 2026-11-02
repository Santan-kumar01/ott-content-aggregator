import asyncio
import logging
import re
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from src.core.database import settings

logger = logging.getLogger("src.core.cache")

# Shared Redis client instance and the event loop it was created on
_redis_client: aioredis.Redis | None = None
_client_loop: asyncio.AbstractEventLoop | None = None

# Tracks if cache invalidation could not reach Redis during a previous write
_invalidation_pending: bool = False


def sanitize_redis_url(url: str) -> str:
    """Mask credentials in Redis URL for safe logging and diagnostic messages."""
    if not url:
        return ""
    # Matches ://<user>:<password>@ or ://:<password>@
    return re.sub(r"://([^:@]*):([^@]+)@", r"://\1:***@", url)


def get_redis_client() -> aioredis.Redis | None:
    """Return the active Redis client, lazily initializing if necessary.

    Re-creates the client if the asyncio event loop changes or is closed
    (e.g., across separate test functions in pytest).
    """
    global _redis_client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _redis_client is not None:
        if (
            current_loop is not None
            and _client_loop is current_loop
            and not current_loop.is_closed()
        ):
            return _redis_client
        # Event loop changed or closed: reset reference
        _redis_client = None
        _client_loop = None

    if not getattr(settings, "cache_enabled", True):
        return None

    try:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
            retry_on_timeout=False,
        )
        _client_loop = current_loop
        return _redis_client
    except Exception as exc:
        logger.warning(
            "Failed to instantiate Redis client for %s: %s",
            sanitize_redis_url(settings.redis_url),
            exc,
        )
        return None


async def init_redis_client() -> aioredis.Redis | None:
    """Initialize Redis client during application startup.

    Verifies connectivity via PING without failing application startup
    if Redis is temporarily unreachable.
    """
    client = get_redis_client()
    if client is None:
        return None

    try:
        await client.ping()
        logger.info(
            "Connected to Redis cache at %s",
            sanitize_redis_url(settings.redis_url),
        )
    except Exception as exc:
        logger.warning(
            "Redis cache at %s is currently unreachable (%s). "
            "Catalog queries will bypass cache until connection is restored.",
            sanitize_redis_url(settings.redis_url),
            exc,
        )
    return client


async def close_redis_client() -> None:
    """Gracefully close the Redis client and release connection pool resources."""
    global _redis_client, _client_loop
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
            logger.info("Redis cache client closed successfully.")
        except Exception as exc:
            logger.warning("Error closing Redis client: %s", exc)
        finally:
            _redis_client = None
            _client_loop = None


async def check_redis_health() -> str:
    """Check connectivity to Redis without raising exceptions.

    Returns:
        'connected' if ping succeeds, otherwise 'disconnected'.
    """
    client = get_redis_client()
    if client is None:
        return "disconnected"

    try:
        is_pong = await client.ping()
        return "connected" if is_pong else "disconnected"
    except Exception:
        return "disconnected"


def set_invalidation_pending(pending: bool) -> None:
    """Set flag indicating whether a background invalidation is pending."""
    global _invalidation_pending
    _invalidation_pending = pending


def is_invalidation_pending() -> bool:
    """Check if a prior invalidation failed and needs re-synchronization."""
    return _invalidation_pending


async def redis_get(key: str) -> str | None:
    """Safely get string value by key from Redis.

    Returns None on cache miss or Redis failure.
    """
    global _redis_client, _client_loop
    client = get_redis_client()
    if client is None:
        return None

    try:
        return await client.get(key)
    except (
        RedisError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        logger.warning(
            "Redis GET failed for key '%s': %s. Bypassing cache.",
            key,
            exc,
        )
        if isinstance(exc, RuntimeError):
            _redis_client = None
            _client_loop = None
        return None


async def redis_set(
    key: str,
    value: str,
    ex: int | None = None,
) -> bool:
    """Safely set a key-value pair in Redis with optional expiration in seconds.

    Returns True if successful, False if Redis is unreachable.
    """
    global _redis_client, _client_loop
    client = get_redis_client()
    if client is None:
        return False

    try:
        await client.set(key, value, ex=ex)
        return True
    except (
        RedisError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        logger.warning(
            "Redis SET failed for key '%s': %s. Cache population skipped.",
            key,
            exc,
        )
        if isinstance(exc, RuntimeError):
            _redis_client = None
            _client_loop = None
        return False


async def redis_delete(*keys: str) -> int:
    """Safely delete one or more keys from Redis.

    Returns the number of keys removed, or 0 if Redis is unreachable.
    """
    global _redis_client, _client_loop
    if not keys:
        return 0

    client = get_redis_client()
    if client is None:
        return 0

    try:
        return await client.delete(*keys)
    except (
        RedisError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        logger.warning(
            "Redis DELETE failed for keys %s: %s.",
            keys,
            exc,
        )
        if isinstance(exc, RuntimeError):
            _redis_client = None
            _client_loop = None
        return 0


async def redis_incr(key: str) -> int | None:
    """Safely increment integer value of a key in Redis.

    Returns new integer value, or None if Redis is unreachable.
    """
    global _redis_client, _client_loop
    client = get_redis_client()
    if client is None:
        return None

    try:
        return await client.incr(key)
    except (
        RedisError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        logger.warning(
            "Redis INCR failed for key '%s': %s.",
            key,
            exc,
        )
        if isinstance(exc, RuntimeError):
            _redis_client = None
            _client_loop = None
        return None


async def redis_incr_with_expiry_details(
    key: str,
    ttl_seconds: int,
    max_attempts: int = 5,
) -> tuple[int, int, int] | None:
    """Return count, remaining attempts, and remaining TTL atomically."""
    global _redis_client, _client_loop

    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be greater than zero")
    if max_attempts <= 0:
        raise ValueError("max_attempts must be greater than zero")

    client = get_redis_client()
    if client is None:
        return None

    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    local ttl = redis.call('TTL', KEYS[1])
    return {count, ttl}
    """

    try:
        result = await client.eval(script, 1, key, ttl_seconds)
        count, ttl = int(result[0]), int(result[1])
        remaining = max(0, max_attempts - count)
        return count, remaining, max(0, ttl)
    except (
        RedisError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        logger.warning("Redis rate-limit details failed: %s", exc)
        if isinstance(exc, RuntimeError):
            _redis_client = None
            _client_loop = None
        return None


async def redis_incr_with_expiry(key: str, ttl_seconds: int) -> int | None:
    """Atomically increment a Redis counter and set its initial expiry."""
    global _redis_client, _client_loop

    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be greater than zero")

    client = get_redis_client()
    if client is None:
        return None

    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return count
    """

    try:
        return int(await client.eval(script, 1, key, ttl_seconds))
    except (
        RedisError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,
        RuntimeError,
    ) as exc:
        logger.warning("Redis rate-limit counter failed: %s", exc)
        if isinstance(exc, RuntimeError):
            _redis_client = None
            _client_loop = None
        return None
