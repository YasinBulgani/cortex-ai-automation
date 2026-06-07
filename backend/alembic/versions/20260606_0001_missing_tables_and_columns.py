"""add_missing_tables_and_columns

Kapsamlı QA analizi sonucunda tespit edilen eksik tablolar ve sütunlar:
  - cicd_webhook_events     → CICD domain GET /events 500 hatası
  - notification_prefs      → Notifications domain GET /prefs 500 hatası
  - prompts                 → Prompts domain GET /prompts 500 hatası
  - prompt_versions         → Prompts servis
  - prompt_rollouts         → Prompts servis
  - tspm_synthetic_*        → Synthetic platform domain 500 hatası
  - external_source col     → test_management_requirements eksik sütun

Revision ID: 20260606_0001
Revises: c56588566379
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "20260606_0001"
down_revision: Union[str, None] = "c56588566379"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. cicd_webhook_events ─────────────────────────────────────────────
    op.create_table(
        "cicd_webhook_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("project_ref", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("payload_summary", postgresql.JSONB(), nullable=True),
        sa.Column("commit_sha", sa.String(64), nullable=True),
        sa.Column("branch", sa.String(255), nullable=True),
        sa.Column("repo_name", sa.String(255), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_cicd_webhook_events_received_at",
        "cicd_webhook_events",
        ["received_at"],
    )

    # ── 2. notification_prefs ──────────────────────────────────────────────
    op.create_table(
        "notification_prefs",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("sd_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("notify_on_complete", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_failure", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        sa.Column(
            "digest_mode",
            sa.String(32),
            nullable=False,
            server_default="instant",
        ),
        sa.Column(
            "channels",
            sa.String(64),
            nullable=False,
            server_default="email,in_app",
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 3. prompts + prompt_versions + prompt_rollouts ─────────────────────
    op.create_table(
        "prompts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(64), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.String(36), primary_key=True, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column(
            "prompt_id",
            sa.String(64),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("user_template", sa.Text(), nullable=True),
        sa.Column("model_hint", sa.String(128), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("prompt_id", "version", name="uq_prompt_versions_prompt_version"),
    )

    op.create_table(
        "prompt_rollouts",
        sa.Column(
            "prompt_id",
            sa.String(64),
            sa.ForeignKey("prompts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("env", sa.String(32), nullable=False),
        sa.Column("active_version", sa.Integer(), nullable=True),
        sa.Column("canary_version", sa.Integer(), nullable=True),
        sa.Column("canary_pct", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("prompt_id", "env"),
    )

    # ── 4. tspm_synthetic_* tables ─────────────────────────────────────────
    op.create_table(
        "tspm_synthetic_projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True, server_default=""),
        sa.Column("owner_id", sa.String(64), nullable=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "tspm_synthetic_detected_schemas",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("tspm_synthetic_projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=True, server_default="csv"),
        sa.Column("source_info", sa.Text(), nullable=True, server_default=""),
        sa.Column("row_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("columns", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("relationships", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("pii_summary", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "tspm_synthetic_generation_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "schema_id",
            sa.String(36),
            sa.ForeignKey("tspm_synthetic_detected_schemas.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("column_name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("rule_config", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("learned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "tspm_synthetic_generation_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("tspm_synthetic_projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("schema_ids", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("row_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("scenario", sa.String(100), nullable=True, server_default="default"),
        sa.Column("format", sa.String(20), nullable=True, server_default="csv"),
        sa.Column("status", sa.String(20), nullable=True, server_default="pending"),
        sa.Column("result_path", sa.Text(), nullable=True, server_default=""),
        sa.Column("generated_data_preview", postgresql.JSONB(), nullable=True, server_default="[]"),
        sa.Column("duration_ms", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── 5. test_management_requirements.external_source sütunu ────────────
    # Sütunun yokluğu GET /requirements 500'e neden oluyor
    conn = op.get_bind()
    res = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='test_management_requirements' AND column_name='external_source'"
        )
    )
    if res.fetchone() is None:
        op.add_column(
            "test_management_requirements",
            sa.Column(
                "external_source",
                sa.String(32),
                nullable=False,
                server_default="internal",
            ),
        )
        # external_key sütunu da model'de mevcut — varsa ekleme
        res2 = conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='test_management_requirements' AND column_name='external_key'"
            )
        )
        if res2.fetchone() is None:
            op.add_column(
                "test_management_requirements",
                sa.Column("external_key", sa.String(128), nullable=True),
            )
            # Unique constraint ekle (varsa atla)
            try:
                op.create_unique_constraint(
                    "uq_tm_requirements_project_source_key",
                    "test_management_requirements",
                    ["project_id", "external_source", "external_key"],
                )
            except Exception:
                pass


def downgrade() -> None:
    # external_source sütununu kaldır
    try:
        op.drop_constraint("uq_tm_requirements_project_source_key", "test_management_requirements")
    except Exception:
        pass
    try:
        op.drop_column("test_management_requirements", "external_key")
    except Exception:
        pass
    try:
        op.drop_column("test_management_requirements", "external_source")
    except Exception:
        pass

    op.drop_table("tspm_synthetic_generation_history")
    op.drop_table("tspm_synthetic_generation_rules")
    op.drop_table("tspm_synthetic_detected_schemas")
    op.drop_table("tspm_synthetic_projects")
    op.drop_table("prompt_rollouts")
    op.drop_table("prompt_versions")
    op.drop_table("prompts")
    op.drop_table("notification_prefs")
    op.drop_index("ix_cicd_webhook_events_received_at", "cicd_webhook_events")
    op.drop_table("cicd_webhook_events")
