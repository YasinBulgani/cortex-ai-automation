"""Scope llm_traces rows by project and user

Revision ID: llm_traces_scope_0005
Revises: knowledge_scope_0004
"""

from alembic import op


revision = "llm_traces_scope_0005"
down_revision = "knowledge_scope_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS project_id VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_project_id
        ON llm_traces(project_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_project_user
        ON llm_traces(project_id, user_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_project_user")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_project_id")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS user_id")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS project_id")
