"""tspm_flows: add template_id, agent_type, tags columns

Revision ID: 20260524_0001
Revises: b4682f9d1d6c
Create Date: 2026-05-24

These columns align the DB model with the frontend flow-designer create payload
(template_id, agent_type, tags) so the fields are persisted rather than silently
dropped.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = "20260524_0001"
down_revision = "b4682f9d1d6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tspm_flows",
        sa.Column("template_id", sa.String(128), nullable=True, server_default=None),
    )
    op.add_column(
        "tspm_flows",
        sa.Column("agent_type", sa.String(64), nullable=True, server_default=None),
    )
    op.add_column(
        "tspm_flows",
        sa.Column("tags", JSONB, nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("tspm_flows", "tags")
    op.drop_column("tspm_flows", "agent_type")
    op.drop_column("tspm_flows", "template_id")
