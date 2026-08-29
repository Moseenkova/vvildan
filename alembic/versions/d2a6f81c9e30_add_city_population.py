"""add city population

Revision ID: d2a6f81c9e30
Revises: b7e3a04d9c21
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d2a6f81c9e30"
down_revision: Union[str, None] = "b7e3a04d9c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cities",
        sa.Column(
            "population",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index("ix_cities_population", "cities", ["population"])


def downgrade() -> None:
    op.drop_index("ix_cities_population", table_name="cities")
    op.drop_column("cities", "population")
