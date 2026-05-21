"""Scope project_knowledge rows by project_id

Revision ID: knowledge_scope_0004
Revises: coverup_0003
"""

from alembic import op


revision = "knowledge_scope_0004"
down_revision = "coverup_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE project_knowledge
        ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) NOT NULL DEFAULT '__system__'
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_project_knowledge_project_id
        ON project_knowledge (project_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_project_knowledge_project_source
        ON project_knowledge (project_id, source)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_knowledge_project_source")
    op.execute("DROP INDEX IF EXISTS ix_project_knowledge_project_id")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS project_id")
