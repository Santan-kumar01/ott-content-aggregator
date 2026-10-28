import asyncio
import logging
from typing import Any

import httpx

from src.core.database import settings
from src.core.http_client import get_http_client, sanitize_url
from src.schemas.sync import ExternalTitleMetadata

logger = logging.getLogger("src.services.external_provider")


class ExternalProviderError(Exception):
    """Base exception for external provider communication failures."""
    pass


class ExternalProviderTimeoutError(ExternalProviderError):
    """Raised when an external request times out after bounded retries."""
    pass


class ExternalProviderNotFoundError(ExternalProviderError):
    """Raised when the requested title is not found on the external provider (HTTP 404)."""
    pass


class ExternalProviderValidationError(ExternalProviderError):
    """Raised when external provider returns malformed or invalid response schema."""
    pass


async def fetch_external_title_metadata(
    external_id: str,
    provider: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> ExternalTitleMetadata:
    """Asynchronously fetch and validate title metadata from an external streaming provider.

    Implements bounded retries with exponential backoff on transient network failures,
    masks sensitive credentials in logs, and strictly validates response schema with Pydantic.
    """
    http_client = client or get_http_client()
    base_url = getattr(
        settings, "external_provider_base_url", "https://api.example-ott-provider.com"
    ).rstrip("/")
    url = f"{base_url}/titles/{external_id}"
    params = {"provider": provider} if provider else None

    max_retries = getattr(settings, "external_api_max_retries", 2)
    sanitized = sanitize_url(url)

    for attempt in range(max_retries + 1):
        try:
            logger.debug(
                "Fetching external metadata from %s (attempt %d/%d)",
                sanitized,
                attempt + 1,
                max_retries + 1,
            )
            response = await http_client.get(url, params=params)

            if response.status_code == 404:
                raise ExternalProviderNotFoundError(
                    f"Title '{external_id}' not found on external provider."
                )

            if response.status_code >= 500:
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise ExternalProviderError(
                    f"External provider server error (HTTP {response.status_code})."
                )

            response.raise_for_status()

            try:
                data = response.json()
            except Exception as json_err:
                raise ExternalProviderValidationError(
                    f"Malformed JSON from external provider: {json_err}"
                )

            try:
                return ExternalTitleMetadata.model_validate(data)
            except Exception as val_err:
                raise ExternalProviderValidationError(
                    f"Schema validation failed for external provider response: {val_err}"
                )

        except (httpx.TimeoutException, httpx.ConnectTimeout) as exc:
            if attempt < max_retries:
                logger.warning(
                    "Timeout connecting to %s (attempt %d/%d). Retrying...",
                    sanitized,
                    attempt + 1,
                    max_retries + 1,
                )
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            logger.error(
                "Request to %s timed out after %d retries: %s",
                sanitized,
                max_retries,
                exc,
            )
            raise ExternalProviderTimeoutError(
                f"External provider request timed out: {exc}"
            )

        except httpx.ConnectError as exc:
            if attempt < max_retries:
                logger.warning(
                    "Connection error to %s (attempt %d/%d). Retrying...",
                    sanitized,
                    attempt + 1,
                    max_retries + 1,
                )
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            logger.error(
                "Failed to connect to %s after %d retries: %s",
                sanitized,
                max_retries,
                exc,
            )
            raise ExternalProviderError(
                f"Failed to connect to external provider: {exc}"
            )

        except (
            ExternalProviderError,
            ExternalProviderNotFoundError,
            ExternalProviderValidationError,
        ):
            raise
        except Exception as exc:
            raise ExternalProviderError(
                f"Unexpected error during external provider request: {exc}"
            )

    raise ExternalProviderError(
        f"External provider request exhausted {max_retries} retries."
    )
