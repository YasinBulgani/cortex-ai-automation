"""Add product runtime fields to TSPM projects.

Revision ID: project_runtime_core_0010
Revises: nexus_autopilot_runs_0001
"""

from alembic import op


revision = "project_runtime_core_0010"
down_revision = "nexus_autopilot_runs_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE tspm_projects
            ADD COLUMN IF NOT EXISTS primary_product_id VARCHAR(64) NOT NULL DEFAULT 'one',
            ADD COLUMN IF NOT EXISTS product_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS default_entry_key VARCHAR(128)
        """
    )
    op.execute(
        """
        UPDATE tspm_projects
        SET default_entry_key = CASE primary_product_id
            WHEN 'studio' THEN 'import'
            WHEN 'service' THEN 'api-testing'
            WHEN 'web' THEN 'manual-to-automation'
            WHEN 'mobile' THEN 'mobile'
            WHEN 'data' THEN 'synthetic'
            WHEN 'intelligence' THEN 'ai-metrics'
            WHEN 'nexus-code' THEN 'project-overview'
            ELSE 'settings'
        END
        WHERE default_entry_key IS NULL OR default_entry_key = ''
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tspm_projects_primary_product_id
            ON tspm_projects (primary_product_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tspm_projects_primary_product_id")
    op.execute("ALTER TABLE tspm_projects DROP COLUMN IF EXISTS default_entry_key")
    op.execute("ALTER TABLE tspm_projects DROP COLUMN IF EXISTS product_tags")
    op.execute("ALTER TABLE tspm_projects DROP COLUMN IF EXISTS primary_product_id")
