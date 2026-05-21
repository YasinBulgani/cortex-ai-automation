"""Add notification_prefs table

Revision ID: notif_prefs_0001
Revises: sched_mobile_0001
Create Date: 2026-04-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "notif_prefs_0001"
down_revision = "sched_mobile_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "notification_prefs" in inspector.get_table_names():
        return

    op.create_table(
        "notification_prefs",
        sa.Column("user_id", sa.UUID(as_uuid=False), sa.ForeignKey("sd_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("notify_on_complete", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_on_failure", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("slack_webhook_url", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_prefs")
