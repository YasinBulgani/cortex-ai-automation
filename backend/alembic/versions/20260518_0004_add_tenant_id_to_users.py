"""Add tenant_id to sd_users for multi-tenant RLS.

Revision ID: add_tenant_id_users_0001
Revises: automation_agents_merge_0001
Create Date: 2026-05-18

ADR: docs/adr/0005-multi-tenant-rls.md

Every user belongs to exactly one tenant. Existing users (single-tenant dev)
get the default local tenant UUID. Production users must have their tenant_id
set before enabling RLS on sd_users.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "add_tenant_id_users_0001"
down_revision: Union[str, None] = "automation_agents_merge_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # Add tenant_id with default so existing rows are backfilled
    op.add_column(
        "sd_users",
        sa.Column(
            "tenant_id",
            sa.String(36),
            nullable=False,
            server_default=_DEFAULT_TENANT,
        ),
    )
    op.create_index("ix_sd_users_tenant_id", "sd_users", ["tenant_id"])

    # Backfill any null rows (safety net, server_default should handle it)
    op.execute(
        f"UPDATE sd_users SET tenant_id = '{_DEFAULT_TENANT}' WHERE tenant_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_sd_users_tenant_id", table_name="sd_users")
    op.drop_column("sd_users", "tenant_id")
