"""LLM trace correlation ID — bir kullanici istegi -> N LLM cagrisi baglantisi

Revision ID: llm_correlation_0001
Revises: audit_hash_chain_0001

Plan: AI gozlenebilirlik katmani.

Eklenenler:
    * llm_traces.correlation_id  (VARCHAR 64, nullable, indexed)
    * llm_judge_runs.correlation_id (VARCHAR 64, nullable, indexed)

Eski kayitlar NULL kalir. Yeni kayitlar CorrelationMiddleware'den uretilen
UUID4 veya client'in verdigi X-Correlation-ID'yi tasir.
"""

from alembic import op


revision = "llm_correlation_0001"
down_revision = "audit_hash_chain_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_llm_traces_correlation ON llm_traces(correlation_id) WHERE correlation_id IS NOT NULL"
    )

    # llm_judge_runs tablosu varsa oraya da ekle (few_shot_bank migration'da olusuyor)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs') THEN
                ALTER TABLE llm_judge_runs ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64);
                CREATE INDEX IF NOT EXISTS idx_llm_judge_runs_correlation
                    ON llm_judge_runs(correlation_id) WHERE correlation_id IS NOT NULL;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs') THEN
                DROP INDEX IF EXISTS idx_llm_judge_runs_correlation;
                ALTER TABLE llm_judge_runs DROP COLUMN IF EXISTS correlation_id;
            END IF;
        END
        $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_correlation")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS correlation_id")
