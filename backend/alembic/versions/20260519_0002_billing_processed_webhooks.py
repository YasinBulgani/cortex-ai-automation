"""Processed-webhook idempotency table for Stripe events.

Revision ID: billing_processed_webhooks_0001
Revises: billing_subscriptions_0001
Create Date: 2026-05-19

One row per Stripe event we have handled. The webhook handler does an
INSERT before applying side effects; conflict means we have already
processed this event and the request is a Stripe retry.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "billing_processed_webhooks_0001"
down_revision: Union[str, None] = "billing_subscriptions_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_processed_webhooks",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_billing_processed_webhooks_event_type",
        "billing_processed_webhooks",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_processed_webhooks_event_type",
        table_name="billing_processed_webhooks",
    )
    op.drop_table("billing_processed_webhooks")
