"""Allow sender requests without an end date."""

import sqlalchemy as sa

from alembic import op

revision = "ab28f9d1c604"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("requests", "date_to", existing_type=sa.Date(), nullable=True)


def downgrade() -> None:
    # Refuse to discard open-ended dates; resolve them before downgrading.
    op.alter_column("requests", "date_to", existing_type=sa.Date(), nullable=False)
