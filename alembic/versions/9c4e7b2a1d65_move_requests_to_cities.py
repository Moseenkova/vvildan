"""move request locations from airports to cities

Revision ID: 9c4e7b2a1d65
Revises: 3f8c2d1a9b47
Create Date: 2026-08-29 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "9c4e7b2a1d65"
down_revision: Union[str, None] = "3f8c2d1a9b47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_departure_cities",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id", "city_id"),
    )
    op.create_table(
        "request_arrival_cities",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id", "city_id"),
    )
    op.execute(
        """
        INSERT INTO request_departure_cities (request_id, city_id)
        SELECT DISTINCT request_id, airports.city_id
        FROM request_departure_airports
        JOIN airports ON airports.id = request_departure_airports.airport_id
        """
    )
    op.execute(
        """
        INSERT INTO request_arrival_cities (request_id, city_id)
        SELECT DISTINCT request_id, airports.city_id
        FROM request_arrival_airports
        JOIN airports ON airports.id = request_arrival_airports.airport_id
        """
    )
    op.drop_table("request_arrival_airports")
    op.drop_table("request_departure_airports")


def downgrade() -> None:
    op.create_table(
        "request_departure_airports",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("airport_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["airport_id"], ["airports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id", "airport_id"),
    )
    op.create_table(
        "request_arrival_airports",
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("airport_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["airport_id"], ["airports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id", "airport_id"),
    )
    op.execute(
        """
        INSERT INTO request_departure_airports (request_id, airport_id)
        SELECT request_id, MIN(airports.id)
        FROM request_departure_cities
        JOIN airports ON airports.city_id = request_departure_cities.city_id
        GROUP BY request_id, request_departure_cities.city_id
        """
    )
    op.execute(
        """
        INSERT INTO request_arrival_airports (request_id, airport_id)
        SELECT request_id, MIN(airports.id)
        FROM request_arrival_cities
        JOIN airports ON airports.city_id = request_arrival_cities.city_id
        GROUP BY request_id, request_arrival_cities.city_id
        """
    )
    op.drop_table("request_arrival_cities")
    op.drop_table("request_departure_cities")
