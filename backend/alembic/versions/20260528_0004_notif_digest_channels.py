"""Notification prefs: digest_mode + channels.

Revision ID: notif_digest_0001
Revises: org_teams_0001
Create Date: 2026-05-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "notif_digest_0001"
down_revision: Union[str, None] = "org_teams_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_prefs",
        sa.Column(
            "digest_mode", sa.String(32), nullable=False, server_default="instant"
        ),
    )
    op.add_column(
        "notification_prefs",
        sa.Column(
            "channels",
            sa.String(64),
            nullable=False,
            server_default="email,in_app",
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_prefs", "channels")
    op.drop_column("notification_prefs", "digest_mode")
