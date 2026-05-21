"""Add tspm_automation_artifacts table

Revision ID: automation_artifacts_0007
Revises: llm_traces_0002
Create Date: 2026-04-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "automation_artifacts_0007"
down_revision: Union[str, None] = "llm_traces_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("tspm_automation_artifacts"):
        op.create_table(
            "tspm_automation_artifacts",
            sa.Column("id", UUID(as_uuid=False), primary_key=True),
            sa.Column(
                "project_id",
                UUID(as_uuid=False),
                sa.ForeignKey("tspm_projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "batch_id",
                UUID(as_uuid=False),
                sa.ForeignKey("tspm_ai_batches.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("artifact_type", sa.String(32), nullable=False),
            sa.Column("feature_name", sa.String(300), nullable=False),
            sa.Column("filename", sa.String(300), nullable=False),
            sa.Column("storage_path", sa.String(512), nullable=False),
            sa.Column("mime_type", sa.String(128), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_test_case_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tspm_automation_artifacts_project_id
        ON tspm_automation_artifacts (project_id)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_tspm_automation_artifacts_project_id", table_name="tspm_automation_artifacts")
    op.drop_table("tspm_automation_artifacts")
