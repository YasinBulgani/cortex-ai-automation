"""add_review_workflow_and_flakiness_to_cases

Adds review workflow state machine and flakiness tracking columns to test_management_cases.

Revision ID: 20260608_0001
Revises: 20260607_0002
Create Date: 2026-06-08 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '20260608_0001'
down_revision: Union[str, None] = '20260607_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Review workflow columns
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS review_status VARCHAR(32) NOT NULL DEFAULT 'none'")
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS review_by VARCHAR(36)")
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS review_at TIMESTAMPTZ")
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS review_comment TEXT")

    # Flakiness tracking columns
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS run_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS pass_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS fail_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE test_management_cases ADD COLUMN IF NOT EXISTS flakiness_score FLOAT NOT NULL DEFAULT 0")

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_tm_cases_review_status ON test_management_cases (review_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tm_cases_flakiness_score ON test_management_cases (project_id, flakiness_score)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tm_cases_flakiness_score")
    op.execute("DROP INDEX IF EXISTS ix_tm_cases_review_status")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS flakiness_score")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS fail_count")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS pass_count")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS run_count")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS review_comment")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS review_at")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS review_by")
    op.execute("ALTER TABLE test_management_cases DROP COLUMN IF EXISTS review_status")
