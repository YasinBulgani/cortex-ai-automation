"""Expand llm_traces contract fields

Revision ID: llm_trace_contract_0007
Revises: cicd_events_0006
"""

from alembic import op

revision = "llm_trace_contract_0007"
down_revision = "cicd_events_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS provider VARCHAR(32)
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS task_type VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(64)
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS cost_usd DOUBLE PRECISION
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS is_streaming BOOLEAN DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS trace_metadata JSONB DEFAULT '{}'::jsonb
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_provider_created
        ON llm_traces(provider, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_task_type
        ON llm_traces(task_type)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_streaming
        ON llm_traces(is_streaming)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_streaming")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_task_type")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_provider_created")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS trace_metadata")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS is_streaming")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS fallback_used")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS cost_usd")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS prompt_version")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS task_type")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS provider")
