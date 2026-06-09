"""Analytics domain models — event tracking and metrics."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class AnalyticsEvent(Base):
    """Domain event for analytics — test runs, defects, coverage changes."""

    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Event classification
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "test_run", "defect", "coverage"
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)  # "test_run_started", "test_case_completed"

    # Entity references
    entity_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # "TestRun", "Defect", "TestCase"

    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Event payload
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index('idx_analytics_events_tenant', 'tenant_id'),
        Index('idx_analytics_events_type', 'event_type'),
        Index('idx_analytics_events_timestamp', 'timestamp'),
        Index('idx_analytics_events_project', 'project_id'),
        Index('idx_analytics_events_user', 'user_id'),
        Index('idx_analytics_events_tenant_type_ts', 'tenant_id', 'event_type', 'timestamp'),
    )


class AnalyticsMetric(Base):
    """Aggregated analytics metrics — daily, weekly, monthly."""

    __tablename__ = "analytics_metrics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Metric identification
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)  # "test_execution_count", "defect_rate"
    metric_category: Mapped[str] = mapped_column(String(64), nullable=False)  # "execution", "defect", "coverage"

    # Metric value
    metric_value: Mapped[float] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    metric_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # "count", "percentage", "hours"

    # Dimensions
    project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    team_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Time dimension
    date: Mapped[datetime] = mapped_column(Date(), nullable=False)
    period: Mapped[str] = mapped_column(String(32), nullable=False)  # "daily", "weekly", "monthly"

    # Additional metadata
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index('idx_analytics_metrics_tenant', 'tenant_id'),
        Index('idx_analytics_metrics_name', 'metric_name'),
        Index('idx_analytics_metrics_date', 'date'),
        Index('idx_analytics_metrics_project', 'project_id'),
        Index('idx_analytics_metrics_tenant_name_date', 'tenant_id', 'metric_name', 'date'),
    )
