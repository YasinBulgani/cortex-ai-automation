"""Event Streaming Models — Database representations for streaming infrastructure."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, event, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StreamEventStatus(str, Enum):
    """Event streaming status."""
    PENDING = "pending"           # Waiting to be published
    PUBLISHED = "published"       # Successfully published
    CONSUMED = "consumed"         # Consumed by at least one consumer
    FAILED = "failed"             # Delivery/consumption failed
    DLQ = "dlq"                   # Moved to dead-letter queue


class StreamEvent(Base):
    """Track events published to streaming platforms.

    Complements outbox table (pre-publication event log).
    Used for audit trail, replay, metrics collection.
    """

    __tablename__ = "stream_events"

    id = UUID(as_uuid=True, primary_key=True, default=uuid4)
    topic = String(255, nullable=False)  # e.g., "auth.events"
    schema_name = String(255, nullable=False)  # e.g., "UserLoginEvent"
    schema_version = Integer(nullable=False, server_default="1")
    tenant_id = UUID(as_uuid=True, nullable=False)  # Multi-tenancy
    correlation_id = String(255, nullable=True)  # Request trace
    event_id = String(255, nullable=False, unique=True)  # Idempotency key
    payload = JSONB(nullable=False)  # Event data
    status = String(20, nullable=False, server_default=StreamEventStatus.PENDING.value)
    broker = String(50, nullable=False)  # "kafka" | "redis"
    broker_message_id = String(255, nullable=True)  # Offset/entry ID from broker
    published_at = DateTime(timezone=True, nullable=True)
    consumed_count = Integer(nullable=False, server_default="0")
    created_at = DateTime(timezone=True, nullable=False, server_default=func.now())
    updated_at = DateTime(timezone=True, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_stream_events_topic", "topic"),
        Index("idx_stream_events_tenant", "tenant_id"),
        Index("idx_stream_events_status", "status"),
        Index("idx_stream_events_published", "published_at"),
        Index("idx_stream_events_created", "created_at"),
    )


class ConsumerGroupOffset(Base):
    """Track consumer group offsets (exactly-once semantics).

    Backup for Kafka/Redis offset tracking in DB.
    Enables offset recovery after consumer restart.
    """

    __tablename__ = "consumer_group_offsets"

    id = UUID(as_uuid=True, primary_key=True, default=uuid4)
    group_id = String(255, nullable=False)  # Consumer group name
    topic = String(255, nullable=False)
    partition = Integer(nullable=True)  # Kafka partition, NULL for Redis
    broker = String(50, nullable=False)  # "kafka" | "redis"
    committed_offset = String(255, nullable=False)  # Offset or entry ID
    lag = Integer(nullable=False, server_default="0")
    last_heartbeat = DateTime(timezone=True, nullable=False, server_default=func.now())
    updated_at = DateTime(timezone=True, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_consumer_group_topic", ("group_id", "topic", "partition")),
        Index("idx_consumer_group_lag", "lag"),
    )


class ConsumerGroupMetrics(Base):
    """Time-series metrics for consumer group performance.

    Sampled periodically for monitoring/alerting.
    """

    __tablename__ = "consumer_group_metrics"

    id = UUID(as_uuid=True, primary_key=True, default=uuid4)
    group_id = String(255, nullable=False)
    topic = String(255, nullable=False)
    partition = Integer(nullable=True)
    lag = Integer(nullable=False)
    processing_rate = String(50, nullable=True)  # msgs/sec
    fetch_rate = String(50, nullable=True)  # msgs/sec
    consumer_count = Integer(nullable=False, server_default="1")
    created_at = DateTime(timezone=True, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_consumer_metrics_group", ("group_id", "created_at")),
        Index("idx_consumer_metrics_topic", ("topic", "created_at")),
    )


class EventSubscription(Base):
    """Define consumer subscriptions (routing configuration).

    Links topics to consumer groups + handlers.
    """

    __tablename__ = "event_subscriptions"

    id = UUID(as_uuid=True, primary_key=True, default=uuid4)
    name = String(255, nullable=False, unique=True)  # e.g., "analytics_processor"
    topic = String(255, nullable=False)  # e.g., "auth.events"
    consumer_group_id = String(255, nullable=False)
    handler_service = String(255, nullable=False)  # e.g., "analytics_service.on_auth_event"
    enabled = Boolean(nullable=False, server_default="true")
    filter_config = JSONB(nullable=True)  # Optional filtering rules
    retry_max_attempts = Integer(nullable=False, server_default="3")
    retry_backoff_ms = Integer(nullable=False, server_default="1000")
    created_at = DateTime(timezone=True, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_subscriptions_topic", "topic"),
        Index("idx_subscriptions_enabled", "enabled"),
    )


class EventDeadLetterQueue(Base):
    """Dead-letter queue for unprocessable events."""

    __tablename__ = "event_dlq"

    id = UUID(as_uuid=True, primary_key=True, default=uuid4)
    topic = String(255, nullable=False)
    original_offset = String(255, nullable=True)
    consumer_group_id = String(255, nullable=False)
    payload = JSONB(nullable=False)
    error_reason = Text(nullable=True)
    attempt_count = Integer(nullable=False, server_default="0")
    moved_to_dlq_at = DateTime(timezone=True, nullable=False, server_default=func.now())
    resolved = Boolean(nullable=False, server_default="false")
    resolution_notes = Text(nullable=True)

    __table_args__ = (
        Index("idx_dlq_topic", "topic"),
        Index("idx_dlq_resolved", "resolved"),
        Index("idx_dlq_created", "moved_to_dlq_at"),
    )


# ─────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────

def create_stream_event(
    topic: str,
    schema_name: str,
    payload: Dict[str, Any],
    tenant_id: str,
    correlation_id: Optional[str] = None,
    schema_version: int = 1,
) -> StreamEvent:
    """Factory for creating stream event records."""
    from uuid import uuid4
    return StreamEvent(
        id=uuid4(),
        topic=topic,
        schema_name=schema_name,
        schema_version=schema_version,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
        event_id=f"{topic}-{uuid4().hex[:12]}",
        payload=payload,
        status=StreamEventStatus.PENDING.value,
    )
