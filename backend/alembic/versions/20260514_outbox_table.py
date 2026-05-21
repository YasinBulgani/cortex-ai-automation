"""Outbox tablosu — reliable domain event delivery.

Revision ID: outbox_0001
Revises: b4682f9d1d6c
Create Date: 2026-05-14

ADR: docs/adr/0004-outbox-pattern-events.md
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "outbox_0001"
down_revision: Union[str, None] = "b4682f9d1d6c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(200), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )

    # Pending fetch için partial index — sadece pending/failed entry'leri tara
    op.create_index(
        "idx_outbox_pending",
        "outbox",
        ["status", "created_at"],
        postgresql_where=sa.text("status IN ('pending', 'failed')"),
    )

    # Debugging için aggregate lookup
    op.create_index("idx_outbox_aggregate", "outbox", ["aggregate_id"])

    # Event type filter (subscriber bazlı query)
    op.create_index("idx_outbox_event_type", "outbox", ["event_type"])

    # Check constraint: valid status values
    op.execute("""
        ALTER TABLE outbox ADD CONSTRAINT chk_outbox_status
        CHECK (status IN ('pending', 'processing', 'delivered', 'failed', 'dead'))
    """)


def downgrade() -> None:
    op.drop_index("idx_outbox_event_type", table_name="outbox")
    op.drop_index("idx_outbox_aggregate", table_name="outbox")
    op.drop_index("idx_outbox_pending", table_name="outbox")
    op.drop_table("outbox")
