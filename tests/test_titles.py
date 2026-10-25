from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.database import Base, get_db
from src.main import app
from src.models.title import Title


@pytest.fixture
async def client():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a test user and return a valid access token."""
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "validation@example.com",
            "username": "validationuser",
            "password": "StrongPassword123!",
        },
    )
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "validation@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.anyio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.anyio
async def test_readiness_endpoint(client: AsyncClient):
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }


@pytest.mark.anyio
async def test_readiness_endpoint_returns_503_when_database_fails(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from src import main

    mock_connection = MagicMock()
    mock_connection.execute = AsyncMock(
        side_effect=RuntimeError("Database connection failed")
    )

    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(
        return_value=mock_connection
    )
    mock_engine.connect.return_value.__aexit__ = AsyncMock(
        return_value=False
    )

    monkeypatch.setattr(main, "engine", mock_engine)

    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "not_ready",
            "database": "disconnected",
        }
    }

@pytest.mark.anyio
async def test_create_title_invalid_year(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "name": "Test Movie",
        "description": "Testing invalid year",
        "content_type": "movie",
        "release_year": 1700,
        "genre": "Drama",
        "platform": "Netflix",
    }

    response = await client.post(
        "/api/v1/titles",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.anyio
async def test_create_title_invalid_content_type(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "name": "Test Documentary",
        "description": "Testing invalid content type",
        "content_type": "documentary",
        "release_year": 2020,
        "genre": "Documentary",
        "platform": "Netflix",
    }

    response = await client.post(
        "/api/v1/titles",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.anyio
async def test_unknown_title_returns_404(client: AsyncClient):
    response = await client.get("/api/v1/titles/999999")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_paginated_titles_empty_result(client: AsyncClient):
    response = await client.get("/api/v1/titles/paginated")

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 20
    assert data["has_next"] is False


@pytest.mark.anyio
async def test_paginated_titles_returns_total_and_has_next(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    titles = [
        {
            "name": f"Pagination Movie {i}",
            "description": "Pagination test",
            "content_type": "movie",
            "release_year": 2020 + i,
            "genre": "Drama",
            "platform": "Netflix",
        }
        for i in range(3)
    ]

    for title in titles:
        response = await client.post(
            "/api/v1/titles",
            json=title,
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated?skip=0&limit=2"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["skip"] == 0
    assert data["limit"] == 2
    assert data["has_next"] is True


@pytest.mark.anyio
async def test_paginated_titles_last_page_has_no_next(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    for i in range(2):
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": f"Last Page Movie {i}",
                "description": "Last page test",
                "content_type": "movie",
                "release_year": 2020,
                "genre": "Drama",
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated?skip=1&limit=1"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["has_next"] is False


@pytest.mark.anyio
async def test_paginated_titles_filters_by_genre(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    for name, genre in [
        ("Drama Movie", "Drama"),
        ("Comedy Movie", "Comedy"),
    ]:
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": name,
                "description": "Genre filter test",
                "content_type": "movie",
                "release_year": 2024,
                "genre": genre,
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated?genre=Drama"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["genre"] == "Drama"


@pytest.mark.anyio
async def test_paginated_titles_invalid_pagination_parameters(
    client: AsyncClient,
):
    response = await client.get(
        "/api/v1/titles/paginated?skip=-1"
    )
    assert response.status_code == 422

    response = await client.get(
        "/api/v1/titles/paginated?limit=0"
    )
    assert response.status_code == 422

    response = await client.get(
        "/api/v1/titles/paginated?limit=101"
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_valid_movie_returns_created_title(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "name": "Inception",
        "description": "A science-fiction thriller",
        "content_type": "movie",
        "release_year": 2010,
        "genre": "Sci-Fi",
        "platform": "Netflix",
    }

    response = await client.post(
        "/api/v1/titles",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["id"] > 0
    assert data["name"] == "Inception"
    assert data["content_type"] == "movie"
    assert data["release_year"] == 2010
    assert data["genre"] == "Sci-Fi"
    assert data["platform"] == "Netflix"
    assert "created_at" in data


@pytest.mark.anyio
async def test_list_titles_returns_created_movie(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "name": "Interstellar",
        "description": "A space exploration movie",
        "content_type": "movie",
        "release_year": 2014,
        "genre": "Sci-Fi",
        "platform": "Prime Video",
    }

    create_response = await client.post(
        "/api/v1/titles",
        json=payload,
        headers=auth_headers,
    )
    assert create_response.status_code == 201, create_response.text

    response = await client.get("/api/v1/titles")

    assert response.status_code == 200, response.text
    data = response.json()

    assert any(
        title["name"] == "Interstellar"
        and title["platform"] == "Prime Video"
        for title in data
    )


@pytest.mark.anyio
async def test_list_titles_filters_by_platform_and_release_year(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    titles = [
        {
            "name": "Filter Match",
            "description": "Should match both filters",
            "content_type": "movie",
            "release_year": 2022,
            "genre": "Drama",
            "platform": "Netflix",
        },
        {
            "name": "Different Platform",
            "description": "Should not match platform",
            "content_type": "movie",
            "release_year": 2022,
            "genre": "Drama",
            "platform": "Prime Video",
        },
        {
            "name": "Different Year",
            "description": "Should not match year",
            "content_type": "movie",
            "release_year": 2020,
            "genre": "Drama",
            "platform": "Netflix",
        },
    ]

    for title in titles:
        create_response = await client.post(
            "/api/v1/titles",
            json=title,
            headers=auth_headers,
        )
        assert create_response.status_code == 201, create_response.text

    response = await client.get(
        "/api/v1/titles?platform=Netflix&release_year=2022"
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "Filter Match"
    assert data[0]["platform"] == "Netflix"
    assert data[0]["release_year"] == 2022


@pytest.mark.anyio
async def test_list_titles_searches_name_and_description_case_insensitively(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    titles = [
        {
            "name": "Galaxy Quest",
            "description": "A culinary adventure",
            "content_type": "movie",
            "release_year": 2024,
            "genre": "Comedy",
            "platform": "Netflix",
        },
        {
            "name": "Quiet Planet",
            "description": "A GALACTIC journey",
            "content_type": "show",
            "release_year": 2023,
            "genre": "Sci-Fi",
            "platform": "Prime Video",
        },
        {
            "name": "Unrelated Title",
            "description": "Nothing in common",
            "content_type": "movie",
            "release_year": 2022,
            "genre": "Drama",
            "platform": "Netflix",
        },
        {
            "name": "100% Match",
            "description": "Literal wildcard search",
            "content_type": "movie",
            "release_year": 2021,
            "genre": "Comedy",
            "platform": "Netflix",
        },
        {
            "name": "100X Match",
            "description": "Wildcard lookalike",
            "content_type": "movie",
            "release_year": 2021,
            "genre": "Comedy",
            "platform": "Netflix",
        },
    ]

    for title in titles:
        response = await client.post(
            "/api/v1/titles",
            json=title,
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    name_response = await client.get("/api/v1/titles?search=galaxy")
    description_response = await client.get(
        "/api/v1/titles/paginated?search=GALACTIC"
    )
    literal_response = await client.get(
        "/api/v1/titles/paginated?search=100%25"
    )

    assert name_response.status_code == 200, name_response.text
    assert [title["name"] for title in name_response.json()] == [
        "Galaxy Quest"
    ]
    assert description_response.status_code == 200, description_response.text
    assert [
        title["name"] for title in description_response.json()["items"]
    ] == ["Quiet Planet"]
    assert literal_response.status_code == 200, literal_response.text
    assert [
        title["name"] for title in literal_response.json()["items"]
    ] == ["100% Match"]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("sort_by", "sort_order", "expected_names"),
    [
        ("name", "asc", ["Alpha", "Mike", "Zulu"]),
        ("name", "desc", ["Zulu", "Mike", "Alpha"]),
        ("release_year", "asc", ["Zulu", "Mike", "Alpha"]),
        ("release_year", "desc", ["Alpha", "Mike", "Zulu"]),
    ],
)
async def test_paginated_titles_sort_by_name_or_release_year(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sort_by: str,
    sort_order: str,
    expected_names: list[str],
):
    titles = [
        ("Zulu", 2020),
        ("Alpha", 2022),
        ("Mike", 2021),
    ]
    for name, release_year in titles:
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": name,
                "description": "Sorting test",
                "content_type": "movie",
                "release_year": release_year,
                "genre": "Drama",
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        f"/api/v1/titles/paginated?sort_by={sort_by}"
        f"&sort_order={sort_order}"
    )

    assert response.status_code == 200, response.text
    assert [
        title["name"] for title in response.json()["items"]
    ] == expected_names


@pytest.mark.anyio
async def test_paginated_titles_sort_by_created_at_in_both_directions(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    for name in ["Older", "Middle", "Newer"]:
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": name,
                "description": "Creation date sorting test",
                "content_type": "movie",
                "release_year": 2024,
                "genre": "Drama",
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    session_generator = app.dependency_overrides[get_db]()
    session = await session_generator.__anext__()
    try:
        for name, created_at in [
            ("Older", datetime(2020, 1, 1, tzinfo=timezone.utc)),
            ("Middle", datetime(2021, 1, 1, tzinfo=timezone.utc)),
            ("Newer", datetime(2022, 1, 1, tzinfo=timezone.utc)),
        ]:
            await session.execute(
                update(Title)
                .where(Title.name == name)
                .values(created_at=created_at)
            )
        await session.commit()
    finally:
        await session_generator.aclose()

    ascending_response = await client.get(
        "/api/v1/titles/paginated?sort_by=created_at&sort_order=asc"
    )
    descending_response = await client.get(
        "/api/v1/titles/paginated?sort_by=created_at&sort_order=desc"
    )

    assert ascending_response.status_code == 200, ascending_response.text
    assert descending_response.status_code == 200, descending_response.text
    assert [
        title["name"] for title in ascending_response.json()["items"]
    ] == ["Older", "Middle", "Newer"]
    assert [
        title["name"] for title in descending_response.json()["items"]
    ] == ["Newer", "Middle", "Older"]


@pytest.mark.anyio
async def test_paginated_titles_combine_search_filters_sorting_and_pagination(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    titles = [
        ("Apollo", "SPACE mission", 2020, "Sci-Fi", "Netflix"),
        ("Zenith", "Space exploration", 2020, "Sci-Fi", "Netflix"),
        ("Other Genre", "Space story", 2020, "Drama", "Netflix"),
        ("Other Platform", "Space story", 2020, "Sci-Fi", "Prime Video"),
        ("Other Year", "Space story", 2019, "Sci-Fi", "Netflix"),
        ("No Keyword", "A quiet story", 2020, "Sci-Fi", "Netflix"),
    ]
    for name, description, year, genre, platform in titles:
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": name,
                "description": description,
                "content_type": "movie",
                "release_year": year,
                "genre": genre,
                "platform": platform,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        "/api/v1/titles/paginated"
        "?search=space&genre=Sci-Fi&platform=Netflix&release_year=2020"
        "&sort_by=name&sort_order=desc&skip=1&limit=1"
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 2
    assert [title["name"] for title in data["items"]] == ["Apollo"]
    assert data["skip"] == 1
    assert data["limit"] == 1
    assert data["has_next"] is False


@pytest.mark.anyio
@pytest.mark.parametrize(
    "query",
    [
        "sort_by=invalid",
        "sort_order=descending",
        "search=",
        f"search={'x' * 201}",
    ],
)
async def test_list_titles_rejects_invalid_search_and_sort_parameters(
    client: AsyncClient,
    query: str,
):
    response = await client.get(f"/api/v1/titles/paginated?{query}")

    assert response.status_code == 422


def test_title_list_openapi_documentation():
    """Verify catalog list endpoint documentation in OpenAPI."""
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/titles"]["get"]

    assert operation["summary"] == "List and search catalog titles"
    assert "case-insensitive" in operation["description"]

    parameters = {
        parameter["name"]: parameter
        for parameter in operation["parameters"]
    }

    search_schema = parameters["search"]["schema"]
    string_schema = next(
        item
        for item in search_schema["anyOf"]
        if item.get("type") == "string"
    )

    assert string_schema["minLength"] == 1
    assert string_schema["maxLength"] == 200
    assert (
        "Case-insensitive partial match"
        in parameters["search"]["description"]
    )

    assert "sort_by" in parameters
    assert "sort_order" in parameters
    assert "skip" in parameters
    assert "limit" in parameters


def test_paginated_titles_openapi_documentation():
    """Verify paginated endpoint summary and response schema."""
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/titles/paginated"]["get"]

    assert operation["summary"] == (
        "List catalog titles with pagination metadata"
    )
    assert "has_next" in operation["description"]

    response_schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert response_schema["$ref"].endswith("/PaginatedTitleRead")


def test_catalog_error_responses_use_error_response_schema():
    """Verify catalog error responses reference the reusable ErrorResponse schema."""
    schema = app.openapi()
    paths = schema["paths"]

    expected_responses = {
        ("/api/v1/titles", "post"): ["401", "422"],
        ("/api/v1/titles/{title_id}", "get"): ["404"],
        ("/api/v1/titles/{title_id}", "put"): ["401", "404", "422"],
        ("/api/v1/titles/{title_id}", "delete"): ["401", "404"],
    }

    for (path, method), status_codes in expected_responses.items():
        operation = paths[path][method]

        for status_code in status_codes:
            response = operation["responses"][status_code]
            response_schema = response["content"]["application/json"]["schema"]

            assert response_schema["$ref"] == (
                "#/components/schemas/ErrorResponse"
            ), f"{method.upper()} {path} response {status_code}"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "field", "invalid_value"),
    [
        ("post", "name", ""),
        ("post", "name", "N" * 201),
        ("post", "description", "D" * 2001),
        ("post", "genre", ""),
        ("post", "platform", "P" * 101),
        ("post", "release_year", 2101),
        ("put", "name", ""),
        ("put", "description", "D" * 2001),
        ("put", "genre", ""),
        ("put", "platform", "P" * 101),
    ],
)
async def test_title_endpoints_reject_invalid_field_boundaries(
    client: AsyncClient,
    auth_headers: dict[str, str],
    method: str,
    field: str,
    invalid_value: str | int,
):
    """Reject title payloads that violate schema boundary constraints."""
    payload = {
        "name": "Boundary Test Movie",
        "description": "Valid description",
        "content_type": "movie",
        "release_year": 2020,
        "genre": "Drama",
        "platform": "Netflix",
    }
    payload[field] = invalid_value

    if method == "post":
        response = await client.post(
            "/api/v1/titles",
            json=payload,
            headers=auth_headers,
        )
    else:
        response = await client.put(
            "/api/v1/titles/1",
            json=payload,
            headers=auth_headers,
        )

    assert response.status_code == 422, response.text


@pytest.mark.anyio
@pytest.mark.parametrize("sort_order", ["asc", "desc"])
async def test_paginated_titles_use_id_as_stable_sort_tiebreaker(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sort_order: str,
):
    """Keep equal primary sort values ordered by ascending title ID."""
    created_titles = []

    for name in ["First Inserted", "Second Inserted", "Third Inserted"]:
        response = await client.post(
            "/api/v1/titles",
            json={
                "name": name,
                "description": "Stable sorting regression test",
                "content_type": "movie",
                "release_year": 2024,
                "genre": "Drama",
                "platform": "Netflix",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text
        created_titles.append(response.json())

    session_generator = app.dependency_overrides[get_db]()
    session = await session_generator.__anext__()
    try:
        for title, new_name in zip(
            created_titles,
            ["Third Inserted", "Second Inserted", "First Inserted"],
        ):
            await session.execute(
                update(Title)
                .where(Title.id == title["id"])
                .values(name=new_name)
            )
        await session.commit()
    finally:
        await session_generator.aclose()

    response = await client.get(
        f"/api/v1/titles/paginated?sort_by=release_year&sort_order={sort_order}"
    )

    assert response.status_code == 200, response.text
    result_titles = response.json()["items"]

    assert [title["id"] for title in result_titles] == sorted(
        title["id"] for title in result_titles
    )
    assert [title["name"] for title in result_titles] == [
        "Third Inserted",
        "Second Inserted",
        "First Inserted",
    ]

@pytest.mark.anyio
async def test_health_endpoint_stays_healthy_when_database_fails(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    from src import main

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = RuntimeError(
        "Database connection failed"
    )

    monkeypatch.setattr(main, "engine", mock_engine)

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
