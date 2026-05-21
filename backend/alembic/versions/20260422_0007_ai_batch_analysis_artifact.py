"""tspm_ai_batches — analysis artifact fields

Revision ID: ai_batch_analysis_artifact_0001
Revises: automation_artifact_contract_0001

Amaç:
    `tspm_ai_batches` kaydını yalnızca toplu üretim kaydı olmaktan çıkarıp
    ürün planındaki `analysis artifact` omurgasına yaklaştırmak.

Eklenen alanlar:
    * analysis_artifact_kind
    * source_checksum
    * normalized_source_excerpt
    * extracted_requirements_count
    * candidate_scenarios_count
    * trace_links
"""

from alembic import op


revision = "ai_batch_analysis_artifact_0001"
down_revision = "automation_artifact_contract_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tspm_ai_batches
            ADD COLUMN IF NOT EXISTS analysis_artifact_kind VARCHAR(64) NOT NULL DEFAULT 'document_analysis'
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_ai_batches
            ADD COLUMN IF NOT EXISTS source_checksum VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_ai_batches
            ADD COLUMN IF NOT EXISTS normalized_source_excerpt TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_ai_batches
            ADD COLUMN IF NOT EXISTS extracted_requirements_count INTEGER NOT NULL DEFAULT 0
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_ai_batches
            ADD COLUMN IF NOT EXISTS candidate_scenarios_count INTEGER NOT NULL DEFAULT 0
        """
    )
    op.execute(
        """
        ALTER TABLE tspm_ai_batches
            ADD COLUMN IF NOT EXISTS trace_links JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tspm_ai_batches DROP COLUMN IF EXISTS trace_links")
    op.execute("ALTER TABLE tspm_ai_batches DROP COLUMN IF EXISTS candidate_scenarios_count")
    op.execute("ALTER TABLE tspm_ai_batches DROP COLUMN IF EXISTS extracted_requirements_count")
    op.execute("ALTER TABLE tspm_ai_batches DROP COLUMN IF EXISTS normalized_source_excerpt")
    op.execute("ALTER TABLE tspm_ai_batches DROP COLUMN IF EXISTS source_checksum")
    op.execute("ALTER TABLE tspm_ai_batches DROP COLUMN IF EXISTS analysis_artifact_kind")
