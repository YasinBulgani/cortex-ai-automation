"""tspm_approvals — source + decision traceability

Revision ID: approval_traceability_0001
Revises: ai_batch_analysis_artifact_0001
"""

from alembic import op


revision = "approval_traceability_0001"
down_revision = "ai_batch_analysis_artifact_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tspm_approvals
            ADD COLUMN IF NOT EXISTS source_batch_id UUID
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_approvals
            ADD COLUMN IF NOT EXISTS source_test_case_id UUID
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_approvals
            ADD COLUMN IF NOT EXISTS decision_note TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_approvals
            ADD COLUMN IF NOT EXISTS decision_trace JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tspm_approvals DROP COLUMN IF EXISTS decision_trace")
    op.execute("ALTER TABLE tspm_approvals DROP COLUMN IF EXISTS decision_note")
    op.execute("ALTER TABLE tspm_approvals DROP COLUMN IF EXISTS source_test_case_id")
    op.execute("ALTER TABLE tspm_approvals DROP COLUMN IF EXISTS source_batch_id")
