"""Add quarantine columns to sd_apitest_cases

Revision ID: api_testing_quarantine_0005
Revises: notif_prefs_0001
Create Date: 2026-04-15
"""

from __future__ import annotations

from alembic import op

revision = "api_testing_quarantine_0005"
down_revision = "notif_prefs_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE sd_apitest_cases
        ADD COLUMN IF NOT EXISTS quarantined BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE sd_apitest_cases
        ADD COLUMN IF NOT EXISTS quarantine_reason TEXT
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apitc_quarantined
        ON sd_apitest_cases(quarantined)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_apitc_quarantined")
    op.execute(
        """
        ALTER TABLE sd_apitest_cases
        DROP COLUMN IF EXISTS quarantine_reason
        """
    )
    op.execute(
        """
        ALTER TABLE sd_apitest_cases
        DROP COLUMN IF EXISTS quarantined
        """
    )
