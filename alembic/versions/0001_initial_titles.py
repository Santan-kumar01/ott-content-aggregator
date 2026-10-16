"""Initial migration: create titles table

Revision ID: 0001
Revises: None
Create Date: 2026-10-14 16:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

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
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_titles_genre"), "titles", ["genre"], unique=False)
        op.create_index(op.f("ix_titles_id"), "titles", ["id"], unique=False)
        op.create_index(op.f("ix_titles_name"), "titles", ["name"], unique=False)
        op.create_index(op.f("ix_titles_platform"), "titles", ["platform"], unique=False)
        op.create_index(op.f("ix_titles_release_year"), "titles", ["release_year"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "titles" in tables:
        op.drop_index(op.f("ix_titles_release_year"), table_name="titles")
        op.drop_index(op.f("ix_titles_platform"), table_name="titles")
        op.drop_index(op.f("ix_titles_name"), table_name="titles")
        op.drop_index(op.f("ix_titles_id"), table_name="titles")
        op.drop_index(op.f("ix_titles_genre"), table_name="titles")
        op.drop_table("titles")
