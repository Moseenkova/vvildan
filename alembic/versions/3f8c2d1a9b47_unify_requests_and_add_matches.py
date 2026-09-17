"""unify sender and courier requests and add matches

Revision ID: 3f8c2d1a9b47
Revises: d2a6f81c9e30
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "3f8c2d1a9b47"
down_revision: Union[str, None] = "d2a6f81c9e30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


request_role = postgresql.ENUM(
    "sender", "courier", name="requestrole", create_type=False
)
request_status = postgresql.ENUM(
    "active",
    "cancelled",
    "completed",
    "expired",
    name="requeststatus",
    create_type=False,
)
match_status = postgresql.ENUM(
    "proposed",
    "contacted",
    "accepted",
    "rejected",
    "completed",
    name="matchstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    request_role.create(bind, checkfirst=True)
    request_status.create(bind, checkfirst=True)
    match_status.create(bind, checkfirst=True)

    # A request must have exactly one legacy owner before it can be migrated.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM requests
                WHERE (sender_id IS NULL) = (courier_id IS NULL)
            ) THEN
                RAISE EXCEPTION
                    'Every request must belong to exactly one sender or courier';
            END IF;
        END $$
        """
    )

    op.alter_column(
        "users",
        "phone",
        existing_type=sa.Integer(),
        type_=sa.String(),
        postgresql_using="phone::text",
        existing_nullable=True,
    )

    op.add_column("requests", sa.Column("user_id", sa.Integer(), nullable=True))
    op.add_column("requests", sa.Column("role", request_role, nullable=True))
    op.add_column(
        "requests",
        sa.Column(
            "status_new",
            request_status,
            nullable=True,
            server_default="active",
        ),
    )

    op.execute(
        """
        UPDATE requests AS request
        SET user_id = sender.user_id, role = 'sender'
        FROM senders AS sender
        WHERE request.sender_id = sender.id
        """
    )
    op.execute(
        """
        UPDATE requests AS request
        SET user_id = courier.user_id, role = 'courier'
        FROM couriers AS courier
        WHERE request.courier_id = courier.id
        """
    )
    op.execute(
        """
        UPDATE requests
        SET date_from = COALESCE(date_from, date),
            date_to = COALESCE(date_to, date),
            status_new = CASE
                WHEN status::text = 'fulfilled' THEN 'completed'::requeststatus
                WHEN status::text = 'rejected' THEN 'cancelled'::requeststatus
                ELSE 'active'::requeststatus
            END
        """
    )

    op.alter_column("requests", "user_id", nullable=False)
    op.alter_column("requests", "role", nullable=False)
    op.alter_column("requests", "date_from", existing_type=sa.Date(), nullable=False)
    op.alter_column("requests", "date_to", existing_type=sa.Date(), nullable=False)
    op.alter_column("requests", "status_new", nullable=False)

    op.drop_constraint("requests_sender_id_fkey", "requests", type_="foreignkey")
    op.drop_constraint("requests_courier_id_fkey", "requests", type_="foreignkey")
    op.drop_column("requests", "sender_id")
    op.drop_column("requests", "courier_id")
    op.drop_column("requests", "date")
    op.drop_column("requests", "status")
    op.alter_column("requests", "status_new", new_column_name="status")

    op.create_foreign_key(
        "requests_user_id_fkey",
        "requests",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_requests_user_id", "requests", ["user_id"])
    op.create_index("ix_requests_role", "requests", ["role"])
    op.create_index("ix_requests_status", "requests", ["status"])
    op.create_check_constraint(
        "ck_requests_date_range", "requests", "date_from <= date_to"
    )

    op.create_table(
        "matches",
        sa.Column("sender_request_id", sa.Integer(), nullable=False),
        sa.Column("courier_request_id", sa.Integer(), nullable=False),
        sa.Column("status", match_status, server_default="proposed", nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "sender_request_id <> courier_request_id",
            name="ck_matches_different_requests",
        ),
        sa.ForeignKeyConstraint(
            ["sender_request_id"], ["requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["courier_request_id"], ["requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sender_request_id", "courier_request_id"),
    )

    op.drop_table("senders")
    op.drop_table("couriers")


def downgrade() -> None:
    op.create_table(
        "couriers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "senders",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.execute(
        """
        INSERT INTO senders (user_id, created_at)
        SELECT DISTINCT user_id, now() FROM requests WHERE role = 'sender'
        """
    )
    op.execute(
        """
        INSERT INTO couriers (user_id, created_at)
        SELECT DISTINCT user_id, now() FROM requests WHERE role = 'courier'
        """
    )

    old_status = postgresql.ENUM(
        "new",
        "pending",
        "accepted",
        "rejected",
        "fulfilled",
        name="status",
        create_type=False,
    )
    old_status.create(op.get_bind(), checkfirst=True)

    op.add_column("requests", sa.Column("sender_id", sa.Integer(), nullable=True))
    op.add_column("requests", sa.Column("courier_id", sa.Integer(), nullable=True))
    op.add_column("requests", sa.Column("date", sa.Date(), nullable=True))
    op.add_column("requests", sa.Column("status_old", old_status, nullable=True))
    op.execute(
        """
        UPDATE requests AS request
        SET sender_id = sender.id
        FROM senders AS sender
        WHERE request.role = 'sender' AND request.user_id = sender.user_id
        """
    )
    op.execute(
        """
        UPDATE requests AS request
        SET courier_id = courier.id, date = request.date_from
        FROM couriers AS courier
        WHERE request.role = 'courier' AND request.user_id = courier.user_id
        """
    )
    op.execute(
        """
        UPDATE requests
        SET status_old = CASE
            WHEN status::text = 'completed' THEN 'fulfilled'::status
            WHEN status::text = 'cancelled' THEN 'rejected'::status
            ELSE 'new'::status
        END
        """
    )
    op.alter_column("requests", "status_old", nullable=False)

    op.drop_table("matches")
    op.drop_constraint("ck_requests_date_range", "requests", type_="check")
    op.drop_index("ix_requests_status", table_name="requests")
    op.drop_index("ix_requests_role", table_name="requests")
    op.drop_index("ix_requests_user_id", table_name="requests")
    op.drop_constraint("requests_user_id_fkey", "requests", type_="foreignkey")
    op.drop_column("requests", "status")
    op.alter_column("requests", "status_old", new_column_name="status")
    op.drop_column("requests", "role")
    op.drop_column("requests", "user_id")
    op.create_foreign_key(
        "requests_sender_id_fkey", "requests", "senders", ["sender_id"], ["id"]
    )
    op.create_foreign_key(
        "requests_courier_id_fkey",
        "requests",
        "couriers",
        ["courier_id"],
        ["id"],
    )

    op.alter_column(
        "users",
        "phone",
        existing_type=sa.String(),
        type_=sa.Integer(),
        postgresql_using="phone::integer",
        existing_nullable=True,
    )

    match_status.drop(op.get_bind(), checkfirst=True)
    request_status.drop(op.get_bind(), checkfirst=True)
    request_role.drop(op.get_bind(), checkfirst=True)
