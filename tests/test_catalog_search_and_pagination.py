from datetime import datetime, timezone

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
            "email": "catalogtester@example.com",
            "username": "catalogtester",
            "password": "StrongPassword123!",
        },
    )
    assert register_response.status_code == 201, register_response.text

    with patch(
        "src.api.endpoints.auth.redis_incr_with_expiry",
        new=AsyncMock(return_value=1),
    ):
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "catalogtester@example.com",
                "password": "StrongPassword123!",
            },
        )
    assert login_response.status_code == 200, login_response.text

    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


# ===========================================================================
# 1. CATALOG TEXT SEARCH TESTS
# ===========================================================================

@pytest.mark.anyio
async def test_search_by_title_name_case_insensitive(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify search matches title name case-insensitively and returns matching records."""
    titles = [
        {"name": "Inception", "description": "Mind heist", "content_type": "movie", "release_year": 2010, "genre": "Sci-Fi", "platform": "Netflix"},
        {"name": "Interstellar", "description": "Wormhole journey", "content_type": "movie", "release_year": 2014, "genre": "Sci-Fi", "platform": "Prime"},
        {"name": "The Dark Knight", "description": "Gotham vigilante", "content_type": "movie", "release_year": 2008, "genre": "Action", "platform": "HBO Max"},
    ]
    for t in titles:
        res = await client.post("/api/v1/titles", json=t, headers=auth_headers)
        assert res.status_code == 201

    # Search lowercase 'inception'
    res = await client.get("/api/v1/titles?search=inception")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "Inception"

    # Search uppercase 'INCEPTION'
    res = await client.get("/api/v1/titles?search=INCEPTION")
    assert res.status_code == 200
    assert len(res.json()) == 1

    # Partial match 'cep'
    res = await client.get("/api/v1/titles?search=cep")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["name"] == "Inception"


@pytest.mark.anyio
async def test_search_by_description_case_insensitive(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify search matches words in description."""
    res = await client.post(
        "/api/v1/titles",
        json={"name": "Dune", "description": "Spice and desert planet Arrakis", "content_type": "movie", "release_year": 2021, "genre": "Sci-Fi", "platform": "Max"},
        headers=auth_headers,
    )
    assert res.status_code == 201

    res = await client.get("/api/v1/titles?search=arrakis")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["name"] == "Dune"


@pytest.mark.anyio
async def test_search_wildcard_escaping(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify SQL wildcard characters %, _, \\ in search are escaped and matched literally."""
    titles = [
        {"name": "100% Cotton", "description": "Literal percent", "content_type": "movie", "release_year": 2020, "genre": "Comedy", "platform": "Netflix"},
        {"name": "1000 Cotton", "description": "Not percent", "content_type": "movie", "release_year": 2020, "genre": "Comedy", "platform": "Netflix"},
        {"name": "file_one", "description": "Literal underscore", "content_type": "movie", "release_year": 2020, "genre": "Drama", "platform": "Netflix"},
        {"name": "fileAone", "description": "Not underscore", "content_type": "movie", "release_year": 2020, "genre": "Drama", "platform": "Netflix"},
    ]
    for t in titles:
        res = await client.post("/api/v1/titles", json=t, headers=auth_headers)
        assert res.status_code == 201

    # Search literal '%'
    res = await client.get("/api/v1/titles?search=100%25")
    assert res.status_code == 200
    names = [x["name"] for x in res.json()]
    assert names == ["100% Cotton"]

    # Search literal '_'
    res = await client.get("/api/v1/titles?search=file_")
    assert res.status_code == 200
    names = [x["name"] for x in res.json()]
    assert names == ["file_one"]


@pytest.mark.anyio
async def test_search_empty_results(client: AsyncClient):
    """Verify search returns empty list when no titles match."""
    res = await client.get("/api/v1/titles?search=nonexistent")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["search=", f"search={'a' * 201}"])
async def test_search_validation_boundaries(client: AsyncClient, query: str):
    """Verify empty search or exceeding 200 chars produces 422 Unprocessable Entity."""
    res = await client.get(f"/api/v1/titles?{query}")
    assert res.status_code == 422


# ===========================================================================
# 2. DYNAMIC SORTING TESTS
# ===========================================================================

@pytest.mark.anyio
@pytest.mark.parametrize(
    ("sort_by", "sort_order", "expected_names"),
    [
        ("name", "asc", ["Alpha", "Beta", "Gamma"]),
        ("name", "desc", ["Gamma", "Beta", "Alpha"]),
        ("release_year", "asc", ["Beta", "Gamma", "Alpha"]),
        ("release_year", "desc", ["Alpha", "Gamma", "Beta"]),
    ],
)
async def test_dynamic_sorting_by_name_and_year(
    client: AsyncClient,
    auth_headers: dict[str, str],
    sort_by: str,
    sort_order: str,
    expected_names: list[str],
):
    """Verify dynamic sorting by name and release_year in asc/desc."""
    items = [
        ("Gamma", 2015),
        ("Alpha", 2024),
        ("Beta", 2005),
    ]
    for name, year in items:
        res = await client.post(
            "/api/v1/titles",
            json={"name": name, "description": "Sort test", "content_type": "movie", "release_year": year, "genre": "Drama", "platform": "Netflix"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    res = await client.get(f"/api/v1/titles?sort_by={sort_by}&sort_order={sort_order}")
    assert res.status_code == 200
    assert [t["name"] for t in res.json()] == expected_names


@pytest.mark.anyio
async def test_dynamic_sorting_by_created_at(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify dynamic sorting by created_at in both directions."""
    for name in ["First", "Second", "Third"]:
        res = await client.post(
            "/api/v1/titles",
            json={"name": name, "description": "Date sort", "content_type": "movie", "release_year": 2020, "genre": "Action", "platform": "Netflix"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    session_generator = app.dependency_overrides[get_db]()
    session = await session_generator.__anext__()
    try:
        for name, created_at in [
            ("First", datetime(2021, 1, 1, tzinfo=timezone.utc)),
            ("Second", datetime(2022, 1, 1, tzinfo=timezone.utc)),
            ("Third", datetime(2023, 1, 1, tzinfo=timezone.utc)),
        ]:
            await session.execute(
                update(Title).where(Title.name == name).values(created_at=created_at)
            )
        await session.commit()
    finally:
        await session_generator.aclose()

    res_asc = await client.get("/api/v1/titles?sort_by=created_at&sort_order=asc")
    assert res_asc.status_code == 200
    assert [t["name"] for t in res_asc.json()] == ["First", "Second", "Third"]

    res_desc = await client.get("/api/v1/titles?sort_by=created_at&sort_order=desc")
    assert res_desc.status_code == 200
    assert [t["name"] for t in res_desc.json()] == ["Third", "Second", "First"]


@pytest.mark.anyio
async def test_sorting_stable_tiebreaker(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify identical sort keys use Title.id.asc() as deterministic tiebreaker."""
    for i in range(3):
        res = await client.post(
            "/api/v1/titles",
            json={"name": f"Same Year {i}", "description": "Tiebreaker", "content_type": "movie", "release_year": 2020, "genre": "Action", "platform": "Netflix"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    res = await client.get("/api/v1/titles?sort_by=release_year&sort_order=desc")
    assert res.status_code == 200
    data = res.json()
    ids = [t["id"] for t in data]
    assert ids == sorted(ids)


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["sort_by=director", "sort_by=id", "sort_order=ascending", "sort_order=descending"])
async def test_sorting_invalid_parameters_rejected(client: AsyncClient, query: str):
    """Verify invalid sort_by or sort_order fields produce 422 Unprocessable Entity."""
    res = await client.get(f"/api/v1/titles?{query}")
    assert res.status_code == 422


# ===========================================================================
# 3. PAGINATION AND METADATA TESTS
# ===========================================================================

@pytest.mark.anyio
async def test_paginated_titles_empty_catalog(client: AsyncClient):
    """Verify /titles/paginated on empty database returns empty items and correct metadata."""
    res = await client.get("/api/v1/titles/paginated")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 20
    assert data["has_next"] is False


@pytest.mark.anyio
async def test_paginated_titles_first_middle_last_pages(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify first, middle, last page pagination behavior."""
    for i in range(5):
        res = await client.post(
            "/api/v1/titles",
            json={"name": f"Page Movie {i}", "description": "Page test", "content_type": "movie", "release_year": 2020 + i, "genre": "Drama", "platform": "Netflix"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    # First page: skip=0, limit=2
    res_first = await client.get("/api/v1/titles/paginated?skip=0&limit=2")
    assert res_first.status_code == 200
    d_first = res_first.json()
    assert len(d_first["items"]) == 2
    assert d_first["total"] == 5
    assert d_first["skip"] == 0
    assert d_first["limit"] == 2
    assert d_first["has_next"] is True

    # Middle page: skip=2, limit=2
    res_mid = await client.get("/api/v1/titles/paginated?skip=2&limit=2")
    assert res_mid.status_code == 200
    d_mid = res_mid.json()
    assert len(d_mid["items"]) == 2
    assert d_mid["total"] == 5
    assert d_mid["has_next"] is True

    # Last page: skip=4, limit=2
    res_last = await client.get("/api/v1/titles/paginated?skip=4&limit=2")
    assert res_last.status_code == 200
    d_last = res_last.json()
    assert len(d_last["items"]) == 1
    assert d_last["total"] == 5
    assert d_last["has_next"] is False

    # Out of range page: skip=10, limit=2
    res_oor = await client.get("/api/v1/titles/paginated?skip=10&limit=2")
    assert res_oor.status_code == 200
    d_oor = res_oor.json()
    assert d_oor["items"] == []
    assert d_oor["total"] == 5
    assert d_oor["has_next"] is False


@pytest.mark.anyio
async def test_paginated_titles_filtered_total_accuracy(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify total in paginated response reflects filtered count, not entire database count."""
    for i in range(6):
        genre = "Sci-Fi" if i < 4 else "Comedy"
        res = await client.post(
            "/api/v1/titles",
            json={"name": f"Movie {i}", "description": "Count test", "content_type": "movie", "release_year": 2020, "genre": genre, "platform": "Netflix"},
            headers=auth_headers,
        )
        assert res.status_code == 201

    res = await client.get("/api/v1/titles/paginated?genre=Sci-Fi&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] == 4
    assert data["has_next"] is True


@pytest.mark.anyio
@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101"])
async def test_paginated_titles_invalid_pagination_boundaries(client: AsyncClient, query: str):
    """Verify negative skip, limit=0, or limit>100 return 422."""
    res = await client.get(f"/api/v1/titles/paginated?{query}")
    assert res.status_code == 422


# ===========================================================================
# 4. COMBINED SEARCH, FILTERS, SORTING, AND PAGINATION
# ===========================================================================

@pytest.mark.anyio
async def test_combined_search_filter_sort_paginate(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Verify combination of search, genre, platform, release_year, sort_by, sort_order, skip, limit."""
    titles = [
        ("Apollo 11", "SPACE exploration", 2020, "Sci-Fi", "Netflix"),
        ("Zenith Space", "Deep mission", 2020, "Sci-Fi", "Netflix"),
        ("Other Genre", "Space drama", 2020, "Drama", "Netflix"),
        ("Other Platform", "Space doc", 2020, "Sci-Fi", "Prime"),
        ("Other Year", "Space history", 2018, "Sci-Fi", "Netflix"),
        ("No Keyword", "Unrelated ocean", 2020, "Sci-Fi", "Netflix"),
    ]
    for name, desc, year, genre, platform in titles:
        res = await client.post(
            "/api/v1/titles",
            json={"name": name, "description": desc, "content_type": "movie", "release_year": year, "genre": genre, "platform": platform},
            headers=auth_headers,
        )
        assert res.status_code == 201

    # Filter: search=space, genre=Sci-Fi, platform=Netflix, release_year=2020, sort_by=name, sort_order=desc
    # Matches: "Zenith Space", "Apollo 11"
    # Paginate: skip=1, limit=1 -> should return "Apollo 11", total=2, has_next=False
    res = await client.get(
        "/api/v1/titles/paginated?search=space&genre=Sci-Fi&platform=Netflix&release_year=2020&sort_by=name&sort_order=desc&skip=1&limit=1"
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert [t["name"] for t in data["items"]] == ["Apollo 11"]
    assert data["skip"] == 1
    assert data["limit"] == 1
    assert data["has_next"] is False


# ===========================================================================
# 5. OPENAPI SCHEMA VALIDATION
# ===========================================================================

def test_openapi_schema_contains_catalog_features():
    """Verify OpenAPI documentation includes search, sort, and pagination schemas."""
    schema = app.openapi()
    paths = schema["paths"]

    # Verify /api/v1/titles GET
    titles_get = paths["/api/v1/titles"]["get"]
    param_names = [p["name"] for p in titles_get["parameters"]]
    assert "search" in param_names
    assert "genre" in param_names
    assert "platform" in param_names
    assert "release_year" in param_names
    assert "sort_by" in param_names
    assert "sort_order" in param_names
    assert "skip" in param_names
    assert "limit" in param_names

    # Verify /api/v1/titles/paginated GET
    paginated_get = paths["/api/v1/titles/paginated"]["get"]
    pag_param_names = [p["name"] for p in paginated_get["parameters"]]
    assert "search" in pag_param_names
    assert "sort_by" in pag_param_names
    assert "sort_order" in pag_param_names
    assert "skip" in pag_param_names
    assert "limit" in pag_param_names

    ref = paginated_get["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("PaginatedTitleRead")
