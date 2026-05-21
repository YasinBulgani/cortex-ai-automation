"""Automation Brain normalized run table.

Revision ID: automation_brain_runs_0001
Revises: ddd_contexts_0001
Create Date: 2026-05-18
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "automation_brain_runs_0001"
down_revision: Union[str, None] = "ddd_contexts_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sd_automation_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("project_id", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("trigger", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("environment", sa.String(120), nullable=True),
        sa.Column("device", sa.String(160), nullable=True),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("provenance", sa.String(32), nullable=False, server_default="fallback"),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("retry_of", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("next_action", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("run_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("idx_automation_runs_project_created", "sd_automation_runs", ["project_id", "created_at"])
    op.create_index("idx_automation_runs_kind_status", "sd_automation_runs", ["kind", "status"])
    op.create_index("idx_automation_runs_status", "sd_automation_runs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_automation_runs_status", table_name="sd_automation_runs")
    op.drop_index("idx_automation_runs_kind_status", table_name="sd_automation_runs")
    op.drop_index("idx_automation_runs_project_created", table_name="sd_automation_runs")
    op.drop_table("sd_automation_runs")
