"""Organizations, Teams, Team/Project memberships, Invitations.

Revision ID: org_teams_0001
Revises: mgmt_notif_channel_0002
Create Date: 2026-05-28

Multi-team foundation:
- organizations: ust seviye tenant (mevcut tenant_id -> organization_id mapping)
- teams: bir organization icinde N takim
- team_members: kullanici <-> takim, rol bilgisi
- project_members: kullanici <-> proje, opsiyonel rol override
- tenant_invitations: email-bazli davet, token expire
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "org_teams_0001"
down_revision: Union[str, None] = "mgmt_notif_channel_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # ─── organizations ────────────────────────────────────────────
    op.create_table(
        "sd_organizations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("plan_code", sa.String(32), nullable=False, server_default="free"),
        sa.Column("settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Seed: default organization for the existing default tenant
    op.execute(
        f"""
        INSERT INTO sd_organizations (id, name, slug, plan_code)
        VALUES ('{_DEFAULT_TENANT}', 'Default Organization', 'default', 'free')
        ON CONFLICT (id) DO NOTHING
        """
    )

    # ─── teams ────────────────────────────────────────────────────
    op.create_table(
        "sd_teams",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organization_id", "slug", name="uq_team_org_slug"),
    )

    # ─── team_members ─────────────────────────────────────────────
    op.create_table(
        "sd_team_members",
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_teams.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_team_members_user", "sd_team_members", ["user_id"])

    # ─── project_members (project-level ACL override) ────────────
    op.create_table(
        "sd_project_members",
        sa.Column("project_id", sa.String(128), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_project_members_user", "sd_project_members", ["user_id"])

    # ─── tenant_invitations ──────────────────────────────────────
    op.create_table(
        "sd_invitations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "team_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "invited_by",
            UUID(as_uuid=False),
            sa.ForeignKey("sd_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_invitations_org_email", "sd_invitations", ["organization_id", "email"]
    )


def downgrade() -> None:
    op.drop_index("ix_invitations_org_email", table_name="sd_invitations")
    op.drop_table("sd_invitations")
    op.drop_index("ix_project_members_user", table_name="sd_project_members")
    op.drop_table("sd_project_members")
    op.drop_index("ix_team_members_user", table_name="sd_team_members")
    op.drop_table("sd_team_members")
    op.drop_table("sd_teams")
    op.drop_table("sd_organizations")
