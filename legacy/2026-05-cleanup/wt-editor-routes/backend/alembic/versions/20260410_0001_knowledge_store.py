"""project_knowledge tablosu — RAG vektör deposu

Revision ID: knowledge_store_0001
Revises: missing_cols_0006
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "knowledge_store_0001"
down_revision = "missing_cols_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector eklentisini dene — yoksa atla (tablo yine oluşur, vector arama devre dışı)
    op.execute("""
        DO $$
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector extension kurulamadı, embedding_vec kolonu atlanacak';
        END
        $$;
    """)

    op.create_table(
        "project_knowledge",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        # JSON string olarak embedding (Ollama nomic-embed-text, 768 boyut)
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        # feature_file | execution | insight | docs | code_change | error_pattern
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_project_knowledge_source", "project_knowledge", ["source"])
    op.create_index("ix_project_knowledge_created_at", "project_knowledge", ["created_at"])

    # Native vector kolonu için ayrı ALTER (pgvector kuruluysa)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
                ALTER TABLE project_knowledge
                    ADD COLUMN IF NOT EXISTS embedding_vec vector(768);
                CREATE INDEX IF NOT EXISTS ix_knowledge_embedding_vec
                    ON project_knowledge
                    USING ivfflat (embedding_vec vector_cosine_ops)
                    WITH (lists = 50);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.drop_table("project_knowledge")
