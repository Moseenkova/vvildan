"""Add OpenAI response ID to customer Telegram topics.

Revision ID: 0d4e6f8a1b2c
Revises: c8f4a2d7e901
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0d4e6f8a1b2c"
down_revision: Union[str, None] = "c8f4a2d7e901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_tg_topics",
        sa.Column("last_openai_response_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("customer_tg_topics", "last_openai_response_id")
