"""Add localized country, city, and airport names.

Revision ID: b7e3a04d9c21
Revises: 6a8d1f4c2b90
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e3a04d9c21"
down_revision: Union[str, None] = "6a8d1f4c2b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_names_table(table: str, parent: str, foreign_key: str) -> None:
    op.create_table(
        table,
        sa.Column(foreign_key, sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            [foreign_key], [f"{parent}.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            foreign_key, "language_code", "name", name=f"uq_{table}_entity_language_name"
        ),
    )
    op.create_index(f"ix_{table}_{foreign_key}", table, [foreign_key])
    op.create_index(f"ix_{table}_language_code", table, ["language_code"])
    op.create_index(f"ix_{table}_language_name", table, ["language_code", "name"])


def upgrade() -> None:
    _create_names_table("country_names", "countries", "country_id")
    _create_names_table("city_names", "cities", "city_id")
    _create_names_table("airport_names", "airports", "airport_id")


def downgrade() -> None:
    op.drop_table("airport_names")
    op.drop_table("city_names")
    op.drop_table("country_names")
