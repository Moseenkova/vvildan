"""add match seen timestamps

Revision ID: af42d8910c73
Revises: 0d4e6f8a1b2c
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "af42d8910c73"
down_revision: Union[str, None] = "0d4e6f8a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("sender_seen_at", sa.DateTime(), nullable=True))
    op.add_column("matches", sa.Column("courier_seen_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "courier_seen_at")
    op.drop_column("matches", "sender_seen_at")
