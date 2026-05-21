"""Add sd_dsl_edit_proposals + sd_dsl_catalog_audit tables

DSL Sözlüğü editör akışı için öneri ve denetim kayıt tabloları.

    sd_dsl_edit_proposals   — human/AI düzenleme önerileri (pending → merged)
    sd_dsl_catalog_audit    — başarıyla YAML'e işlenen her değişikliğin izi

Revision ID: dsl_edit_0001
Revises: dsl_feedback_0001
Create Date: 2026-04-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "dsl_edit_0001"
down_revision = "dsl_feedback_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "sd_dsl_edit_proposals" not in existing:
        op.create_table(
            "sd_dsl_edit_proposals",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("action_id", sa.String(length=128), nullable=False),
            sa.Column(
                "proposer_id",
                sa.UUID(as_uuid=False),
                sa.ForeignKey("sd_users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "proposer_kind",
                sa.String(length=16),
                nullable=False,
                server_default="human",
            ),
            sa.Column("operation", sa.String(length=16), nullable=False),
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("diff", JSONB(), nullable=False),
            sa.Column("ai_reasoning", sa.Text(), nullable=True),
            sa.Column("base_commit_sha", sa.String(length=40), nullable=True),
            sa.Column("branch", sa.String(length=256), nullable=True),
            sa.Column("commit_sha", sa.String(length=40), nullable=True),
            sa.Column("pr_url", sa.String(length=512), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "reviewer_id",
                sa.UUID(as_uuid=False),
                sa.ForeignKey("sd_users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reviewer_note", sa.Text(), nullable=True),
            sa.Column(
                "reviewed_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_sd_dsl_edit_proposals_action_id",
            "sd_dsl_edit_proposals",
            ["action_id"],
        )
        op.create_index(
            "ix_sd_dsl_edit_proposals_proposer_id",
            "sd_dsl_edit_proposals",
            ["proposer_id"],
        )
        op.create_index(
            "ix_sd_dsl_edit_proposals_status",
            "sd_dsl_edit_proposals",
            ["status"],
        )
        op.create_index(
            "ix_sd_dsl_edit_proposals_created_at",
            "sd_dsl_edit_proposals",
            ["created_at"],
        )

    if "sd_dsl_catalog_audit" not in existing:
        op.create_table(
            "sd_dsl_catalog_audit",
            sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
            sa.Column("action_id", sa.String(length=128), nullable=False),
            sa.Column("operation", sa.String(length=16), nullable=False),
            sa.Column(
                "actor_id",
                sa.UUID(as_uuid=False),
                sa.ForeignKey("sd_users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "proposal_id",
                sa.UUID(as_uuid=False),
                sa.ForeignKey("sd_dsl_edit_proposals.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("commit_sha", sa.String(length=40), nullable=True),
            sa.Column("pr_url", sa.String(length=512), nullable=True),
            sa.Column("diff", JSONB(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_sd_dsl_catalog_audit_action_id",
            "sd_dsl_catalog_audit",
            ["action_id"],
        )
        op.create_index(
            "ix_sd_dsl_catalog_audit_created_at",
            "sd_dsl_catalog_audit",
            ["created_at"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_sd_dsl_catalog_audit_created_at", table_name="sd_dsl_catalog_audit"
    )
    op.drop_index(
        "ix_sd_dsl_catalog_audit_action_id", table_name="sd_dsl_catalog_audit"
    )
    op.drop_table("sd_dsl_catalog_audit")

    op.drop_index(
        "ix_sd_dsl_edit_proposals_created_at", table_name="sd_dsl_edit_proposals"
    )
    op.drop_index(
        "ix_sd_dsl_edit_proposals_status", table_name="sd_dsl_edit_proposals"
    )
    op.drop_index(
        "ix_sd_dsl_edit_proposals_proposer_id", table_name="sd_dsl_edit_proposals"
    )
    op.drop_index(
        "ix_sd_dsl_edit_proposals_action_id", table_name="sd_dsl_edit_proposals"
    )
    op.drop_table("sd_dsl_edit_proposals")
