"""Add token usage tracking columns to llm_traces

Adds prompt_tokens, completion_tokens, total_tokens columns
and an llm_token_summary view for cost analysis.

Revision ID: token_tracking_0001
Revises: api_testing_quarantine_0005
"""

from alembic import op

revision = "token_tracking_0001"
down_revision = "api_testing_quarantine_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER;
    """)
    op.execute("""
    ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS completion_tokens INTEGER;
    """)
    op.execute("""
    ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS total_tokens INTEGER;
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_llm_traces_tokens
        ON llm_traces (agent_name, created_at)
        WHERE total_tokens IS NOT NULL;
    """)

    op.execute("""
    CREATE OR REPLACE VIEW llm_token_summary AS
    SELECT
        model,
        agent_name,
        DATE(created_at) AS day,
        COUNT(*) AS call_count,
        SUM(total_tokens) AS total_tokens,
        SUM(prompt_tokens) AS total_prompt_tokens,
        SUM(completion_tokens) AS total_completion_tokens,
        ROUND(AVG(latency_ms)) AS avg_latency_ms,
        COUNT(*) FILTER (WHERE success = TRUE) AS success_count,
        COUNT(*) FILTER (WHERE success = FALSE) AS failure_count
    FROM llm_traces
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY model, agent_name, DATE(created_at)
    ORDER BY day DESC, total_tokens DESC NULLS LAST;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS llm_token_summary;")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_tokens;")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS total_tokens;")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS completion_tokens;")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS prompt_tokens;")
