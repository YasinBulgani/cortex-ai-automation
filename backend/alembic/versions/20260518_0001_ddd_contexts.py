"""DDD bounded context tabloları: iam_users, prj_projects, scn_scenarios.

Revision ID: ddd_contexts_0001
Revises: outbox_0001
Create Date: 2026-05-18

Kapsam:
  - identity context  → iam_users
  - projects context  → prj_projects
  - scenarios context → scn_scenarios (steps JSONB, prj_projects FK)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "ddd_contexts_0001"
down_revision: Union[str, None] = "outbox_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── identity: iam_users ───────────────────────────────────────────────────
    op.create_table(
        "iam_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("agg_version", sa.String(20), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_iam_users_email", "iam_users", ["email"], unique=True)
    op.create_index("ix_iam_users_is_active", "iam_users", ["is_active"])

    # ── projects: prj_projects ────────────────────────────────────────────────
    op.create_table(
        "prj_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_url", sa.String(2048), nullable=False, server_default=""),
        sa.Column("product_family", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("agg_version", sa.String(20), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_prj_projects_name", "prj_projects", ["name"], unique=True)
    op.create_index("ix_prj_projects_status", "prj_projects", ["status"])

    # ── scenarios: scn_scenarios ──────────────────────────────────────────────
    op.create_table(
        "scn_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("agg_version", sa.String(20), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["prj_projects.id"],
            name="fk_scn_scenarios_project_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_scn_scenarios_project_id", "scn_scenarios", ["project_id"])
    op.create_index("ix_scn_scenarios_status", "scn_scenarios", ["status"])


def downgrade() -> None:
    op.drop_table("scn_scenarios")
    op.drop_table("prj_projects")
    op.drop_table("iam_users")
