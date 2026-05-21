"""sd_refresh_tokens tablosu — JWT refresh token depolama

Revision ID: refresh_tokens_0003
Revises: automation_artifacts_0007
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa

revision = "refresh_tokens_0003"
down_revision = "automation_artifacts_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent — tablo zaten varsa atla
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'sd_refresh_tokens'
            ) THEN
                CREATE TABLE sd_refresh_tokens (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES sd_users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(128) NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    revoked BOOLEAN DEFAULT FALSE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    user_agent TEXT
                );
            END IF;
        END $$;
    """)

    # Indexler — idempotent (IF NOT EXISTS)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON sd_refresh_tokens(user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON sd_refresh_tokens(token_hash)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sd_refresh_tokens")
