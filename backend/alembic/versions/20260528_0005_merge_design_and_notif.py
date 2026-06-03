"""Merge mgmt_design_techniques and notif_digest_channels branches

Revision ID: 20260528_0005
Revises: mgmt_design_tech_0001, notif_digest_0001
Create Date: 2026-05-28
"""
from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "20260528_0005"
down_revision: Union[str, tuple] = ("mgmt_design_tech_0001", "notif_digest_0001")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
