"""Initial migration: create titles table

Revision ID: 0001
Revises: None
Create Date: 2026-10-14 16:30:00.000000

"""
from collections.abc import Sequence
import os
from typing import Any

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_TITLES_COLUMNS = {
    "id",
    "name",
    "description",
    "content_type",
    "release_year",
    "genre",
    "platform",
    "created_at",
}

REQUIRED_TITLES_SCHEMA = {
    "id": (sa.Integer(), False),
    "name": (sa.String(length=200), False),
    "description": (sa.String(length=2000), True),
    "content_type": (sa.String(length=20), False),
    "release_year": (sa.Integer(), False),
    "genre": (sa.String(length=100), False),
    "platform": (sa.String(length=100), False),
    "created_at": (sa.DateTime(timezone=True), False),
}

REQUIRED_TITLES_INDEXES = [
    ("ix_titles_genre", ["genre"], False),
    ("ix_titles_id", ["id"], False),
    ("ix_titles_name", ["name"], False),
    ("ix_titles_platform", ["platform"], False),
    ("ix_titles_release_year", ["release_year"], False),
]


def _incompatible_columns(columns: dict[str, Any]) -> list[str]:
    issues = []
    for name, (expected_type, nullable) in REQUIRED_TITLES_SCHEMA.items():
        if name not in columns:
            continue

        column = columns[name]
        actual_type = column["type"]
        if not isinstance(actual_type, type(expected_type)) or (
            isinstance(expected_type, sa.String)
            and actual_type.length != expected_type.length
        ):
            issues.append(
                f"column '{name}' must use {expected_type} (found {actual_type})"
            )
        if name != "id" and column["nullable"] is not nullable:
            expected_nullability = "NULL" if nullable else "NOT NULL"
            issues.append(f"column '{name}' must be {expected_nullability}")
    return issues


def _create_titles_table() -> None:
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
    for idx_name, cols, is_unique in REQUIRED_TITLES_INDEXES:
        op.create_index(op.f(idx_name), "titles", cols, unique=is_unique)


def upgrade() -> None:
    if context.is_offline_mode():
        _create_titles_table()
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "titles" not in tables:
        _create_titles_table()
    else:
        # Table exists: validate schema compatibility before adopting
        columns = {c["name"]: c for c in inspector.get_columns("titles")}
        existing_cols = set(columns)
        missing_cols = REQUIRED_TITLES_COLUMNS - existing_cols
        if missing_cols:
            raise RuntimeError(
                f"Migration 0001 aborted: Pre-existing table 'titles' has an incompatible schema. "
                f"Missing required column(s): {sorted(missing_cols)}. "
                "Please reconcile the database schema or restore from a verified backup before migrating."
            )

        incompatible_columns = _incompatible_columns(columns)
        if incompatible_columns:
            raise RuntimeError(
                "Migration 0001 aborted: Pre-existing table 'titles' has an incompatible schema. "
                f"Incompatible column(s): {'; '.join(incompatible_columns)}. "
                "Please reconcile the database schema or restore from a verified backup before migrating."
            )

        pk = inspector.get_pk_constraint("titles")
        if not pk or not pk.get("constrained_columns") or "id" not in pk["constrained_columns"]:
            raise RuntimeError(
                "Migration 0001 aborted: Pre-existing table 'titles' lacks a primary key constraint on 'id'."
            )

        # Ensure required indexes exist on the adopted table
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("titles")}
        for idx_name, cols, is_unique in REQUIRED_TITLES_INDEXES:
            if idx_name not in existing_indexes:
                op.create_index(op.f(idx_name), "titles", cols, unique=is_unique)


def downgrade() -> None:
    if context.is_offline_mode():
        for idx_name, _, _ in reversed(REQUIRED_TITLES_INDEXES):
            op.drop_index(op.f(idx_name), table_name="titles")
        op.drop_table("titles")
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "titles" in tables:
        # Protect against accidental deletion of pre-existing or production data
        has_data = conn.execute(sa.text("SELECT 1 FROM titles LIMIT 1")).first() is not None
        allow_destructive = os.environ.get("ALLOW_DESTRUCTIVE_DOWNGRADE", "").lower() in ("1", "true", "yes")

        if has_data and not allow_destructive:
            raise RuntimeError(
                "Downgrade aborted: Table 'titles' contains data. "
                "Refusing to drop table during rollback to prevent accidental data loss. "
                "If you intentionally want to drop the table and destroy all data, "
                "set the environment variable ALLOW_DESTRUCTIVE_DOWNGRADE=1 before running downgrade."
            )

        existing_indexes = {idx["name"] for idx in inspector.get_indexes("titles")}
        for idx_name, _, _ in reversed(REQUIRED_TITLES_INDEXES):
            if idx_name in existing_indexes:
                op.drop_index(op.f(idx_name), table_name="titles")
        op.drop_table("titles")
