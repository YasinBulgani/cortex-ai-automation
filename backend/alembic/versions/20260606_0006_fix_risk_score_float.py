"""fix risk_score column type from integer to float in regression_set_cases

Revision ID: 20260606_0006
Revises: 20260606_0005
Create Date: 2026-06-06

"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260606_0006"
down_revision: Union[str, None] = "20260606_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "test_management_regression_set_cases",
        "risk_score",
        type_=sa.Float(),
        existing_type=sa.Integer(),
        existing_nullable=False,
        postgresql_using="risk_score::float",
    )


def downgrade() -> None:
    op.alter_column(
        "test_management_regression_set_cases",
        "risk_score",
        type_=sa.Integer(),
        existing_type=sa.Float(),
        existing_nullable=False,
        postgresql_using="risk_score::integer",
    )
