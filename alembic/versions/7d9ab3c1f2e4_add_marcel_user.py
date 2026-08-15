"""add Marcel user

Revision ID: 7d9ab3c1f2e4
Revises: f81445165daa
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d9ab3c1f2e4"
down_revision: Union[str, None] = "f81445165daa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO users (tg_id, name, phone, created_at)
        SELECT 5875912525, 'Marcel', NULL, NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM users WHERE tg_id = 5875912525
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM users
        WHERE tg_id = 5875912525 AND name = 'Marcel'
        """
    )
