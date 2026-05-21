"""Add platform and device_name columns to tspm_schedules

Revision ID: sched_mobile_0001
Revises: perf_indexes_0001
Create Date: 2026-04-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "sched_mobile_0001"
down_revision = "perf_indexes_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tspm_schedules",
        sa.Column("platform", sa.String(32), nullable=True),
    )
    op.add_column(
        "tspm_schedules",
        sa.Column("device_name", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tspm_schedules", "device_name")
    op.drop_column("tspm_schedules", "platform")
