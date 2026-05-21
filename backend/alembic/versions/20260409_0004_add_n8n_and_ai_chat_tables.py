"""Add tspm_n8n_workflows, tspm_n8n_executions, ai_chat_sessions, ai_chat_messages tables

Revision ID: missing_tables_0004
Revises: user_profile_0003
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "missing_tables_0004"
down_revision = "user_profile_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tspm_n8n_workflows ────────────────────────────────────────────────
    op.create_table(
        "tspm_n8n_workflows",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False),
                  sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("n8n_workflow_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True, default=""),
        sa.Column("trigger_on", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("webhook_path", sa.String(500), nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_tspm_n8n_workflows_project_id", "tspm_n8n_workflows", ["project_id"])

    # ── tspm_n8n_executions ───────────────────────────────────────────────
    op.create_table(
        "tspm_n8n_executions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("workflow_link_id", UUID(as_uuid=False),
                  sa.ForeignKey("tspm_n8n_workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("n8n_execution_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tspm_n8n_executions_workflow_link_id", "tspm_n8n_executions", ["workflow_link_id"])

    # ── ai_chat_sessions ──────────────────────────────────────────────────
    op.create_table(
        "ai_chat_sessions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=False),
                  sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False),
                  sa.ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default="Yeni Sohbet"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_ai_chat_sessions_project_id", "ai_chat_sessions", ["project_id"])
    op.create_index("ix_ai_chat_sessions_user_id", "ai_chat_sessions", ["user_id"])

    # ── ai_chat_messages ──────────────────────────────────────────────────
    op.create_table(
        "ai_chat_messages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=False),
                  sa.ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_ai_chat_messages_session_id", "ai_chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_table("ai_chat_messages")
    op.drop_table("ai_chat_sessions")
    op.drop_table("tspm_n8n_executions")
    op.drop_table("tspm_n8n_workflows")
