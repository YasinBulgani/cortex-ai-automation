"""Add agents/v2 tables — sd_agent_v2_runs, sd_locators, sd_healing_attempts

LangGraph tabanlı 9 ajanlı orchestrator için kalıcı veri tabloları.

Revision ID: agents_v2_0001
Revises: dsl_edit_0001
Create Date: 2026-04-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "agents_v2_0001"
down_revision = "dsl_edit_0001"
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
            sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
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
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_agent_v2_runs_project_created", "sd_agent_v2_runs",
                        ["project_id", "created_at"])
        op.create_index("idx_agent_v2_runs_status", "sd_agent_v2_runs", ["status"])

    if "sd_locators" not in existing:
        op.create_table(
            "sd_locators",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.UUID(as_uuid=False), nullable=True, index=True),
            sa.Column("project_id", sa.UUID(as_uuid=False), nullable=False, index=True),
            sa.Column("url_pattern", sa.Text, nullable=False),
            sa.Column("element_fingerprint", sa.String(length=64), nullable=False),
            sa.Column("element_description", sa.Text, nullable=False),
            sa.Column("primary_strategy", sa.String(length=32), nullable=False),
            sa.Column("primary_selector", sa.Text, nullable=False),
            sa.Column("primary_playwright_expr", sa.Text, nullable=True),
            sa.Column("fallback_selectors", JSONB, nullable=False, server_default="[]"),
            sa.Column("stability_score", sa.Numeric(4, 3), nullable=False, server_default="0"),
            sa.Column("verify_success_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("verify_failure_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("embedding_json", JSONB, nullable=True,
                      comment="pgvector yerine JSONB fallback"),
            sa.Column("version", sa.Integer, nullable=False, server_default="1"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="pipeline"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint(
                "tenant_id", "project_id", "url_pattern", "element_fingerprint",
                name="uq_locators_tenant_project_url_element",
            ),
        )
        op.create_index("idx_locators_project_url", "sd_locators",
                        ["project_id", "url_pattern"])
        op.create_index("idx_locators_fingerprint", "sd_locators",
                        ["element_fingerprint"])

    if "sd_locator_history" not in existing:
        op.create_table(
            "sd_locator_history",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("locator_id", sa.UUID(as_uuid=False),
                      sa.ForeignKey("sd_locators.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("run_id", sa.UUID(as_uuid=False), nullable=True),
            sa.Column("success", sa.Boolean, nullable=False),
            sa.Column("selector_used", sa.Text, nullable=False),
            sa.Column("strategy_used", sa.String(length=32), nullable=False),
            sa.Column("duration_ms", sa.Integer, nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("idx_locator_history_locator_timestamp",
                        "sd_locator_history", ["locator_id", "timestamp"])

    if "sd_healing_attempts" not in existing:
        op.create_table(
            "sd_healing_attempts",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.UUID(as_uuid=False), nullable=True, index=True),
            sa.Column("project_id", sa.UUID(as_uuid=False), nullable=False, index=True),
            sa.Column("run_id", sa.UUID(as_uuid=False), nullable=True, index=True),
            sa.Column("test_id", sa.Text, nullable=False),
            sa.Column("failure_category", sa.String(length=32), nullable=False),
            sa.Column("broken_selector", sa.Text, nullable=True),
            sa.Column("element_description", sa.Text, nullable=True),
            sa.Column("hypotheses", JSONB, nullable=False, server_default="[]"),
            sa.Column("winner_strategy", sa.String(length=32), nullable=True),
            sa.Column("winner_selector", sa.Text, nullable=True),
            sa.Column("winner_score", sa.Numeric(4, 3), nullable=True),
            sa.Column("auto_merged", sa.Boolean, nullable=False,
                      server_default=sa.false()),
            sa.Column("hitl_required", sa.Boolean, nullable=False,
                      server_default=sa.false()),
            sa.Column("hitl_reason", sa.Text, nullable=True),
            sa.Column("pr_url", sa.Text, nullable=True),
            sa.Column("branch", sa.String(length=200), nullable=True),
            sa.Column("final_outcome", sa.String(length=32), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                      server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_healing_project_created",
                        "sd_healing_attempts", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_table("sd_healing_attempts")
    op.drop_table("sd_locator_history")
    op.drop_table("sd_locators")
    op.drop_table("sd_agent_v2_runs")
