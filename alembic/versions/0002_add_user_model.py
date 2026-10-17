"""Add user model for authentication

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 10:00:00.000000

"""
from collections.abc import Sequence
import os
from typing import Any

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_USERS_COLUMNS = {
    "id",
    "email",
    "username",
    "hashed_password",
    "is_active",
    "is_superuser",
    "created_at",
}

REQUIRED_USERS_SCHEMA = {
    "id": (sa.Integer(), False),
    "email": (sa.String(length=255), False),
    "username": (sa.String(length=100), False),
    "hashed_password": (sa.String(length=255), False),
    "is_active": (sa.Boolean(), False),
    "is_superuser": (sa.Boolean(), False),
    "created_at": (sa.DateTime(timezone=True), False),
}

REQUIRED_USERS_INDEXES = [
    ("ix_users_email", ["email"], True),
    ("ix_users_id", ["id"], False),
    ("ix_users_username", ["username"], False),
]


def _incompatible_columns(columns: dict[str, Any]) -> list[str]:
    issues = []
    for name, (expected_type, nullable) in REQUIRED_USERS_SCHEMA.items():
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


def _create_users_table() -> None:
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
    for idx_name, cols, is_unique in REQUIRED_USERS_INDEXES:
        op.create_index(op.f(idx_name), "users", cols, unique=is_unique)


def upgrade() -> None:
    if context.is_offline_mode():
        _create_users_table()
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "users" not in tables:
        _create_users_table()
    else:
        # Table exists: validate schema compatibility before adopting
        columns = {c["name"]: c for c in inspector.get_columns("users")}
        existing_cols = set(columns)
        missing_cols = REQUIRED_USERS_COLUMNS - existing_cols
        if missing_cols:
            raise RuntimeError(
                f"Migration 0002 aborted: Pre-existing table 'users' has an incompatible schema. "
                f"Missing required column(s): {sorted(missing_cols)}. "
                "Please reconcile the database schema or restore from a verified backup before migrating."
            )

        incompatible_columns = _incompatible_columns(columns)
        if incompatible_columns:
            raise RuntimeError(
                "Migration 0002 aborted: Pre-existing table 'users' has an incompatible schema. "
                f"Incompatible column(s): {'; '.join(incompatible_columns)}. "
                "Please reconcile the database schema or restore from a verified backup before migrating."
            )

        pk = inspector.get_pk_constraint("users")
        if not pk or not pk.get("constrained_columns") or "id" not in pk["constrained_columns"]:
            raise RuntimeError(
                "Migration 0002 aborted: Pre-existing table 'users' lacks a primary key constraint on 'id'."
            )

        existing_indexes = {idx["name"]: idx for idx in inspector.get_indexes("users")}

        # Check unique constraint or unique index on email
        has_unique_email = False
        for idx in existing_indexes.values():
            if "email" in idx.get("column_names", []) and idx.get("unique"):
                has_unique_email = True
                break
        if not has_unique_email:
            for uq in inspector.get_unique_constraints("users"):
                if "email" in uq.get("column_names", []):
                    has_unique_email = True
                    break

        if not has_unique_email:
            if "ix_users_email" not in existing_indexes:
                op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
            else:
                raise RuntimeError(
                    "Migration 0002 aborted: Index 'ix_users_email' exists on table 'users' but is not UNIQUE."
                )

        # Ensure remaining required indexes exist
        for idx_name, cols, is_unique in REQUIRED_USERS_INDEXES:
            if idx_name == "ix_users_email":
                continue
            if idx_name not in existing_indexes:
                op.create_index(op.f(idx_name), "users", cols, unique=is_unique)


def downgrade() -> None:
    if context.is_offline_mode():
        for idx_name, _, _ in reversed(REQUIRED_USERS_INDEXES):
            op.drop_index(op.f(idx_name), table_name="users")
        op.drop_table("users")
        return

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

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

        existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        for idx_name, _, _ in reversed(REQUIRED_USERS_INDEXES):
            if idx_name in existing_indexes:
                op.drop_index(op.f(idx_name), table_name="users")
        op.drop_table("users")
