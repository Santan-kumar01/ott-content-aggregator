"""merge migration heads

Revision ID: 0003
Revises: 0002, 497ce7b6dfad
Create Date: 2026-10-25 22:54:00.000000

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: tuple[str, str] = ("0002", "497ce7b6dfad")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge migration heads: schema already established and validated in parent revisions."""
    pass


def downgrade() -> None:
    """Downgrade merge: pass through to parent revisions."""
    pass
