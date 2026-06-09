"""Reporting domain models — scheduled reports, templates, exports."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Any, Optional

from sqlalchemy import (
    DateTime, Index, Integer, String, Text, UniqueConstraint, Boolean,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class ReportTemplate(Base):
    """Report template — predefined or custom report layouts."""

    __tablename__ = "report_templates"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Template type: "executive_summary", "detailed", "custom"
    template_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Template configuration: field definitions, ordering, filters
    # {
    #   "sections": [
    #     {"name": "test_metrics", "fields": ["total_tests", "pass_rate", "coverage"]},
    #     {"name": "defects", "fields": ["total", "open", "critical"]},
    #     {"name": "trends", "chart_type": "line"}
    #   ]
    # }
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    is_global: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # True = shared across org
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_report_templates_tenant_id", "tenant_id"),
        Index("ix_report_templates_template_type", "template_type"),
        UniqueConstraint("tenant_id", "name", name="uq_report_template_tenant_name"),
    )


class ScheduledReport(Base):
    """Scheduled report — recurring report generation & delivery."""

    __tablename__ = "scheduled_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Cron schedule: "0 9 * * MON" (every Monday at 9am), "0 0 1 * *" (monthly)
    cron_schedule: Mapped[str] = mapped_column(String(128), nullable=False)

    # Delivery channels: ["email", "slack", "teams", "webhook"]
    delivery_channels: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    delivery_recipients: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # {"email": ["a@b.com"], "slack": "#reports"}

    # Report scope
    project_ids: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)  # None = all projects
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # {"status": "failed", "severity": "high"}

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_scheduled_reports_tenant_id", "tenant_id"),
        Index("ix_scheduled_reports_is_active", "is_active"),
        Index("ix_scheduled_reports_next_scheduled_at", "next_scheduled_at"),
    )


class ReportGeneration(Base):
    """Report generation execution — one generation per scheduled report run."""

    __tablename__ = "report_generations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    scheduled_report_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("scheduled_reports.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Status: "pending", "generating", "generated", "failed"
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # Report data
    report_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    report_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File storage
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # S3/MinIO path
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_report_generations_scheduled_report_id", "scheduled_report_id"),
        Index("ix_report_generations_tenant_id", "tenant_id"),
        Index("ix_report_generations_status", "status"),
        Index("ix_report_generations_created_at", "created_at"),
    )


class DataExportJob(Base):
    """Data export job — on-demand export to CSV/JSON/Parquet."""

    __tablename__ = "data_export_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Export type: "csv", "json", "parquet", "sql"
    export_format: Mapped[str] = mapped_column(String(32), nullable=False)

    # Data scope
    entity_types: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)  # ["test_runs", "defects"]
    project_ids: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    date_range: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)  # {"start": "2026-01-01", "end": "2026-12-31"}
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # "pending", "processing", "completed", "failed"
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Output
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_data_export_jobs_tenant_id", "tenant_id"),
        Index("ix_data_export_jobs_status", "status"),
        Index("ix_data_export_jobs_created_by", "created_by"),
        Index("ix_data_export_jobs_created_at", "created_at"),
    )


class RetentionPolicy(Base):
    """Data retention policy — auto-delete rules by entity type and age."""

    __tablename__ = "retention_policies"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Entity type: "test_runs", "defects", "logs", "events"
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Retention: keep data for X days (0 = no limit)
    retention_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Archive before delete (optional)
    archive_before_delete: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archive_location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_retention_policies_tenant_id", "tenant_id"),
        Index("ix_retention_policies_entity_type", "entity_type"),
        UniqueConstraint("tenant_id", "entity_type", name="uq_retention_policy_tenant_entity"),
    )
