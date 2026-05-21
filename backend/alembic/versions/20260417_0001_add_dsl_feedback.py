"""Add sd_dsl_feedback table

DSL sözlüğü arama sonuçları için kullanıcıdan gelen 👍 / 👎 geri bildirimleri.
Bu kayıtlar ileride skor rerank ve "otomatik alias aday üretme" akışı için
sinyal görevi görür.

Revision ID: dsl_feedback_0001
Revises: 20260417_0010
Create Date: 2026-04-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "dsl_feedback_0001"
down_revision = "20260417_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "sd_dsl_feedback" in inspector.get_table_names():
        return

    op.create_table(
        "sd_dsl_feedback",
        sa.Column(
            "id", sa.UUID(as_uuid=False), primary_key=True, nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("sd_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("vote", sa.String(length=16), nullable=False),
        sa.Column("search_mode", sa.String(length=32), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("raw_score", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_sd_dsl_feedback_user_id", "sd_dsl_feedback", ["user_id"]
    )
    op.create_index(
        "ix_sd_dsl_feedback_query", "sd_dsl_feedback", ["query"]
    )
    op.create_index(
        "ix_sd_dsl_feedback_action_id", "sd_dsl_feedback", ["action_id"]
    )
    op.create_index(
        "ix_sd_dsl_feedback_created_at", "sd_dsl_feedback", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_sd_dsl_feedback_created_at", table_name="sd_dsl_feedback")
    op.drop_index("ix_sd_dsl_feedback_action_id", table_name="sd_dsl_feedback")
    op.drop_index("ix_sd_dsl_feedback_query", table_name="sd_dsl_feedback")
    op.drop_index("ix_sd_dsl_feedback_user_id", table_name="sd_dsl_feedback")
    op.drop_table("sd_dsl_feedback")
