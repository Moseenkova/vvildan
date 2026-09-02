"""add airports

Revision ID: a13f67e8c902
Revises: 7d9ab3c1f2e4
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a13f67e8c902"
down_revision: Union[str, None] = "7d9ab3c1f2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("countries", sa.Column("iso_code", sa.String(), nullable=True))
    op.create_unique_constraint("uq_countries_iso_code", "countries", ["iso_code"])

    op.drop_constraint("cities_name_key", "cities", type_="unique")
    op.create_unique_constraint(
        "uq_cities_country_id_name", "cities", ["country_id", "name"]
    )

    op.create_table(
        "airports",
        sa.Column("ident", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("airport_type", sa.String(), nullable=False),
        sa.Column("iata_code", sa.String(), nullable=True),
        sa.Column("icao_code", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("scheduled_service", sa.Boolean(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_airports_city_id", "airports", ["city_id"])
    op.create_index("ix_airports_iata_code", "airports", ["iata_code"])
    op.create_index("ix_airports_icao_code", "airports", ["icao_code"])
    op.create_index("ix_airports_ident", "airports", ["ident"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_airports_ident", table_name="airports")
    op.drop_index("ix_airports_icao_code", table_name="airports")
    op.drop_index("ix_airports_iata_code", table_name="airports")
    op.drop_index("ix_airports_city_id", table_name="airports")
    op.drop_table("airports")

    op.drop_constraint("uq_cities_country_id_name", "cities", type_="unique")
    op.create_unique_constraint("cities_name_key", "cities", ["name"])

    op.drop_constraint("uq_countries_iso_code", "countries", type_="unique")
    op.drop_column("countries", "iso_code")
