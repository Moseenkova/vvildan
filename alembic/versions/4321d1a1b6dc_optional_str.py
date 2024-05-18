"""optional str

Revision ID: 4321d1a1b6dc
Revises: 15bfa61f3c92
Create Date: 2024-05-18 16:56:34.376733

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4321d1a1b6dc"
down_revision: Union[str, None] = "15bfa61f3c92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("users", "phone", existing_type=sa.INTEGER(), nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column("users", "phone", existing_type=sa.INTEGER(), nullable=False)
    # ### end Alembic commands ###
