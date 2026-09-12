"""Allow sender requests without a start date."""

import sqlalchemy as sa

from alembic import op

revision = "5e8a1c7d9f02"
down_revision = "ab28f9d1c604"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("requests", "date_from", existing_type=sa.Date(), nullable=True)
    op.create_check_constraint(
        "ck_requests_has_date",
        "requests",
        "date_from IS NOT NULL OR date_to IS NOT NULL",
    )


def downgrade() -> None:
    # Refuse to discard requests without start dates; resolve them before downgrading.
    op.drop_constraint("ck_requests_has_date", "requests", type_="check")
    op.alter_column("requests", "date_from", existing_type=sa.Date(), nullable=False)
