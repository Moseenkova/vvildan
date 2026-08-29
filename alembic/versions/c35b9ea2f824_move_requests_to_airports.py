"""move request locations from cities to airports

Revision ID: c35b9ea2f824
Revises: a13f67e8c902
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c35b9ea2f824"
down_revision: Union[str, None] = "a13f67e8c902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM requests) THEN
                RAISE EXCEPTION
                    'Cannot migrate request city IDs to airport IDs while requests exist';
            END IF;
        END $$;
        """
    )
    op.drop_constraint("requests_origin_id_fkey", "requests", type_="foreignkey")
    op.drop_constraint("requests_destination_id_fkey", "requests", type_="foreignkey")
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


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM requests) THEN
                RAISE EXCEPTION
                    'Cannot migrate request airport IDs to city IDs while requests exist';
            END IF;
        END $$;
        """
    )
    op.drop_constraint("requests_origin_id_fkey", "requests", type_="foreignkey")
    op.drop_constraint("requests_destination_id_fkey", "requests", type_="foreignkey")
    op.create_foreign_key(
        "requests_origin_id_fkey", "requests", "cities", ["origin_id"], ["id"]
    )
    op.create_foreign_key(
        "requests_destination_id_fkey",
        "requests",
        "cities",
        ["destination_id"],
        ["id"],
    )
