"""add_mobile_sessions

Creates mobile_sessions — durable storage for mobile automation run records
(replaces the in-memory SessionStore; session history + step results survive
pod restart, and disk artifacts gain a queryable parent record). Steps stored
as JSONB. Global table, no RLS.

Revision ID: 20260608_0006
Revises: 20260608_0005
Create Date: 2026-06-08 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = '20260608_0006'
down_revision: Union[str, None] = '20260608_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mobile_sessions (
            id VARCHAR(32) PRIMARY KEY,
            device_id VARCHAR(64) NOT NULL,
            scenario_name TEXT NOT NULL DEFAULT '',
            status VARCHAR(16) NOT NULL DEFAULT 'queued',
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ,
            mode VARCHAR(16) NOT NULL DEFAULT 'simulation',
            failure_category VARCHAR(48),
            failure_message TEXT,
            healed INTEGER NOT NULL DEFAULT 0,
            steps JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_mobile_sessions_started "
        "ON mobile_sessions (started_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mobile_sessions")
