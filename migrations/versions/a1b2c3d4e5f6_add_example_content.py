"""Add example_content to lessons

Revision ID: a1b2c3d4e5f6
Revises: bb06ade6a000
Create Date: 2026-05-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "bb06ade6a000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add example_content column to lessons table."""
    op.add_column("lessons", sa.Column("example_content", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove example_content column from lessons table."""
    op.drop_column("lessons", "example_content")
