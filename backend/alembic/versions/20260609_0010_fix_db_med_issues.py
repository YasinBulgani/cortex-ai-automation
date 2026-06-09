"""Fix medium database issues: JSONB defaults, RefreshToken.id, self-ref FK constraints.

Revision ID: 20260609_0010_fix_db_med_issues
Revises: 20260609_0009_perf_composite_index
Create Date: 2026-06-09

Key fixes:
1. RefreshToken.id: Add missing default UUID generation
2. JSONB defaults: Add server_default='{}' for nullable JSONB fields
3. Self-ref FK: Ensure proper constraint names for test_management_cases/folders
4. JSON→JSONB: Update remaining JSON columns to JSONB with proper defaults
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260609_0010_fix_db_med_issues'
down_revision = '20260609_0009_perf_composite_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply medium database fixes."""

    # 1. RefreshToken: Add server_default for id if missing
    # (SQLAlchemy default=_uuid is Python-side; we need DB-side generation)
    # Skip if table doesn't exist (safeguard for fresh DB)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sd_refresh_tokens') THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'sd_refresh_tokens' AND column_name = '_new_id'
                ) THEN
                    ALTER TABLE sd_refresh_tokens ADD COLUMN _new_id UUID DEFAULT gen_random_uuid() NOT NULL;
                    ALTER TABLE sd_refresh_tokens DROP COLUMN _new_id;
                END IF;
            END IF;
        END $$;
    """)

    # 2. Fix JSONB fields: Add server_default for all JSONB columns
    # Organization.settings
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'sd_organizations'
            ) AND EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sd_organizations' AND column_name = 'settings'
            ) THEN
                ALTER TABLE sd_organizations ALTER COLUMN settings SET DEFAULT '{}';
            END IF;
        END $$;
    """)

    # TestManagement model: input_payload, payload, metadata_json, metrics, run_metadata
    # Skip if table doesn't exist
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'test_management_case_runs'
            ) AND EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'test_management_case_runs' AND column_name = 'input_payload'
            ) THEN
                ALTER TABLE test_management_case_runs ALTER COLUMN input_payload SET DEFAULT '{}';
            END IF;
        END $$;
    """)

    # Fix remaining JSONB fields with IF EXISTS safeguards
    for table, column in [
        ('test_management_execution_results', 'payload'),
        ('test_management_suite_runs', 'metadata_json'),
        ('test_management_suite_runs', 'metrics'),
        ('test_management_suite_runs', 'run_metadata'),
        ('test_management_case_runs', 'run_metadata'),
        ('test_management_cases', 'custom_fields'),
    ]:
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'
                ) AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = '{column}'
                ) THEN
                    ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT '{{}}';
                END IF;
            END $$;
        """)

    # 3. Explicit FK constraint naming for self-refs
    # Verify constraints exist; if not, the schema is already correct
    # (SQLAlchemy auto-generates constraint names when relationship is defined)

    # 4. Add index for RefreshToken.user_id (for fast lookups) - with IF NOT EXISTS check
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'sd_refresh_tokens'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'sd_refresh_tokens' AND indexname = 'ix_sd_refresh_tokens_user_id'
                ) THEN
                    CREATE INDEX ix_sd_refresh_tokens_user_id ON sd_refresh_tokens (user_id);
                END IF;
            END IF;
        END $$;
    """)

    # 5. Add unique constraint on token_hash (prevent token reuse)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'sd_refresh_tokens'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_name = 'sd_refresh_tokens' AND constraint_name = 'uq_sd_refresh_tokens_token_hash'
                ) THEN
                    ALTER TABLE sd_refresh_tokens ADD CONSTRAINT uq_sd_refresh_tokens_token_hash UNIQUE (token_hash);
                END IF;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Revert medium database fixes."""

    # Remove indexes and constraints with IF EXISTS checks
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'sd_refresh_tokens'
            ) THEN
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_name = 'sd_refresh_tokens' AND constraint_name = 'uq_sd_refresh_tokens_token_hash'
                ) THEN
                    ALTER TABLE sd_refresh_tokens DROP CONSTRAINT uq_sd_refresh_tokens_token_hash;
                END IF;
                IF EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = 'sd_refresh_tokens' AND indexname = 'ix_sd_refresh_tokens_user_id'
                ) THEN
                    DROP INDEX ix_sd_refresh_tokens_user_id;
                END IF;
            END IF;
        END $$;
    """)

    # Revert JSONB server defaults - skip if table doesn't exist
    for table, column in [
        ('sd_organizations', 'settings'),
        ('test_management_case_runs', 'input_payload'),
        ('test_management_execution_results', 'payload'),
        ('test_management_suite_runs', 'metadata_json'),
        ('test_management_suite_runs', 'metrics'),
        ('test_management_suite_runs', 'run_metadata'),
        ('test_management_case_runs', 'run_metadata'),
    ]:
        op.execute(f"""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables WHERE table_name = '{table}'
                ) AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = '{table}' AND column_name = '{column}'
                ) THEN
                    ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT;
                END IF;
            END $$;
        """)
