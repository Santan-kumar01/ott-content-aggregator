import os
from pathlib import Path
import subprocess
import sys

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def get_test_alembic_config(db_path: Path) -> Config:
    """Create an isolated Alembic configuration pointing to a temporary SQLite database."""
    config = Config("alembic.ini")
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_cli_uses_database_url_from_environment(tmp_path: Path):
    """Verify the Alembic CLI uses the configured application database URL."""
    db_file = tmp_path / "configured-url.db"
    project_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    env["JWT_SECRET_KEY"] = "test-only-secret-key-for-local-verification"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert db_file.exists()
    with sa.create_engine(f"sqlite:///{db_file.as_posix()}").connect() as conn:
        tables = set(sa.inspect(conn).get_table_names())
    assert {"titles", "users", "alembic_version"} <= tables


def test_fresh_database_migration_to_head(tmp_path: Path):
    """Verify that a clean database migrates to head cleanly and creates all tables, columns, and indexes."""
    db_file = tmp_path / "fresh.db"
    cfg = get_test_alembic_config(db_file)

    command.upgrade(cfg, "head")

    sync_engine = sa.create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        inspector = sa.inspect(sync_engine)
        tables = inspector.get_table_names()
        assert "alembic_version" in tables
        assert "titles" in tables
        assert "users" in tables

        # Verify titles table columns
        titles_cols = {c["name"]: c for c in inspector.get_columns("titles")}
        for col_name in [
            "id", "name", "description", "content_type",
            "release_year", "genre", "platform", "created_at"
        ]:
            assert col_name in titles_cols

        # Verify titles indexes
        titles_idx_names = {idx["name"] for idx in inspector.get_indexes("titles")}
        for idx in [
            "ix_titles_genre", "ix_titles_id", "ix_titles_name",
            "ix_titles_platform", "ix_titles_release_year"
        ]:
            assert idx in titles_idx_names

        # Verify users table columns
        users_cols = {c["name"]: c for c in inspector.get_columns("users")}
        for col_name in [
            "id", "email", "username", "hashed_password",
            "is_active", "is_superuser", "created_at"
        ]:
            assert col_name in users_cols

        # Verify users indexes and unique constraint
        users_indexes = {idx["name"]: idx for idx in inspector.get_indexes("users")}
        assert "ix_users_id" in users_indexes
        assert "ix_users_username" in users_indexes
        assert "ix_users_email" in users_indexes
        assert bool(users_indexes["ix_users_email"]["unique"]) is True
    finally:
        sync_engine.dispose()


def test_existing_compatible_schema_adoption(tmp_path: Path):
    """Verify that an existing, pre-populated database with compatible schema is safely adopted."""
    db_file = tmp_path / "adoption.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"

    # Pre-create tables without indexes outside of Alembic
    sync_engine = sa.create_engine(sync_url)
    with sync_engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE titles (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description VARCHAR(2000),
                content_type VARCHAR(20) NOT NULL,
                release_year INTEGER NOT NULL,
                genre VARCHAR(100) NOT NULL,
                platform VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO titles (id, name, content_type, release_year, genre, platform)
            VALUES (1, 'Existing Movie', 'Movie', 2021, 'Drama', 'Netflix')
        """))

        conn.execute(sa.text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                username VARCHAR(100) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                is_superuser BOOLEAN DEFAULT 0 NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO users (id, email, username, hashed_password, is_active, is_superuser)
            VALUES (1, 'legacy@example.com', 'legacy_user', 'hashed_pw', 1, 0)
        """))
    sync_engine.dispose()

    # Run Alembic upgrade
    cfg = get_test_alembic_config(db_file)
    command.upgrade(cfg, "head")

    # Verify existing data is intact and required indexes were added
    verify_engine = sa.create_engine(sync_url)
    try:
        with verify_engine.connect() as conn:
            title_row = conn.execute(sa.text("SELECT name FROM titles WHERE id = 1")).fetchone()
            assert title_row is not None
            assert title_row[0] == "Existing Movie"

            user_row = conn.execute(sa.text("SELECT username FROM users WHERE id = 1")).fetchone()
            assert user_row is not None
            assert user_row[0] == "legacy_user"

        inspector = sa.inspect(verify_engine)
        titles_idx = {i["name"] for i in inspector.get_indexes("titles")}
        assert "ix_titles_name" in titles_idx
        assert "ix_titles_genre" in titles_idx

        users_idx = {i["name"] for i in inspector.get_indexes("users")}
        assert "ix_users_email" in users_idx
        assert "ix_users_username" in users_idx
    finally:
        verify_engine.dispose()


def test_incompatible_titles_schema_detection(tmp_path: Path):
    """Verify that an existing titles table missing required columns causes migration to fail loudly."""
    db_file = tmp_path / "incompatible_titles.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"

    # Create titles table missing release_year and content_type
    sync_engine = sa.create_engine(sync_url)
    with sync_engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE titles (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                genre VARCHAR(100) NOT NULL
            )
        """))
    sync_engine.dispose()

    cfg = get_test_alembic_config(db_file)
    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(cfg, "head")

    assert "Migration 0001 aborted: Pre-existing table 'titles' has an incompatible schema" in str(exc_info.value)
    assert "content_type" in str(exc_info.value)
    assert "release_year" in str(exc_info.value)


@pytest.mark.parametrize(
    ("name_column", "expected_error"),
    [
        ("name INTEGER NOT NULL", "must use VARCHAR(200)"),
        ("name VARCHAR(200)", "must be NOT NULL"),
    ],
)
def test_incompatible_title_column_definition(
    tmp_path: Path, name_column: str, expected_error: str
):
    db_file = tmp_path / "incompatible_title_column.db"
    sync_engine = sa.create_engine(f"sqlite:///{db_file.as_posix()}")
    with sync_engine.begin() as conn:
        conn.execute(sa.text(f"""
            CREATE TABLE titles (
                id INTEGER PRIMARY KEY,
                {name_column},
                description VARCHAR(2000),
                content_type VARCHAR(20) NOT NULL,
                release_year INTEGER NOT NULL,
                genre VARCHAR(100) NOT NULL,
                platform VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
    sync_engine.dispose()

    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(get_test_alembic_config(db_file), "head")

    assert expected_error in str(exc_info.value)


def test_incompatible_users_schema_detection(tmp_path: Path):
    """Verify that an existing users table missing required columns causes migration to fail loudly."""
    db_file = tmp_path / "incompatible_users.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"

    sync_engine = sa.create_engine(sync_url)
    with sync_engine.begin() as conn:
        # Valid titles table
        conn.execute(sa.text("""
            CREATE TABLE titles (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description VARCHAR(2000),
                content_type VARCHAR(20) NOT NULL,
                release_year INTEGER NOT NULL,
                genre VARCHAR(100) NOT NULL,
                platform VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        # Invalid users table missing hashed_password and is_superuser
        conn.execute(sa.text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                username VARCHAR(100) NOT NULL
            )
        """))
    sync_engine.dispose()

    cfg = get_test_alembic_config(db_file)
    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(cfg, "head")

    assert "Migration 0002 aborted: Pre-existing table 'users' has an incompatible schema" in str(exc_info.value)
    assert "hashed_password" in str(exc_info.value)


@pytest.mark.parametrize(
    ("email_column", "expected_error"),
    [
        ("email INTEGER NOT NULL", "must use VARCHAR(255)"),
        ("email VARCHAR(255)", "must be NOT NULL"),
    ],
)
def test_incompatible_user_column_definition(
    tmp_path: Path, email_column: str, expected_error: str
):
    db_file = tmp_path / "incompatible_user_column.db"
    sync_engine = sa.create_engine(f"sqlite:///{db_file.as_posix()}")
    with sync_engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE titles (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description VARCHAR(2000),
                content_type VARCHAR(20) NOT NULL,
                release_year INTEGER NOT NULL,
                genre VARCHAR(100) NOT NULL,
                platform VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        conn.execute(sa.text(f"""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                {email_column},
                username VARCHAR(100) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                is_superuser BOOLEAN DEFAULT 0 NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
    sync_engine.dispose()

    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(get_test_alembic_config(db_file), "head")

    assert expected_error in str(exc_info.value)


def test_incompatible_users_non_unique_email_index(tmp_path: Path):
    """Verify that an existing users table with a non-unique email index is rejected."""
    db_file = tmp_path / "non_unique_email.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"

    sync_engine = sa.create_engine(sync_url)
    with sync_engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE titles (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description VARCHAR(2000),
                content_type VARCHAR(20) NOT NULL,
                release_year INTEGER NOT NULL,
                genre VARCHAR(100) NOT NULL,
                platform VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        conn.execute(sa.text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                username VARCHAR(100) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT 1 NOT NULL,
                is_superuser BOOLEAN DEFAULT 0 NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        # Create non-unique index with ix_users_email name
        conn.execute(sa.text("CREATE INDEX ix_users_email ON users (email)"))
    sync_engine.dispose()

    cfg = get_test_alembic_config(db_file)
    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(cfg, "head")

    assert "Migration 0002 aborted: Index 'ix_users_email' exists on table 'users' but is not UNIQUE." in str(exc_info.value)


def test_downgrade_preserves_data_and_blocks_accidental_drop(tmp_path: Path):
    """Verify that downgrade refuses to drop tables when rows are present to protect data."""
    db_file = tmp_path / "downgrade_protect.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_test_alembic_config(db_file)

    # First upgrade to head
    command.upgrade(cfg, "head")

    # Insert user data
    sync_engine = sa.create_engine(sync_url)
    with sync_engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO users (id, email, username, hashed_password, is_active, is_superuser, created_at)
            VALUES (1, 'protected@example.com', 'protected_user', 'secret', 1, 0, CURRENT_TIMESTAMP)
        """))
    sync_engine.dispose()

    # Attempt downgrade without ALLOW_DESTRUCTIVE_DOWNGRADE
    with pytest.raises(RuntimeError) as exc_info:
        command.downgrade(cfg, "-1")

    assert "Downgrade aborted: Table 'users' contains data." in str(exc_info.value)
    assert "Refusing to drop table during rollback to prevent accidental data loss" in str(exc_info.value)

    # Verify table and data are still intact
    verify_engine = sa.create_engine(sync_url)
    try:
        with verify_engine.connect() as conn:
            row = conn.execute(sa.text("SELECT email FROM users WHERE id = 1")).fetchone()
            assert row is not None
            assert row[0] == "protected@example.com"
    finally:
        verify_engine.dispose()


def test_downgrade_with_explicit_permission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify that downgrade drops tables when ALLOW_DESTRUCTIVE_DOWNGRADE is explicitly set."""
    db_file = tmp_path / "downgrade_allowed.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_test_alembic_config(db_file)

    command.upgrade(cfg, "head")

    sync_engine = sa.create_engine(sync_url)
    with sync_engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO titles (id, name, content_type, release_year, genre, platform)
            VALUES (1, 'Delete Me', 'Movie', 2020, 'Action', 'Prime')
        """))
        conn.execute(sa.text("""
            INSERT INTO users (id, email, username, hashed_password, is_active, is_superuser, created_at)
            VALUES (1, 'deleteme@example.com', 'delete_user', 'secret', 1, 0, CURRENT_TIMESTAMP)
        """))
    sync_engine.dispose()

    # Set explicit opt-in environment variable
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_DOWNGRADE", "1")

    # Downgrade to base should now succeed
    command.downgrade(cfg, "base")

    verify_engine = sa.create_engine(sync_url)
    try:
        inspector = sa.inspect(verify_engine)
        tables = inspector.get_table_names()
        assert "users" not in tables
        assert "titles" not in tables
    finally:
        verify_engine.dispose()


def test_downgrade_empty_tables_succeeds(tmp_path: Path):
    """Verify that downgrade on empty tables succeeds without error."""
    db_file = tmp_path / "downgrade_empty.db"
    sync_url = f"sqlite:///{db_file.as_posix()}"
    cfg = get_test_alembic_config(db_file)

    command.upgrade(cfg, "head")

    # Empty tables rollback
    command.downgrade(cfg, "base")

    verify_engine = sa.create_engine(sync_url)
    try:
        inspector = sa.inspect(verify_engine)
        tables = inspector.get_table_names()
        assert "users" not in tables
        assert "titles" not in tables
    finally:
        verify_engine.dispose()
