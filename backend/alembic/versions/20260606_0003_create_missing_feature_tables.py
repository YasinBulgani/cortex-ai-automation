"""create_missing_feature_tables

f3990e7f3667 migration'ı skip edildi (squash olduğu için çoğu tablo zaten mevcut).
Bu migration sadece gerçekten eksik olan tabloları oluşturur.

Revision ID: 20260606_0003
Revises: 20260606_0002
Create Date: 2026-06-06 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "20260606_0003"
down_revision: Union[str, None] = "20260606_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name: str) -> bool:
    res = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=:t"
        ),
        {"t": table_name},
    )
    return res.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── test_management_shared_steps ──────────────────────────────────────
    if not _table_exists(conn, "test_management_shared_steps"):
        op.create_table(
            "test_management_shared_steps",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
            sa.Column("project_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("action", sa.Text(), nullable=True),
            sa.Column("expected", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # ── cicd_jenkins_connections ───────────────────────────────────────────
    if not _table_exists(conn, "cicd_jenkins_connections"):
        op.create_table(
            "cicd_jenkins_connections",
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("base_url", sa.String(512), nullable=False),
            sa.Column("username", sa.String(128), nullable=True),
            sa.Column("api_token", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(36), nullable=True, index=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # ── api_healing_logs ───────────────────────────────────────────────────
    if not _table_exists(conn, "api_healing_logs"):
        op.create_table(
            "api_healing_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), nullable=False, index=True),
            sa.Column("run_id", sa.String(36), nullable=False),
            sa.Column("test_case_id", sa.String(36), nullable=False),
            sa.Column("healed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("original_request", postgresql.JSONB(), nullable=True),
            sa.Column("healed_request", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # ── heal_history ───────────────────────────────────────────────────────
    if not _table_exists(conn, "heal_history"):
        op.create_table(
            "heal_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(64), nullable=True),
            sa.Column("test_file", sa.String(512), nullable=True),
            sa.Column("test_name", sa.String(255), nullable=True),
            sa.Column("healed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("strategy", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # ── llm_traces ─────────────────────────────────────────────────────────
    if not _table_exists(conn, "llm_traces"):
        op.create_table(
            "llm_traces",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("session_id", sa.String(36), nullable=True, index=True),
            sa.Column("tenant_id", sa.String(36), nullable=True, index=True),
            sa.Column("model", sa.String(64), nullable=True),
            sa.Column("task_type", sa.String(64), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("latency_ms", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("status", sa.String(32), nullable=True, server_default="ok"),
            sa.Column("error_msg", sa.Text(), nullable=True),
            sa.Column("correlation_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # ── outbox (event outbox for reliability) ─────────────────────────────
    if not _table_exists(conn, "outbox"):
        op.create_table(
            "outbox",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )

    # ── project_knowledge ─────────────────────────────────────────────────
    if not _table_exists(conn, "project_knowledge"):
        op.create_table(
            "project_knowledge",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), nullable=False, index=True),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("source", sa.String(255), nullable=True),
            sa.Column("embedding", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )

    # ── tspm_wizard_snapshots ─────────────────────────────────────────────
    if not _table_exists(conn, "tspm_wizard_snapshots"):
        op.create_table(
            "tspm_wizard_snapshots",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("project_id", sa.String(36), nullable=False, index=True),
            sa.Column("data", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )


def downgrade() -> None:
    for table in [
        "tspm_wizard_snapshots",
        "project_knowledge",
        "outbox",
        "llm_traces",
        "heal_history",
        "api_healing_logs",
        "cicd_jenkins_connections",
        "test_management_shared_steps",
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass
