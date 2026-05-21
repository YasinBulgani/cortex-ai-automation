"""Synthetic-data platform tabloları (Faz 3.B — ADR-0003).

Revision ID: synthetic_platform_0001
Revises: llm_correlation_0001

Platform-v4'ten backend'e taşınan sentetik veri platformu tabloları:
    * tspm_synthetic_projects            — proje kapsayıcısı
    * tspm_synthetic_detected_schemas    — analiz edilmiş şema
    * tspm_synthetic_generation_rules    — kolon üretim kuralları
    * tspm_synthetic_generation_history  — üretim geçmişi (LearningEngine için)

Tablolar `tspm_synthetic_` prefix'i ile izole; mevcut tspm tablolarıyla
çakışmaz. IF NOT EXISTS + IF EXISTS kullanılır — idempotent, yeniden
çalıştırılabilir.
"""

from alembic import op


revision = "synthetic_platform_0001"
down_revision = "llm_correlation_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── 1. Projects ───────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tspm_synthetic_projects (
            id           VARCHAR(36) PRIMARY KEY,
            name         VARCHAR(255) NOT NULL,
            description  TEXT DEFAULT '',
            owner_id     VARCHAR(64),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tspm_synthetic_projects_owner
            ON tspm_synthetic_projects(owner_id)
    """)

    # ─── 2. Detected Schemas ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tspm_synthetic_detected_schemas (
            id              VARCHAR(36) PRIMARY KEY,
            project_id      VARCHAR(36) NOT NULL REFERENCES tspm_synthetic_projects(id) ON DELETE CASCADE,
            table_name      VARCHAR(255) NOT NULL,
            source_type     VARCHAR(50) DEFAULT 'csv',
            source_info     TEXT DEFAULT '',
            row_count       INTEGER DEFAULT 0,
            columns         JSONB NOT NULL DEFAULT '[]'::jsonb,
            relationships   JSONB DEFAULT '[]'::jsonb,
            pii_summary     JSONB DEFAULT '{}'::jsonb,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tspm_synthetic_schemas_project
            ON tspm_synthetic_detected_schemas(project_id)
    """)

    # ─── 3. Generation Rules ──────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tspm_synthetic_generation_rules (
            id           VARCHAR(36) PRIMARY KEY,
            schema_id    VARCHAR(36) NOT NULL REFERENCES tspm_synthetic_detected_schemas(id) ON DELETE CASCADE,
            column_name  VARCHAR(255) NOT NULL,
            rule_type    VARCHAR(50) NOT NULL,
            rule_config  JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active    BOOLEAN DEFAULT TRUE,
            learned      BOOLEAN DEFAULT FALSE,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tspm_synthetic_rules_schema
            ON tspm_synthetic_generation_rules(schema_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tspm_synthetic_rules_active
            ON tspm_synthetic_generation_rules(schema_id, is_active)
            WHERE is_active = TRUE
    """)

    # ─── 4. Generation History ────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS tspm_synthetic_generation_history (
            id                       VARCHAR(36) PRIMARY KEY,
            project_id               VARCHAR(36) NOT NULL REFERENCES tspm_synthetic_projects(id) ON DELETE CASCADE,
            schema_ids               JSONB DEFAULT '[]'::jsonb,
            row_count                INTEGER DEFAULT 0,
            scenario                 VARCHAR(100) DEFAULT 'default',
            format                   VARCHAR(20) DEFAULT 'csv',
            status                   VARCHAR(20) DEFAULT 'pending',
            result_path              TEXT DEFAULT '',
            generated_data_preview   JSONB DEFAULT '[]'::jsonb,
            duration_ms              INTEGER DEFAULT 0,
            error_message            TEXT DEFAULT '',
            created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tspm_synthetic_history_project
            ON tspm_synthetic_generation_history(project_id, created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tspm_synthetic_history_status
            ON tspm_synthetic_generation_history(status)
            WHERE status IN ('pending', 'running')
    """)


def downgrade() -> None:
    # Dependent order: history → rules → schemas → projects
    op.execute("DROP TABLE IF EXISTS tspm_synthetic_generation_history CASCADE")
    op.execute("DROP TABLE IF EXISTS tspm_synthetic_generation_rules CASCADE")
    op.execute("DROP TABLE IF EXISTS tspm_synthetic_detected_schemas CASCADE")
    op.execute("DROP TABLE IF EXISTS tspm_synthetic_projects CASCADE")
