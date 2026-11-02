import asyncio
import logging
import re
from typing import Any

import httpx

from src.core.database import settings

logger = logging.getLogger("src.core.http_client")

_http_client: httpx.AsyncClient | None = None
_client_loop: asyncio.AbstractEventLoop | None = None


def sanitize_url(url: str) -> str:
    """Mask sensitive query parameters (e.g. api_key, token, secret) in URLs for safe logging."""
    if not url:
        return ""
    # Mask common sensitive query parameters
    sanitized = re.sub(
        r"([?&](?:api_key|token|secret|password|access_token|key)=)[^&]*",
        r"\1***",
        url,
        flags=re.IGNORECASE,
    )
    # Mask user:password in authority component
    sanitized = re.sub(r"://([^:@]*):([^@]+)@", r"://\1:***@", sanitized)
    return sanitized


def get_http_client() -> httpx.AsyncClient:
    """Return the shared asynchronous HTTP client, lazily initializing if needed.

    Re-creates the client if the asyncio event loop changes or is closed
    (e.g., across separate test functions in pytest).
    """
    global _http_client, _client_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if _http_client is not None and not _http_client.is_closed:
        if (
            current_loop is not None
            and _client_loop is current_loop
            and not current_loop.is_closed()
        ):
            return _http_client
        # Event loop changed or closed: reset reference
        _http_client = None
        _client_loop = None

    timeout_seconds = getattr(settings, "external_api_timeout_seconds", 10.0)
    timeout = httpx.Timeout(
        connect=5.0,
        read=timeout_seconds,
        write=5.0,
        pool=5.0,
    )
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    _http_client = httpx.AsyncClient(timeout=timeout, limits=limits)
    _client_loop = current_loop
    return _http_client


async def init_http_client() -> httpx.AsyncClient:
    """Initialize shared HTTP client during application startup."""
    client = get_http_client()
    logger.info("Shared asynchronous HTTP client initialized.")
    return client


async def close_http_client() -> None:
    """Gracefully close the shared HTTP client and release connection pool resources."""
    global _http_client, _client_loop
    if _http_client is not None and not _http_client.is_closed:
        try:
            await _http_client.aclose()
            logger.info("Shared asynchronous HTTP client closed successfully.")
        except Exception as exc:
            logger.warning("Error closing HTTP client: %s", exc)
        finally:
            _http_client = None
            _client_loop = None
