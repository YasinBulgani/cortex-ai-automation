"""management: release_signoff.role, folder.suite_id update, case hard delete support

Revision ID: 20260603_0004
Revises: 20260603_0003
Create Date: 2026-06-03 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260603_0004"
down_revision = "20260603_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "test_management_release_signoffs",
        sa.Column("role", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("test_management_release_signoffs", "role")
