"""Add language code to customer Telegram topics.

Revision ID: c8f4a2d7e901
Revises: 5e8a1c7d9f02
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c8f4a2d7e901"
down_revision: Union[str, None] = "5e8a1c7d9f02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_tg_topics",
        sa.Column("language_code", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_tg_topics", "language_code")
