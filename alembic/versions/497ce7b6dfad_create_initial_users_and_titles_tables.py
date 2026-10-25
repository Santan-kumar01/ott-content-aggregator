"""create_initial_users_and_titles_tables

Revision ID: 497ce7b6dfad
Revises: 0002
Create Date: 2026-10-25 20:31:59.114010

"""
import os
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '497ce7b6dfad'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: ensure users and titles tables exist with required indexes."""
    if context.is_offline_mode():
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Create users table if not already created
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("is_superuser", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)
    else:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_id" not in existing_indexes:
            op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        if "ix_users_email" not in existing_indexes:
            op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        if "ix_users_username" not in existing_indexes:
            op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    # Create titles table if not already created
    if "titles" not in tables:
        op.create_table(
            "titles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.String(length=2000), nullable=True),
            sa.Column("content_type", sa.String(length=20), nullable=False),
            sa.Column("release_year", sa.Integer(), nullable=False),
            sa.Column("genre", sa.String(length=100), nullable=False),
            sa.Column("platform", sa.String(length=100), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_titles_id"), "titles", ["id"], unique=False)
        op.create_index(op.f("ix_titles_name"), "titles", ["name"], unique=False)
        op.create_index(op.f("ix_titles_release_year"), "titles", ["release_year"], unique=False)
        op.create_index(op.f("ix_titles_genre"), "titles", ["genre"], unique=False)
        op.create_index(op.f("ix_titles_platform"), "titles", ["platform"], unique=False)
    else:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("titles")}
        for idx_name, cols in [
            ("ix_titles_id", ["id"]),
            ("ix_titles_name", ["name"]),
            ("ix_titles_release_year", ["release_year"]),
            ("ix_titles_genre", ["genre"]),
            ("ix_titles_platform", ["platform"]),
        ]:
            if idx_name not in existing_indexes:
                op.create_index(op.f(idx_name), "titles", cols, unique=False)


def downgrade() -> None:
    """Downgrade schema: drop titles and users tables with data loss protection."""
    if context.is_offline_mode():
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Protect against data loss
    if "users" in tables:
        has_data = conn.execute(sa.text("SELECT 1 FROM users LIMIT 1")).first() is not None
        allow_destructive = os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() in ("1", "true", "yes")
        if has_data and not allow_destructive:
            raise RuntimeError(
                "Downgrade aborted: Table 'users' contains data. "
                "Refusing to drop table during rollback to prevent accidental data loss. "
                "If you intentionally want to drop the table and destroy all data, "
                "set the environment variable ALLOW_DESTRUCTIVE_DOWNGRADE=1 before running downgrade."
            )

    if "titles" in tables:
        has_data = conn.execute(sa.text("SELECT 1 FROM titles LIMIT 1")).first() is not None
        allow_destructive = os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() in ("1", "true", "yes")
        if has_data and not allow_destructive:
            raise RuntimeError(
                "Downgrade aborted: Table 'titles' contains data. "
                "Refusing to drop table during rollback to prevent accidental data loss. "
                "If you intentionally want to drop the table and destroy all data, "
                "set the environment variable ALLOW_DESTRUCTIVE_DOWNGRADE=1 before running downgrade."
            )

    if "titles" in tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("titles")}
        for idx in ["ix_titles_platform", "ix_titles_genre", "ix_titles_release_year", "ix_titles_name", "ix_titles_id"]:
            if idx in existing_indexes:
                op.drop_index(op.f(idx), table_name="titles")
        op.drop_table("titles")

    if "users" in tables:
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        for idx in ["ix_users_username", "ix_users_email", "ix_users_id"]:
            if idx in existing_indexes:
                op.drop_index(op.f(idx), table_name="users")
        op.drop_table("users")
