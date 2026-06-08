"""add_exploration_sessions

Creates test_management_exploration_sessions for timeboxed exploratory testing
(charter + timer + free-form notes with inline bug capture).

Revision ID: 20260608_0003
Revises: 20260608_0002
Create Date: 2026-06-08 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = '20260608_0003'
down_revision: Union[str, None] = '20260608_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS test_management_exploration_sessions (
            id UUID PRIMARY KEY,
            project_id UUID NOT NULL REFERENCES test_management_projects(id) ON DELETE CASCADE,
            title VARCHAR(300) NOT NULL,
            charter TEXT,
            areas VARCHAR(500),
            environment VARCHAR(120),
            status VARCHAR(32) NOT NULL DEFAULT 'planned',
            timebox_minutes INTEGER NOT NULL DEFAULT 60,
            elapsed_seconds INTEGER NOT NULL DEFAULT 0,
            notes JSONB NOT NULL DEFAULT '[]',
            tester_id UUID REFERENCES sd_users(id) ON DELETE SET NULL,
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tm_exploration_project_created "
        "ON test_management_exploration_sessions (project_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tm_exploration_project_created")
    op.execute("DROP TABLE IF EXISTS test_management_exploration_sessions")
