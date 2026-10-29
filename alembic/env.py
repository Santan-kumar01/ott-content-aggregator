
import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Ensure project root is in sys.path.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

from src.core.database import Base, settings
from src.models import Title, User

# Alembic Config object.
config = context.config

# Configure Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get the database URL from Alembic arguments or application settings."""
    x_args = context.get_x_argument(as_dictionary=True)

    if x_args.get("url"):
        return x_args["url"]

    current_url = config.get_main_option("sqlalchemy.url")

    if not current_url or current_url.startswith("driver:"):
        current_url = settings.database_url

    if not current_url:
        raise RuntimeError("Database URL is not configured.")

    return current_url


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    url = get_url()

    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    elif url.startswith("sqlite://") and not url.startswith(
        "sqlite+aiosqlite://"
    ):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations using an active connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an asynchronous database connection."""
    url = get_url()

    if url.startswith("sqlite://") and not url.startswith(
        "sqlite+aiosqlite://"
    ):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
