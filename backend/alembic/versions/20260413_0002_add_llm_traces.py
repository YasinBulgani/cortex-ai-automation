"""llm_traces tablosu — LLM cagri izleme ve gozlemlenebilirlik

Revision ID: llm_traces_0002
Revises: knowledge_store_0001
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa

revision = "llm_traces_0002"
down_revision = "knowledge_store_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent — tablo zaten varsa atla
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'llm_traces'
            ) THEN
                CREATE TABLE llm_traces (
                    id SERIAL PRIMARY KEY,
                    run_id VARCHAR(64),
                    agent_name VARCHAR(100),
                    model VARCHAR(100),
                    phase VARCHAR(50),
                    system_prompt_preview TEXT,
                    user_prompt_preview TEXT,
                    response_preview TEXT,
                    full_response_length INT,
                    temperature FLOAT,
                    max_tokens INT,
                    latency_ms INT,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    json_parse_ok BOOLEAN,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            END IF;
        END $$;
    """)

    # Indexler — idempotent (IF NOT EXISTS)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_traces_run_id ON llm_traces(run_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_traces_created ON llm_traces(created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_traces_agent ON llm_traces(agent_name)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_traces")
