"""store departure and arrival airport lists on requests

Revision ID: 6a8d1f4c2b90
Revises: 4f2a1d7c9b30
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "6a8d1f4c2b90"
down_revision: Union[str, None] = "4f2a1d7c9b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_departure_airports",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("airport_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["airport_id"], ["airports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id", "airport_id"),
    )
    op.create_table(
        "request_arrival_airports",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("airport_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["airport_id"], ["airports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id", "airport_id"),
    )

    op.execute(
        """
        INSERT INTO request_departure_airports (request_id, airport_id)
        SELECT id, origin_id FROM requests
        """
    )
    op.execute(
        """
        INSERT INTO request_arrival_airports (request_id, airport_id)
        SELECT id, destination_id FROM requests
        """
    )
    op.drop_column("requests", "origin_id")
    op.drop_column("requests", "destination_id")


def downgrade() -> None:
    op.add_column("requests", sa.Column("origin_id", sa.Integer(), nullable=True))
    op.add_column("requests", sa.Column("destination_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "requests_origin_id_fkey", "requests", "airports", ["origin_id"], ["id"]
    )
    op.create_foreign_key(
        "requests_destination_id_fkey",
        "requests",
        "airports",
        ["destination_id"],
        ["id"],
    )
    op.execute(
        """
        UPDATE requests
        SET origin_id = (
            SELECT MIN(airport_id) FROM request_departure_airports
            WHERE request_id = requests.id
        ),
        destination_id = (
            SELECT MIN(airport_id) FROM request_arrival_airports
            WHERE request_id = requests.id
        )
        """
    )
    op.alter_column("requests", "origin_id", nullable=False)
    op.alter_column("requests", "destination_id", nullable=False)
    op.drop_table("request_arrival_airports")
    op.drop_table("request_departure_airports")
