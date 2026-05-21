"""Add CI/CD webhook events table.

Revision ID: cicd_events_0006
Revises: llm_traces_scope_0005
"""

from alembic import op


revision = "cicd_events_0006"
down_revision = "llm_traces_scope_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cicd_webhook_events (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(32) NOT NULL UNIQUE,
            source VARCHAR(32) NOT NULL,
            event_type VARCHAR(64) NOT NULL DEFAULT '',
            project_ref VARCHAR(256) NOT NULL DEFAULT '',
            payload JSONB NOT NULL DEFAULT '{}',
            payload_summary JSONB NOT NULL DEFAULT '{}',
            commit_sha VARCHAR(64) NOT NULL DEFAULT '',
            branch VARCHAR(128) NOT NULL DEFAULT '',
            repo_name VARCHAR(256) NOT NULL DEFAULT '',
            author VARCHAR(256) NOT NULL DEFAULT '',
            status VARCHAR(32) NOT NULL DEFAULT 'received',
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cicd_events_source
        ON cicd_webhook_events (source, received_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cicd_events_branch
        ON cicd_webhook_events (branch, received_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_cicd_events_project_ref
        ON cicd_webhook_events (project_ref, received_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_cicd_events_project_ref")
    op.execute("DROP INDEX IF EXISTS idx_cicd_events_branch")
    op.execute("DROP INDEX IF EXISTS idx_cicd_events_source")
    op.execute("DROP TABLE IF EXISTS cicd_webhook_events")
