"""Session 4: comprehensive DB fixes - missing columns and nullable changes."""

from alembic import op
import sqlalchemy as sa

revision = '20260607_0001'
down_revision = '20260606_0006'
branch_labels = None
depends_on = None


def upgrade():
    # llm_traces — full schema columns expected by llm_trace.py
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS project_id UUID")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS phase VARCHAR(64)")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS system_prompt_preview TEXT")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS user_prompt_preview TEXT")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS response_preview TEXT")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS full_response_length INTEGER DEFAULT 0")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS temperature FLOAT")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS max_tokens INTEGER")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS error_message TEXT")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS json_parse_ok BOOLEAN")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS fallback_used BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS trace_metadata JSONB DEFAULT '{}'")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS cost_usd FLOAT")
    op.execute("ALTER TABLE llm_traces ADD COLUMN IF NOT EXISTS is_streaming BOOLEAN DEFAULT FALSE")

    # sd_organizations — profile columns
    op.execute("ALTER TABLE sd_organizations ADD COLUMN IF NOT EXISTS website VARCHAR(500)")
    op.execute("ALTER TABLE sd_organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR(1000)")
    op.execute("ALTER TABLE sd_organizations ADD COLUMN IF NOT EXISTS industry VARCHAR(100)")
    op.execute("ALTER TABLE sd_organizations ADD COLUMN IF NOT EXISTS size VARCHAR(50)")
    op.execute("ALTER TABLE sd_organizations ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'Europe/Istanbul'")

    # project_knowledge — metadata already exists, verified in session 4
    op.execute("ALTER TABLE project_knowledge ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'")

    # test_management_defect_links — make nullable
    op.execute("ALTER TABLE test_management_defect_links ALTER COLUMN run_case_id DROP NOT NULL")
    op.execute("ALTER TABLE test_management_defect_links ALTER COLUMN external_key DROP NOT NULL")

    # test_management_shared_steps — columns already exist, verified in session 4
    op.execute("ALTER TABLE test_management_shared_steps ADD COLUMN IF NOT EXISTS steps JSONB DEFAULT '[]'")
    op.execute("ALTER TABLE test_management_shared_steps ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'")
    op.execute("ALTER TABLE test_management_shared_steps ADD COLUMN IF NOT EXISTS usage_count INTEGER DEFAULT 0")


def downgrade():
    pass
