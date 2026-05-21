"""Scope coverup reports by project_id

Revision ID: coverup_scope_0008
Revises: llm_trace_contract_0007
"""

from alembic import op

revision = "coverup_scope_0008"
down_revision = "llm_trace_contract_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE coverage_reports
        ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) DEFAULT '' NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_coverup_reports_project_id_created
        ON coverage_reports(project_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_coverup_reports_project_id_created")
    op.execute("ALTER TABLE coverage_reports DROP COLUMN IF EXISTS project_id")
