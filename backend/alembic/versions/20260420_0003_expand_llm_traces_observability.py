"""llm_traces — observability genişletme (Dalga 0 · E1)

Revision ID: llm_traces_observability_0001
Revises: audit_chain_bind_0001

Bağlam:
    `llm_traces` tablosu şu an agent_name, model, provider, task_type,
    prompt_version, cost_usd, correlation_id, tenant_id, is_streaming,
    fallback_used içeriyor. Per-tenant bütçe + Prometheus metrik için
    ek sinyal alanları gerekli (AI_OTOMASYON_GELISTIRME_PLANI §3 / E1.2
    ve yeni Dalga 0 planı L1).

Eklenen alanlar:
    * tier              — mini | mid | premium | local (routing kararı)
    * routing_mode      — cost_optimized | balanced | quality_first
    * cache_hit         — semantic cache hit oldu mu
    * shadow_of_id      — shadow traffic'te parent trace FK
    * status            — ok | rate_limit | schema_fail | timeout | pii_block |
                          budget_block | unknown_error
    * error_class       — exception class name (monitoring için)
    * refine_iterations — self_refine kaç tur döndü
    * retry_count       — transient error retry sayısı
    * quality_score     — post-hoc judge skoru (0.0-1.0)
    * schema_violation  — structured output başarısız oldu mu
    * ttft_ms           — time-to-first-token (streaming)
    * prompt_id         — prompts registry ID'si (versiyonlu prompt)

Backfill:
    Mevcut satırlar NULL (status hariç — 'ok' default). Yeni kayıtlar zengin
    metadata ile gelir. Zaman serisi analizi için geriye dönük trace'ler
    NULL olarak atlanır.
"""
from alembic import op


revision = "llm_traces_observability_0001"
# Merge: audit_chain_bind + ai_safety (her ikisi de llm_correlation_0001'den
# dallandı — paralel ilerleyen çalışmaları burada birleştiriyoruz).
down_revision = ("audit_chain_bind_0001", "ai_safety_0001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Routing & tier ──────────────────────────────────────────────────
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS tier VARCHAR(16)")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS routing_mode VARCHAR(32)")

    # ── Cache & shadow ──────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS cache_hit BOOLEAN DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS shadow_of_id BIGINT"
    )

    # ── Status / hata sinyalleri ─────────────────────────────────────────
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'ok'"
    )
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS error_class VARCHAR(128)")
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS schema_violation BOOLEAN DEFAULT FALSE"
    )

    # ── Refine & retry ──────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS refine_iterations SMALLINT DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS retry_count SMALLINT DEFAULT 0"
    )

    # ── Post-hoc kalite ──────────────────────────────────────────────────
    op.execute(
        "ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION"
    )

    # ── Streaming ───────────────────────────────────────────────────────
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS ttft_ms INTEGER")

    # ── Prompt registry FK ──────────────────────────────────────────────
    # prompts registry henüz stable değil; string id (FK yok) tutuyoruz
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS prompt_id VARCHAR(128)")

    # ── İndeksler — dashboard query'leri için ──────────────────────────
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_tenant_status_created
        ON llm_traces(tenant_id, status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_tier_created
        ON llm_traces(tier, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_cache_hit
        ON llm_traces(cache_hit) WHERE cache_hit = TRUE
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_shadow_of
        ON llm_traces(shadow_of_id) WHERE shadow_of_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_llm_traces_prompt_id_created
        ON llm_traces(prompt_id, created_at DESC) WHERE prompt_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_prompt_id_created")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_shadow_of")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_cache_hit")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_tier_created")
    op.execute("DROP INDEX IF EXISTS idx_llm_traces_tenant_status_created")
    for col in (
        "prompt_id", "ttft_ms", "quality_score", "retry_count",
        "refine_iterations", "schema_violation", "error_class",
        "status", "shadow_of_id", "cache_hit", "routing_mode", "tier",
    ):
        op.execute(f"ALTER TABLE llm_traces DROP COLUMN IF EXISTS {col}")
