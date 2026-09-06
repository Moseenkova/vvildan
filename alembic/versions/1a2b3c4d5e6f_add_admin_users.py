"""add admin fields to users

Revision ID: 1a2b3c4d5e6f
Revises: 7561ac255540
Create Date: 2026-09-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "7561ac255540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "tg_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.add_column(
        "users", sa.Column("password_hash", sa.String(length=256), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "is_superuser")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
    op.alter_column("users", "tg_id", existing_type=sa.BigInteger(), nullable=False)
