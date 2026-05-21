"""AI usage & budget — tenant_id scope + budget policies

Revision ID: ai_usage_budget_0001
Revises: agents_v2_0001

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §3 / E1.2.

Değişiklikler:
    1. ``llm_traces.tenant_id`` (nullable) — per-tenant raporlama & bütçe
       izleme. Multi-tenant modeline geçilene kadar kullanıcı id'si burada
       proxy olarak saklanır. Legacy kayıtlar NULL kalır.
    2. ``ai_budget_policies`` tablosu — tenant bazlı günlük cap (soft/hard).
       Hiç kayıt yoksa bütçe kontrolü devre dışıdır (fail-open; rate limiter
       ayrı koruma sağlıyor).

Index stratejisi:
    (tenant_id, created_at DESC) — per-tenant range query'ler için.
"""

from alembic import op


revision = "ai_usage_budget_0001"
down_revision = "agents_v2_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) llm_traces'e tenant_id ekle
    op.execute(
        """
        ALTER TABLE llm_traces
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_tenant_created
        ON llm_traces(tenant_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_tenant_model_created
        ON llm_traces(tenant_id, model, created_at DESC)
        """
    )

    # 2) Bütçe politika tablosu
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_budget_policies (
            tenant_id           VARCHAR(64) PRIMARY KEY,
            daily_cap_usd       DOUBLE PRECISION NOT NULL DEFAULT 0,
            hard_cap            BOOLEAN NOT NULL DEFAULT FALSE,
            notify_at_pct       SMALLINT NOT NULL DEFAULT 80,
            notes               TEXT,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_by          VARCHAR(128),
            CHECK (daily_cap_usd >= 0),
            CHECK (notify_at_pct BETWEEN 1 AND 100)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_budget_policies")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_tenant_model_created")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_tenant_created")
    op.execute("ALTER TABLE llm_traces DROP COLUMN IF EXISTS tenant_id")
