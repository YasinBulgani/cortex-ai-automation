"""nexus autopilot run ledger

Revision ID: nexus_autopilot_runs_0001
Revises: approval_traceability_0001
"""

from alembic import op


revision = "nexus_autopilot_runs_0001"
down_revision = "approval_traceability_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tspm_autopilot_runs (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES tspm_projects(id) ON DELETE CASCADE,
            trigger VARCHAR(64) NOT NULL DEFAULT 'manual',
            mode VARCHAR(32) NOT NULL DEFAULT 'autonomous',
            status VARCHAR(32) NOT NULL DEFAULT 'running',
            risk_level VARCHAR(32) NOT NULL DEFAULT 'low',
            summary TEXT,
            snapshot JSONB DEFAULT '{}'::jsonb,
            recommendations JSONB DEFAULT '[]'::jsonb,
            actions JSONB DEFAULT '[]'::jsonb,
            action_results JSONB DEFAULT '[]'::jsonb,
            error TEXT,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tspm_autopilot_runs_project_started
            ON tspm_autopilot_runs(project_id, started_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tspm_autopilot_runs_status
            ON tspm_autopilot_runs(status)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tspm_autopilot_runs_status")
    op.execute("DROP INDEX IF EXISTS ix_tspm_autopilot_runs_project_started")
    op.execute("DROP TABLE IF EXISTS tspm_autopilot_runs")
