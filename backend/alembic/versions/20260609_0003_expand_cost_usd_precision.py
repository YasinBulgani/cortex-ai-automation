"""Expand cost_usd Numeric precision to support high-spend scenarios (>$1M).

Revision ID: expand_cost_usd_001
Revises: project_members_fk_001
Create Date: 2026-06-09

Changes cost_usd column from Numeric(10,6) (max ~$999,999.999999) to
Numeric(18,6) (max ~$999,999,999,999.999999) to prevent overflow in
high-cost automation/agent scenarios.

Backward compatible: existing data remains valid.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "expand_cost_usd_001"
down_revision: Union[str, None] = "project_members_fk_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Expand cost_usd column precision
    op.alter_column(
        "sd_agent_v2_runs",
        "cost_usd",
        type_=sa.Numeric(precision=18, scale=6),
        existing_type=sa.Numeric(precision=10, scale=6),
    )


def downgrade() -> None:
    # Revert to original precision (may fail if data exceeds old max)
    op.alter_column(
        "sd_agent_v2_runs",
        "cost_usd",
        type_=sa.Numeric(precision=10, scale=6),
        existing_type=sa.Numeric(precision=18, scale=6),
    )
