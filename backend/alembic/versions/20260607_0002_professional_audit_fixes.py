"""Professional audit fixes: project_knowledge missing columns, run-trend support

Revision ID: 20260607_0002
Revises: 20260607_0001
Create Date: 2026-06-07 06:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "20260607_0002"
down_revision = "20260607_0001"
branch_labels = None
depends_on = None


def upgrade():
    # ── project_knowledge — eksik sütunlar ─────────────────────────────────────
    # content_hash: tekrar eden içerikleri deduplikasyon için
    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)"
    )
    # occurrence_count: aynı içeriğin kaç kez görüldüğü
    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS occurrence_count INTEGER NOT NULL DEFAULT 1"
    )
    # last_seen_at: son görülme zamanı (deduplikasyon update için)
    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ"
    )
    # embedding_vec: pgvector sütunu (extension yoksa NULL kalır)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE project_knowledge
                    ADD COLUMN IF NOT EXISTS embedding_vec vector(768);
            ELSE
                ALTER TABLE project_knowledge
                    ADD COLUMN IF NOT EXISTS embedding_vec TEXT;
            END IF;
        END $$;
        """
    )
    # content_tsv: full-text search için
    op.execute(
        "ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS content_tsv TSVECTOR"
    )
    # project_id default NULL yapılarak sistem-dışı kayıtlar destekleniyor
    op.execute(
        "ALTER TABLE project_knowledge ALTER COLUMN project_id DROP DEFAULT"
    )
    # content_hash için index
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_project_knowledge_content_hash ON project_knowledge (content_hash)"
    )

    # ── test_management_runs — run-trend için gerekli sütunlar ─────────────────
    # pass_rate, total_cases gibi summary sütunları run objesi üzerinden hesaplanır
    # Yeni sütun gerekmez — run_cases'dan aggregation yapılır
    # (endpoint service katmanında hesaplar)

    # ── admin domain — billing audit event ─────────────────────────────────────
    # audit_log tablosu yoksa oluştur
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            actor_id UUID,
            action VARCHAR(128) NOT NULL,
            resource_type VARCHAR(64),
            resource_id VARCHAR(128),
            metadata JSONB DEFAULT '{}',
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_actor_id ON audit_log (actor_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_project_knowledge_content_hash")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS content_hash")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS occurrence_count")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS last_seen_at")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS embedding_vec")
    op.execute("ALTER TABLE project_knowledge DROP COLUMN IF EXISTS content_tsv")
    op.execute("DROP TABLE IF EXISTS audit_log")
