"""create_initial_users_and_titles_tables

Revision ID: 497ce7b6dfad
Revises: 
Create Date: 2026-10-25 20:31:59.114010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '497ce7b6dfad'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create users and titles tables with indexes."""
    # Create users table
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

    # Create titles table
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


def downgrade() -> None:
    """Downgrade schema: drop titles and users tables with indexes."""
    op.drop_index(op.f("ix_titles_platform"), table_name="titles")
    op.drop_index(op.f("ix_titles_genre"), table_name="titles")
    op.drop_index(op.f("ix_titles_release_year"), table_name="titles")
    op.drop_index(op.f("ix_titles_name"), table_name="titles")
    op.drop_index(op.f("ix_titles_id"), table_name="titles")
    op.drop_table("titles")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

