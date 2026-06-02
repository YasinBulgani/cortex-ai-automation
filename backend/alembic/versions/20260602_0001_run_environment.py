"""add environment column to test_management_runs

Revision ID: 20260602_0001
Revises: 20260524_0002
Create Date: 2026-06-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260602_0001"
down_revision = "20260524_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE test_management_runs ADD COLUMN IF NOT EXISTS environment VARCHAR(64)")


def downgrade() -> None:
    op.drop_column("test_management_runs", "environment")
