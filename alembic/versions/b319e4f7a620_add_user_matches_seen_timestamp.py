"""add user matches seen timestamp

Revision ID: b319e4f7a620
Revises: af42d8910c73
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b319e4f7a620"
down_revision: Union[str, None] = "af42d8910c73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("matches_seen_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "matches_seen_at")
