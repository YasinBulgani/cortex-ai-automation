"""add_automation_suite_runs

Creates automation_suite_runs — durable storage for Automation Suite run
records (replaces the in-memory/Redis _RunRegistry; pod restart no longer
loses run history). Global table, no RLS.

Revision ID: 20260608_0004
Revises: 20260608_0003
Create Date: 2026-06-08 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = '20260608_0004'
down_revision: Union[str, None] = '20260608_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS automation_suite_runs (
            run_id VARCHAR(32) PRIMARY KEY,
            status VARCHAR(16) NOT NULL DEFAULT 'queued',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ,
            feature_path TEXT,
            framework VARCHAR(32),
            passed INTEGER,
            failed INTEGER,
            error TEXT,
            report_url TEXT,
            logs JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_automation_suite_runs_created "
        "ON automation_suite_runs (created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS automation_suite_runs")
