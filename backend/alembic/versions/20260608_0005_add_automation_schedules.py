"""add_automation_schedules

Creates sd_automation_schedules for cron-driven automation runs.
Each row is loaded into APScheduler and fires a trigger="schedule"
AutomationRun on its cron cadence.

Revision ID: 20260608_0005
Revises: 20260608_0004
Create Date: 2026-06-08 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = '20260608_0005'
down_revision: Union[str, None] = '20260608_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_automation_schedules (
            id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(120) NOT NULL,
            kind VARCHAR(32) NOT NULL,
            name VARCHAR(240) NOT NULL,
            cron_expression VARCHAR(120) NOT NULL,
            environment VARCHAR(120),
            device VARCHAR(160),
            target TEXT,
            run_metadata JSONB NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by UUID REFERENCES sd_users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_run_at TIMESTAMPTZ,
            next_run_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_automation_schedules_project "
        "ON sd_automation_schedules (project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_automation_schedules_active "
        "ON sd_automation_schedules (is_active)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_automation_schedules_active")
    op.execute("DROP INDEX IF EXISTS ix_automation_schedules_project")
    op.execute("DROP TABLE IF EXISTS sd_automation_schedules")
