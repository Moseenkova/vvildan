"""add conversations and messages

Revision ID: 11e6a7c91f34
Revises: c541a839e207
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "11e6a7c91f34"
down_revision: Union[str, None] = "c541a839e207"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("user_one_id", sa.Integer(), nullable=False),
        sa.Column("user_two_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("user_one_id < user_two_id", name="ck_conversations_user_order"),
        sa.ForeignKeyConstraint(["user_one_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_two_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_one_id", "user_two_id"),
    )
    op.create_index(op.f("ix_conversations_user_one_id"), "conversations", ["user_one_id"])
    op.create_index(op.f("ix_conversations_user_two_id"), "conversations", ["user_two_id"])
    op.create_table(
        "messages",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.String(length=2000), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"])
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(op.f("ix_messages_sender_id"), "messages", ["sender_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_sender_id"), table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_index(op.f("ix_conversations_user_two_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_user_one_id"), table_name="conversations")
    op.drop_table("conversations")
