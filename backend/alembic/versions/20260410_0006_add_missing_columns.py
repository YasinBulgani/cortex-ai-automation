"""Add missing columns: tspm_scenarios.tags, tspm_ai_batches, tspm_test_cases

Revision ID: missing_cols_0006
Revises: approval_draft_0005
Create Date: 2026-04-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "missing_cols_0006"
down_revision: Union[str, None] = "approval_draft_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ── 1. tspm_scenarios: add tags column ──────────────────────────────
    if "tspm_scenarios" in existing_tables:
        scenario_columns = {col["name"] for col in inspector.get_columns("tspm_scenarios")}
        if "tags" not in scenario_columns:
            op.add_column(
                "tspm_scenarios",
                sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )

    # ── 2. tspm_ai_batches ──────────────────────────────────────────────
    if "tspm_ai_batches" not in existing_tables:
        op.create_table(
            "tspm_ai_batches",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True),
            sa.Column("project_id", sa.UUID(as_uuid=False),
                      sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source_type", sa.String(32), nullable=False, server_default="document"),
            sa.Column("source_name", sa.String(500), nullable=True),
            sa.Column("source_text_preview", sa.Text(), nullable=True),
            sa.Column("ai_provider", sa.String(64), nullable=True),
            sa.Column("ai_model", sa.String(128), nullable=True),
            sa.Column("extra_instructions", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="generating"),
            sa.Column("total_generated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("approved_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rejected_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )

    # ── 3. tspm_test_cases ──────────────────────────────────────────────
    if "tspm_test_cases" not in existing_tables:
        op.create_table(
            "tspm_test_cases",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True),
            sa.Column("project_id", sa.UUID(as_uuid=False),
                      sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("batch_id", sa.UUID(as_uuid=False),
                      sa.ForeignKey("tspm_ai_batches.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("module_name", sa.String(200), nullable=True),
            sa.Column("feature_area", sa.String(200), nullable=True),
            sa.Column("test_type", sa.String(64), nullable=False, server_default="functional"),
            sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
            sa.Column("risk_level", sa.String(32), nullable=False, server_default="medium"),
            sa.Column("preconditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("expected_result", sa.Text(), nullable=True),
            sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("review_status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("reviewer_note", sa.Text(), nullable=True),
            sa.Column("scenario_id", sa.UUID(as_uuid=False),
                      sa.ForeignKey("tspm_scenarios.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("tspm_test_cases")
    op.drop_table("tspm_ai_batches")
    op.drop_column("tspm_scenarios", "tags")
