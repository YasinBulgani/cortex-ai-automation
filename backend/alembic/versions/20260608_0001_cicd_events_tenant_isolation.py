"""Add tenant_id to cicd_webhook_events for multi-tenant isolation.

Revision ID: 20260608_0001
Revises: f3990e7f3667
Create Date: 2026-06-08
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260608_0001"
down_revision: Union[str, None] = "f3990e7f3667"
branch_labels = None
depends_on = None

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.add_column(
        "cicd_webhook_events",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=True,
            comment="Tenant that owns this webhook event; NULL = legacy/system-level",
        ),
    )
    op.execute(
        f"UPDATE cicd_webhook_events SET tenant_id = '{_DEFAULT_TENANT}'::uuid WHERE tenant_id IS NULL"
    )
    op.create_index(
        "idx_cicd_events_tenant_id",
        "cicd_webhook_events",
        ["tenant_id", sa.literal_column("received_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_cicd_events_tenant_id", table_name="cicd_webhook_events")
    op.drop_column("cicd_webhook_events", "tenant_id")
