"""Nexus Repo module: 11 nexus_* tablosu

Revision ID: nexus_repo_0001
Revises: agents_v2_0001
Create Date: 2026-04-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "nexus_repo_0001"
down_revision = "agents_v2_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. nexus_projects ────────────────────────────────────────────
    op.create_table(
        "nexus_projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("repo_url", sa.String(1000), nullable=False),
        sa.Column("repo_type", sa.String(50), nullable=False, server_default="git"),
        sa.Column("branch", sa.String(200), nullable=False, server_default="main"),
        sa.Column("credential_ref", sa.String(500), nullable=True),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default="ollama"),
        sa.Column("llm_model", sa.String(100), nullable=False, server_default="qwen2.5:32b"),
        sa.Column("archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── 2. nexus_crawl_jobs ──────────────────────────────────────────
    op.create_table(
        "nexus_crawl_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("commit_sha", sa.String(100), nullable=True),
        sa.Column("files_scanned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("endpoints_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_crawl_jobs_project_id", "nexus_crawl_jobs", ["project_id"])

    # ── 3. nexus_files ───────────────────────────────────────────────
    op.create_table(
        "nexus_files",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("crawl_job_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_crawl_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(2000), nullable=False),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tokens_estimate", sa.Integer, nullable=False, server_default="0"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_files_crawl_job_id", "nexus_files", ["crawl_job_id"])

    # ── 4. nexus_endpoints ───────────────────────────────────────────
    op.create_table(
        "nexus_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("crawl_job_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_crawl_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(2000), nullable=False),
        sa.Column("source_file", sa.String(2000), nullable=True),
        sa.Column("source_line", sa.Integer, nullable=True),
        sa.Column("request_schema", postgresql.JSONB, nullable=True),
        sa.Column("response_schema", postgresql.JSONB, nullable=True),
        sa.Column("auth_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tags", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_endpoints_crawl_job_id", "nexus_endpoints", ["crawl_job_id"])

    # ── 5. nexus_scenarios ───────────────────────────────────────────
    op.create_table(
        "nexus_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("feature_area", sa.String(200), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("gherkin", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("llm_prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("llm_completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_scenarios_project_id", "nexus_scenarios", ["project_id"])

    # ── 6. nexus_cases ───────────────────────────────────────────────
    op.create_table(
        "nexus_cases",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("preconditions", sa.Text, nullable=True),
        sa.Column("steps", postgresql.JSONB, nullable=True),
        sa.Column("expected_result", sa.Text, nullable=True),
        sa.Column("test_data", postgresql.JSONB, nullable=True),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_cases_scenario_id", "nexus_cases", ["scenario_id"])

    # ── 7. nexus_exports ─────────────────────────────────────────────
    op.create_table(
        "nexus_exports",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(30), nullable=False),
        sa.Column("file_path", sa.String(2000), nullable=True),
        sa.Column("scenario_ids", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_exports_project_id", "nexus_exports", ["project_id"])

    # ── 8. nexus_llm_logs ────────────────────────────────────────────
    op.create_table(
        "nexus_llm_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_llm_logs_project_id", "nexus_llm_logs", ["project_id"])

    # ── 9. nexus_labels ──────────────────────────────────────────────
    op.create_table(
        "nexus_labels",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#6366f1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_labels_scenario_id", "nexus_labels", ["scenario_id"])

    # ── 10. nexus_comments ───────────────────────────────────────────
    op.create_table(
        "nexus_comments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_comments_scenario_id", "nexus_comments", ["scenario_id"])

    # ── 11. nexus_settings ───────────────────────────────────────────
    op.create_table(
        "nexus_settings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nexus_settings_project_id", "nexus_settings", ["project_id"])


def downgrade() -> None:
    op.drop_table("nexus_settings")
    op.drop_table("nexus_comments")
    op.drop_table("nexus_labels")
    op.drop_table("nexus_llm_logs")
    op.drop_table("nexus_exports")
    op.drop_table("nexus_cases")
    op.drop_table("nexus_scenarios")
    op.drop_table("nexus_endpoints")
    op.drop_table("nexus_files")
    op.drop_table("nexus_crawl_jobs")
    op.drop_table("nexus_projects")
