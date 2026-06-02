"""Add `channel` column to mgmt_notifications.

Adds the M-45 delivery-channel field (in_app | email | push | slack | teams)
and a composite ``(user_id, channel)`` index so per-channel inbox queries
remain selective.

Revision ID: mgmt_notif_channel_0002
Revises: mgmt_comments_notif_0001
Create Date: 2026-05-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "mgmt_notif_channel_0002"
down_revision: str = "mgmt_comments_notif_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE mgmt_notifications ADD COLUMN IF NOT EXISTS channel VARCHAR(32) NOT NULL DEFAULT 'in_app'")
    op.create_index("ix_mgmt_notif_user_channel", "mgmt_notifications", ["user_id", "channel"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_mgmt_notif_user_channel", table_name="mgmt_notifications")
    op.drop_column("mgmt_notifications", "channel")
