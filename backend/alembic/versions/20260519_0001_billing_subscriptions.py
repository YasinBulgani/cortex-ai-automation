"""Billing subscriptions and usage events.

Revision ID: billing_subscriptions_0001
Revises: add_tenant_id_users_0001
Create Date: 2026-05-19

Introduces:
    - billing_subscriptions: one row per tenant, tracks plan state.
    - billing_usage_events: append-only ledger of billable events.

Default plan is "free"; existing tenants get a free-tier subscription
auto-created on first billing API call (see service.get_or_create_subscription).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "billing_subscriptions_0001"
down_revision: Union[str, None] = "add_tenant_id_users_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("plan_code", sa.String(32), nullable=False, server_default="free"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("external_subscription_id", sa.String(128), nullable=True),
        sa.Column("external_customer_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("tenant_id", name="uq_billing_subscriptions_tenant"),
    )
    op.create_index(
        "ix_billing_subscriptions_tenant_id",
        "billing_subscriptions",
        ["tenant_id"],
    )

    op.create_table(
        "billing_usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(18, 6),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("meta", sa.String(2000), nullable=True),
    )
    op.create_index(
        "ix_billing_usage_events_tenant_id",
        "billing_usage_events",
        ["tenant_id"],
    )
    op.create_index(
        "ix_billing_usage_events_kind",
        "billing_usage_events",
        ["kind"],
    )
    op.create_index(
        "ix_billing_usage_events_occurred_at",
        "billing_usage_events",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_billing_usage_events_occurred_at", table_name="billing_usage_events")
    op.drop_index("ix_billing_usage_events_kind", table_name="billing_usage_events")
    op.drop_index("ix_billing_usage_events_tenant_id", table_name="billing_usage_events")
    op.drop_table("billing_usage_events")

    op.drop_index("ix_billing_subscriptions_tenant_id", table_name="billing_subscriptions")
    op.drop_table("billing_subscriptions")
