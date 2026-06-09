"""Event Streaming Infrastructure — Kafka/Redis foundation (Faz 3.5).

Revision ID: event_streaming_0001
Revises: Previous migration
Create Date: 2026-06-09

Tables:
- stream_events: Published event audit trail
- consumer_group_offsets: Offset backup for recovery
- consumer_group_metrics: Time-series metrics
- event_subscriptions: Consumer routing config
- event_dlq: Dead-letter queue
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "event_streaming_0001"
down_revision: Union[str, None] = "outbox_0001"  # After outbox table
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # stream_events: Published event audit trail
    op.create_table(
        "stream_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("schema_name", sa.String(255), nullable=False),
        sa.Column("schema_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.Column("event_id", sa.String(255), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("broker", sa.String(50), nullable=False),  # "kafka" | "redis"
        sa.Column("broker_message_id", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )
    op.create_index("idx_stream_events_topic", "stream_events", ["topic"])
    op.create_index("idx_stream_events_tenant", "stream_events", ["tenant_id"])
    op.create_index("idx_stream_events_status", "stream_events", ["status"])
    op.create_index("idx_stream_events_published", "stream_events", ["published_at"])
    op.create_index("idx_stream_events_created", "stream_events", ["created_at"])

    # consumer_group_offsets: Offset backup for recovery
    op.create_table(
        "consumer_group_offsets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("partition", sa.Integer, nullable=True),
        sa.Column("broker", sa.String(50), nullable=False),
        sa.Column("committed_offset", sa.String(255), nullable=False),
        sa.Column("lag", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )
    op.create_index(
        "idx_consumer_group_topic",
        "consumer_group_offsets",
        ["group_id", "topic", "partition"],
    )
    op.create_index("idx_consumer_group_lag", "consumer_group_offsets", ["lag"])

    # consumer_group_metrics: Time-series metrics
    op.create_table(
        "consumer_group_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("group_id", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("partition", sa.Integer, nullable=True),
        sa.Column("lag", sa.Integer, nullable=False),
        sa.Column("processing_rate", sa.String(50), nullable=True),
        sa.Column("fetch_rate", sa.String(50), nullable=True),
        sa.Column("consumer_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "idx_consumer_metrics_group",
        "consumer_group_metrics",
        ["group_id", "created_at"],
    )
    op.create_index(
        "idx_consumer_metrics_topic",
        "consumer_group_metrics",
        ["topic", "created_at"],
    )

    # event_subscriptions: Consumer routing config
    op.create_table(
        "event_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("consumer_group_id", sa.String(255), nullable=False),
        sa.Column("handler_service", sa.String(255), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("filter_config", postgresql.JSONB, nullable=True),
        sa.Column("retry_max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("retry_backoff_ms", sa.Integer, nullable=False, server_default="1000"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_subscriptions_topic", "event_subscriptions", ["topic"])
    op.create_index("idx_subscriptions_enabled", "event_subscriptions", ["enabled"])

    # event_dlq: Dead-letter queue
    op.create_table(
        "event_dlq",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("original_offset", sa.String(255), nullable=True),
        sa.Column("consumer_group_id", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("error_reason", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("moved_to_dlq_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("resolution_notes", sa.Text, nullable=True),
    )
    op.create_index("idx_dlq_topic", "event_dlq", ["topic"])
    op.create_index("idx_dlq_resolved", "event_dlq", ["resolved"])
    op.create_index("idx_dlq_created", "event_dlq", ["moved_to_dlq_at"])


def downgrade() -> None:
    op.drop_index("idx_dlq_created", table_name="event_dlq")
    op.drop_index("idx_dlq_resolved", table_name="event_dlq")
    op.drop_index("idx_dlq_topic", table_name="event_dlq")
    op.drop_table("event_dlq")

    op.drop_index("idx_subscriptions_enabled", table_name="event_subscriptions")
    op.drop_index("idx_subscriptions_topic", table_name="event_subscriptions")
    op.drop_table("event_subscriptions")

    op.drop_index(
        "idx_consumer_metrics_topic",
        table_name="consumer_group_metrics",
    )
    op.drop_index(
        "idx_consumer_metrics_group",
        table_name="consumer_group_metrics",
    )
    op.drop_table("consumer_group_metrics")

    op.drop_index("idx_consumer_group_lag", table_name="consumer_group_offsets")
    op.drop_index(
        "idx_consumer_group_topic",
        table_name="consumer_group_offsets",
    )
    op.drop_table("consumer_group_offsets")

    op.drop_index("idx_stream_events_created", table_name="stream_events")
    op.drop_index("idx_stream_events_published", table_name="stream_events")
    op.drop_index("idx_stream_events_status", table_name="stream_events")
    op.drop_index("idx_stream_events_tenant", table_name="stream_events")
    op.drop_index("idx_stream_events_topic", table_name="stream_events")
    op.drop_table("stream_events")
