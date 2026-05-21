"""agents/v2 workflow durability tables.

Revision ID: agents_v2_workflow_durability_0001
Revises: mt_rls_0001
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "agents_v2_workflow_durability_0001"
down_revision = "mt_rls_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "sd_agent_v2_runs" not in existing:
        op.create_table(
            "sd_agent_v2_runs",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.UUID(as_uuid=False), nullable=True, index=True),
            sa.Column("project_id", sa.UUID(as_uuid=False), nullable=False, index=True),
            sa.Column("user_id", sa.UUID(as_uuid=False), nullable=True),
            sa.Column("input_source", sa.String(length=32), nullable=False),
            sa.Column("input_payload", JSONB, nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("workflow_type", sa.String(length=64), nullable=True),
            sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("intent_graph", JSONB, nullable=True),
            sa.Column("app_map", JSONB, nullable=True),
            sa.Column("scenarios", JSONB, nullable=True),
            sa.Column("generated_code", JSONB, nullable=True),
            sa.Column("run_result", JSONB, nullable=True),
            sa.Column("healing_result", JSONB, nullable=True),
            sa.Column("review", JSONB, nullable=True),
            sa.Column("report", JSONB, nullable=True),
            sa.Column("errors", JSONB, nullable=False, server_default="[]"),
            sa.Column("tokens_used", sa.BigInteger, nullable=False, server_default="0"),
            sa.Column("llm_calls_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0"),
            sa.Column("duration_seconds", sa.Numeric(10, 3), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "idx_agent_v2_runs_project_created",
            "sd_agent_v2_runs",
            ["project_id", "created_at"],
        )
        op.create_index("idx_agent_v2_runs_status", "sd_agent_v2_runs", ["status"])

    op.execute("ALTER TABLE sd_agent_v2_runs ADD COLUMN IF NOT EXISTS workflow_type VARCHAR(64)")
    op.execute(
        "ALTER TABLE sd_agent_v2_runs ADD COLUMN IF NOT EXISTS dry_run BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        """
        ALTER TABLE sd_agent_v2_runs
            ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute("ALTER TABLE sd_agent_v2_runs ADD COLUMN IF NOT EXISTS error_message TEXT")
    op.execute(
        """
        ALTER TABLE sd_agent_v2_runs
            ALTER COLUMN status TYPE VARCHAR(32)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_agent_v2_run_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID NOT NULL REFERENCES sd_agent_v2_runs(id) ON DELETE CASCADE,
            event_type VARCHAR(64) NOT NULL,
            agent_name VARCHAR(64),
            message TEXT,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_run_events_run_created
        ON sd_agent_v2_run_events(run_id, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_run_events_type
        ON sd_agent_v2_run_events(event_type)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_agent_v2_run_artifacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID NOT NULL REFERENCES sd_agent_v2_runs(id) ON DELETE CASCADE,
            kind VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            storage_path VARCHAR(1024) NOT NULL,
            mime_type VARCHAR(128) NOT NULL DEFAULT 'application/octet-stream',
            size_bytes BIGINT NOT NULL DEFAULT 0,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(run_id, kind, storage_path)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_run_artifacts_run_created
        ON sd_agent_v2_run_artifacts(run_id, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_run_artifacts_kind
        ON sd_agent_v2_run_artifacts(kind)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_agent_v2_run_approvals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID NOT NULL REFERENCES sd_agent_v2_runs(id) ON DELETE CASCADE,
            actor_user_id UUID,
            decision VARCHAR(32) NOT NULL,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_run_approvals_run_created
        ON sd_agent_v2_run_approvals(run_id, created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sd_agent_v2_dead_letters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id UUID,
            queue_name VARCHAR(128) NOT NULL,
            reason VARCHAR(128) NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            retry_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_dead_letters_queue_created
        ON sd_agent_v2_dead_letters(queue_name, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_v2_dead_letters_run
        ON sd_agent_v2_dead_letters(run_id) WHERE run_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sd_agent_v2_dead_letters")
    op.execute("DROP TABLE IF EXISTS sd_agent_v2_run_approvals")
    op.execute("DROP TABLE IF EXISTS sd_agent_v2_run_artifacts")
    op.execute("DROP TABLE IF EXISTS sd_agent_v2_run_events")
    op.execute("ALTER TABLE sd_agent_v2_runs DROP COLUMN IF EXISTS error_message")
    op.execute("ALTER TABLE sd_agent_v2_runs DROP COLUMN IF EXISTS requires_approval")
    op.execute("ALTER TABLE sd_agent_v2_runs DROP COLUMN IF EXISTS dry_run")
    op.execute("ALTER TABLE sd_agent_v2_runs DROP COLUMN IF EXISTS workflow_type")
