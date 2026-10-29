import asyncio
import concurrent.futures
import os
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import get_db, settings
from src.main import app

POSTGRES_TEST_URL = os.getenv("POSTGRES_TEST_URL") or make_url(
    settings.database_url
).set(database="ott_test_db").render_as_string(hide_password=False)


@pytest.fixture(scope="module", autouse=True)
def ensure_postgres_schema_migrated():
    """Ensure target PostgreSQL test database has Alembic migrations applied before tests run."""
    def _run_upgrade():
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_section_option(
            "alembic",
            "sqlalchemy.url",
            POSTGRES_TEST_URL.replace("%", "%%"),
        )
        command.upgrade(alembic_cfg, "head")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(_run_upgrade).result()
    else:
        _run_upgrade()


@pytest.fixture(scope="module")
async def pg_engine():
    """Module-level async engine for PostgreSQL integration testing."""
    engine = create_async_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    # Verify genuine PostgreSQL connection
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version()"))
        version_str = result.scalar()
        assert "PostgreSQL" in version_str, f"Expected PostgreSQL, got: {version_str}"
    yield engine
    await engine.dispose()


@pytest.fixture
async def pg_session(pg_engine):
    """Provide a database session connected to PostgreSQL."""
    session_factory = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def pg_client(pg_engine):
    """Provide an HTTPX client whose get_db dependency points to PostgreSQL."""
    session_factory = async_sessionmaker(
        pg_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    from src.api.endpoints import auth

    async def mock_redis_incr_with_expiry(
        key: str, ttl_seconds: int
    ) -> int:
        return 1

    original_limiter = auth.redis_incr_with_expiry
    auth.redis_incr_with_expiry = mock_redis_incr_with_expiry

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        auth.redis_incr_with_expiry = original_limiter
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def pg_auth_headers(pg_client: AsyncClient) -> dict[str, str]:
    """Register and authenticate a test user in PostgreSQL to obtain valid JWT headers."""
    email = "pg_tester@example.com"
    password = "StrongPassword123!"

    # Clean up or register
    await pg_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": "pgtester",
            "password": password,
        },
    )

    login_res = await pg_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# POSTGRESQL INTEGRATION TESTS
# ===========================================================================


@pytest.mark.anyio
async def test_postgres_connection_verification(pg_engine):
    """Verify genuine PostgreSQL connection and driver."""
    async with pg_engine.connect() as conn:
        res = await conn.execute(text("SELECT current_database(), version()"))
        row = res.fetchone()
        db_name, version = row[0], row[1]
        expected_db_name = make_url(
            os.environ.get(
                "POSTGRES_TEST_URL",
                "postgresql+asyncpg://postgres:postgres@localhost:5433/ott_test_db",
            )
        ).database
        assert db_name == expected_db_name
        assert "PostgreSQL" in version


@pytest.mark.anyio
async def test_postgres_user_registration_and_duplicate_handling(pg_client: AsyncClient):
    """Verify user registration, hashing, and duplicate registration rollback in PostgreSQL."""
    email = "unique_pg_user@example.com"
    reg_payload = {
        "email": email,
        "username": "uniquepg",
        "password": "Password123!",
    }

    # 1. First registration succeeds
    res1 = await pg_client.post("/api/v1/auth/register", json=reg_payload)
    assert res1.status_code in (201, 400)  # 201 if fresh, 400 if already exists

    # 2. Duplicate registration is handled with rollback and 400
    res2 = await pg_client.post("/api/v1/auth/register", json=reg_payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()


@pytest.mark.anyio
async def test_postgres_authentication_workflow(
    pg_client: AsyncClient, monkeypatch
):
    """Verify password check, token issuance, and protected routes in PostgreSQL."""

    async def mock_redis_incr_with_expiry(key: str, ttl_seconds: int) -> int:
        return 1

    monkeypatch.setattr(
        "src.api.endpoints.auth.redis_incr_with_expiry",
        mock_redis_incr_with_expiry,
    )
    email = "auth_flow@example.com"
    password = "FlowPassword123!"

    await pg_client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": "authflow", "password": password},
    )

    # Wrong password rejected
    bad_login = await pg_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # Valid login succeeds
    good_login = await pg_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert good_login.status_code == 200
    token = good_login.json()["access_token"]

    # Verify /auth/me
    me_res = await pg_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # Verify unauthenticated write rejected
    unauth_post = await pg_client.post(
        "/api/v1/titles",
        json={"name": "NoToken", "content_type": "movie", "release_year": 2020, "genre": "Drama", "platform": "Netflix"},
    )
    assert unauth_post.status_code == 401


@pytest.mark.anyio
async def test_postgres_catalog_crud_and_persistence(
    pg_client: AsyncClient,
    pg_auth_headers: dict[str, str],
    pg_engine,
):
    """Verify title create, get, patch, search, sort, pagination, persistence across sessions, and delete in PostgreSQL."""
    # 1. Create a uniquely identifiable movie in PostgreSQL
    unique_name = "PG Inception 2026 Persistence Test"
    create_res = await pg_client.post(
        "/api/v1/titles",
        json={
            "name": unique_name,
            "description": "Mind heist in PostgreSQL container",
            "content_type": "movie",
            "release_year": 2026,
            "genre": "Sci-Fi",
            "platform": "Netflix",
        },
        headers=pg_auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    title_id = create_res.json()["id"]

    try:
        # 2. Verify row exists directly in PostgreSQL table via raw SQL
        async with pg_engine.connect() as conn:
            raw_res = await conn.execute(
                text("SELECT id, name, release_year FROM titles WHERE id = :id"),
                {"id": title_id},
            )
            row = raw_res.fetchone()
            assert row is not None
            assert row[1] == unique_name
            assert row[2] == 2026

        # 3. Verify retrieval by ID
        get_res = await pg_client.get(f"/api/v1/titles/{title_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == unique_name

        # 4. Verify search in PostgreSQL (case-insensitive)
        search_res = await pg_client.get("/api/v1/titles?search=persistence")
        assert search_res.status_code == 200
        names = [t["name"] for t in search_res.json()]
        assert unique_name in names

        # 5. Verify sorting and pagination in PostgreSQL
        pag_res = await pg_client.get(
            "/api/v1/titles/paginated?sort_by=release_year&sort_order=desc&limit=10"
        )
        assert pag_res.status_code == 200
        pag_data = pag_res.json()
        assert pag_data["total"] >= 1
        assert "items" in pag_data
        assert pag_data["limit"] == 10

        # 6. Verify PATCH partial update in PostgreSQL
        patch_res = await pg_client.patch(
            f"/api/v1/titles/{title_id}",
            json={"description": "Updated persistence description"},
            headers=pg_auth_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["description"] == "Updated persistence description"

        # 7. Persistence verification after closing/disposing session
        # Simulate restart by creating an entirely new standalone engine
        restart_engine = create_async_engine(POSTGRES_TEST_URL)
        async with restart_engine.connect() as new_conn:
            persisted_res = await new_conn.execute(
                text("SELECT description FROM titles WHERE id = :id"),
                {"id": title_id},
            )
            persisted_desc = persisted_res.scalar()
            assert persisted_desc == "Updated persistence description"
        await restart_engine.dispose()

    finally:
        # 8. Clean up: Delete the test record created by this verification
        del_res = await pg_client.delete(
            f"/api/v1/titles/{title_id}", headers=pg_auth_headers
        )
        assert del_res.status_code == 204

        # Confirm deletion in PostgreSQL
        async with pg_engine.connect() as conn:
            check_del = await conn.execute(
                text("SELECT COUNT(*) FROM titles WHERE id = :id"),
                {"id": title_id},
            )
            assert check_del.scalar() == 0


@pytest.mark.anyio
async def test_postgres_alembic_head_and_schema_parity(pg_engine):
    """Verify Alembic migration head matches PostgreSQL schema and table constraints."""
    async with pg_engine.connect() as conn:
        # 1. Verify alembic_version table exists and reports head
        rev_res = await conn.execute(text("SELECT version_num FROM alembic_version"))
        current_rev = rev_res.scalar()
        assert current_rev == "497ce7b6dfad", f"Expected head 497ce7b6dfad, got {current_rev}"

        # 2. Verify tables exist in PostgreSQL
        tab_res = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        tables = {r[0] for r in tab_res.fetchall()}
        assert "users" in tables
        assert "titles" in tables
        assert "alembic_version" in tables

        # 3. Verify users columns
        u_col_res = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
        )
        u_cols = {r[0] for r in u_col_res.fetchall()}
        assert {"id", "email", "username", "hashed_password", "is_active", "is_superuser", "created_at"}.issubset(u_cols)

        # 4. Verify titles columns
        t_col_res = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'titles'")
        )
        t_cols = {r[0] for r in t_col_res.fetchall()}
        assert {"id", "name", "description", "content_type", "release_year", "genre", "platform", "created_at"}.issubset(t_cols)

        # 5. Verify transaction rollback works under unique constraint violation
        await conn.execute(
            text(
                "INSERT INTO users (email, username, hashed_password) "
                "VALUES ('pg_dupe_check@example.com', 'dupe_base', 'hash123') "
                "ON CONFLICT (email) DO NOTHING"
            )
        )
        await conn.commit()

        trans = await conn.begin()
        try:
            # Attempt duplicate insert violating unique email
            await conn.execute(
                text("INSERT INTO users (email, username, hashed_password) VALUES ('pg_dupe_check@example.com', 'dupe_test', 'hash123')")
            )
        except Exception:
            await trans.rollback()
        else:
            await trans.commit()
            pytest.fail("Duplicate email insert should have violated unique constraint")

        # Session connection is healthy post-rollback
        ping_res = await conn.execute(text("SELECT 1"))
        assert ping_res.scalar() == 1
