"""tspm_scenarios — LLM kalite skoru ve semantik embedding kolonları

Revision ID: scenario_quality_llm_0001
Revises: llm_traces_observability_0001

Bağlam:
    AI_OTOMASYON_GELISTIRME_PLANI — LLM-as-Judge senaryo skorlama + pgvector
    duplicate tespiti için tspm_scenarios tablosuna skor + embedding alanları.

Eklenen alanlar:
    * quality_score       — 0-100 (INT). LLM judge skoru.
    * quality_issues      — JSONB liste: [{severity, message, field}]
    * quality_summary     — TEXT. Skorun kısa gerekçesi (TR).
    * quality_scored_at   — TIMESTAMP. Son skorlama zamanı.
    * title_embedding     — JSONB. 768 boyutlu (nomic-embed-text) vektör
                           listesi. pgvector zorunluluğu olmadan JSONB'de
                           tutulur; kosinüs Python'da hesaplanır.

Backfill:
    Mevcut satırlar NULL kalır; /score endpoint'i on-demand veya batch
    (wizard/score-all) ile doldurur.
"""
from alembic import op


revision = "scenario_quality_llm_0001"
down_revision = "llm_traces_observability_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tspm_scenarios ADD COLUMN IF NOT EXISTS quality_score INTEGER")
    op.execute("ALTER TABLE tspm_scenarios ADD COLUMN IF NOT EXISTS quality_issues JSONB")
    op.execute("ALTER TABLE tspm_scenarios ADD COLUMN IF NOT EXISTS quality_summary TEXT")
    op.execute("ALTER TABLE tspm_scenarios ADD COLUMN IF NOT EXISTS quality_scored_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE tspm_scenarios ADD COLUMN IF NOT EXISTS title_embedding JSONB")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tspm_scenarios_quality_score ON tspm_scenarios(quality_score)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tspm_scenarios_quality_score")
    op.execute("ALTER TABLE tspm_scenarios DROP COLUMN IF EXISTS title_embedding")
    op.execute("ALTER TABLE tspm_scenarios DROP COLUMN IF EXISTS quality_scored_at")
    op.execute("ALTER TABLE tspm_scenarios DROP COLUMN IF EXISTS quality_summary")
    op.execute("ALTER TABLE tspm_scenarios DROP COLUMN IF EXISTS quality_issues")
    op.execute("ALTER TABLE tspm_scenarios DROP COLUMN IF EXISTS quality_score")
