import json
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.anyio
async def test_request_id_is_returned_in_response():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")

    # The request ID must be a valid UUID.
    from uuid import UUID

    UUID(response.headers["X-Request-ID"])


@pytest.mark.anyio
async def test_each_request_gets_a_unique_request_id():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first_response = await client.get("/")
        second_response = await client.get("/")

    first_id = first_response.headers["X-Request-ID"]
    second_id = second_response.headers["X-Request-ID"]

    assert first_id != second_id




def test_request_is_logged_with_safe_metadata(caplog):
    request_logger = logging.getLogger("ott_api.requests")
    previous_level = request_logger.level
    previous_disabled = request_logger.disabled

    request_logger.disabled = False
    request_logger.setLevel(logging.INFO)

    try:
        with caplog.at_level(logging.INFO, logger="ott_api.requests"):
            async def make_request():
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    return await client.get("/")

            import asyncio

            response = asyncio.run(make_request())

        records = [
            record
            for record in caplog.records
            if record.name == "ott_api.requests"
        ]

        assert records, "Expected an HTTP request log entry"

        log_data = json.loads(records[-1].getMessage())

        assert log_data["event"] == "http_request"
        assert log_data["method"] == "GET"
        assert log_data["path"] == "/"
        assert log_data["status_code"] == 200
        assert log_data["request_id"] == response.headers["X-Request-ID"]
        assert log_data["duration_ms"] >= 0
    finally:
        request_logger.setLevel(previous_level)
        request_logger.disabled = previous_disabled
