"""created_by

Revision ID: 52eac5d9ca08
Revises: e897772ccd13
Create Date: 2024-07-12 22:08:55.465838

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "52eac5d9ca08"
down_revision: Union[str, None] = "e897772ccd13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("cities_created_by_id_fkey", "cities", type_="foreignkey")
    op.drop_column("cities", "created_by_id")
    op.add_column(
        "user_cities", sa.Column("created_by_id", sa.Integer(), nullable=False)
    )
    op.create_foreign_key(None, "user_cities", "users", ["created_by_id"], ["id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "user_cities", type_="foreignkey")
    op.drop_column("user_cities", "created_by_id")
    op.add_column(
        "cities",
        sa.Column("created_by_id", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.create_foreign_key(
        "cities_created_by_id_fkey", "cities", "users", ["created_by_id"], ["id"]
    )
    # ### end Alembic commands ###
