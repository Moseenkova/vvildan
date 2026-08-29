"""Add timezone to refresh token expiration.

Revision ID: 4f2a1d7c9b30
Revises: c35b9ea2f824
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f2a1d7c9b30"
down_revision: Union[str, None] = "c35b9ea2f824"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "refresh_tokens",
        "expire",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="expire AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "refresh_tokens",
        "expire",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="expire AT TIME ZONE 'UTC'",
    )
