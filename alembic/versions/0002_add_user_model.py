"""Add user model for authentication

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

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
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "users" in tables:
        op.drop_index(op.f("ix_users_username"), table_name="users")
        op.drop_index(op.f("ix_users_id"), table_name="users")
        op.drop_index(op.f("ix_users_email"), table_name="users")
        op.drop_table("users")
