"""Add PostgreSQL trigram indexes for catalog text search.

Revision ID: 20261107_trgm
Revises: 20261105_outbox
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261107_trgm"
down_revision: Union[str, Sequence[str], None] = "20261105_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        "ix_titles_name_trgm",
        "titles",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_titles_description_trgm",
        "titles",
        ["description"],
        postgresql_using="gin",
        postgresql_ops={"description": "gin_trgm_ops"},
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.drop_index("ix_titles_description_trgm", table_name="titles")
    op.drop_index("ix_titles_name_trgm", table_name="titles")
