"""add user language code

Revision ID: c541a839e207
Revises: b319e4f7a620
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c541a839e207"
down_revision: Union[str, None] = "b319e4f7a620"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language_code", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "language_code")
