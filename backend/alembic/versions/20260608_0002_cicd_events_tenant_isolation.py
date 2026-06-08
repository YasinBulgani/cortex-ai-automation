"""Add tenant_id to cicd_webhook_events for multi-tenant isolation.

Revision ID: 20260608_0002
Revises: 20260608_0001
Create Date: 2026-06-08
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260608_0002"
down_revision: Union[str, None] = "20260608_0001"
branch_labels = None
depends_on = None

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.execute(
        "ALTER TABLE cicd_webhook_events ADD COLUMN IF NOT EXISTS tenant_id UUID"
    )
    op.execute(
        f"UPDATE cicd_webhook_events SET tenant_id = '{_DEFAULT_TENANT}'::uuid WHERE tenant_id IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cicd_events_tenant_id ON cicd_webhook_events (tenant_id, received_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_cicd_events_tenant_id")
    op.execute("ALTER TABLE cicd_webhook_events DROP COLUMN IF EXISTS tenant_id")
