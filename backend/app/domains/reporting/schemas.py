"""Reporting domain schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ReportTemplateCreateRequest(BaseModel):
    """Create report template."""

    name: str = Field(..., min_length=1, max_length=256)
    template_type: str = Field(..., description="'executive_summary', 'detailed', 'custom'")
    description: Optional[str] = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    is_global: bool = False


class ReportTemplateResponse(BaseModel):
    """Report template response."""

    id: str
    name: str
    template_type: str
    description: Optional[str]
    configuration: dict[str, Any]
    is_global: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduledReportCreateRequest(BaseModel):
    """Create scheduled report."""

    name: str = Field(..., min_length=1, max_length=256)
    template_id: Optional[str] = None
    cron_schedule: str = Field(..., description="Cron schedule string")
    delivery_channels: list[str] = Field(default_factory=list, description="['email', 'slack', 'teams', 'webhook']")
    delivery_recipients: dict[str, Any] = Field(default_factory=dict)
    project_ids: Optional[list[str]] = None
    filters: dict[str, Any] = Field(default_factory=dict)


class ScheduledReportResponse(BaseModel):
    """Scheduled report response."""

    id: str
    name: str
    template_id: Optional[str]
    cron_schedule: str
    delivery_channels: list[str]
    delivery_recipients: dict[str, Any]
    project_ids: Optional[list[str]]
    filters: dict[str, Any]
    is_active: bool
    last_generated_at: Optional[datetime]
    next_scheduled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataExportJobCreateRequest(BaseModel):
    """Create data export job."""

    export_format: str = Field(..., description="'csv', 'json', 'parquet', 'sql'")
    entity_types: list[str] = Field(..., description="['test_runs', 'defects', ...]")
    project_ids: Optional[list[str]] = None
    date_range: dict[str, str] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)


class DataExportJobResponse(BaseModel):
    """Data export job response."""

    id: str
    export_format: str
    entity_types: list[str]
    project_ids: Optional[list[str]]
    status: str
    progress_percent: int
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    row_count: Optional[int]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class RetentionPolicyCreateRequest(BaseModel):
    """Create retention policy."""

    entity_type: str = Field(..., description="'test_runs', 'defects', 'logs', 'events'")
    retention_days: int = Field(default=0, description="Days to retain data (0=no limit)")
    archive_before_delete: bool = True
    archive_location: Optional[str] = None


class RetentionPolicyResponse(BaseModel):
    """Retention policy response."""

    id: str
    entity_type: str
    retention_days: int
    archive_before_delete: bool
    archive_location: Optional[str]
    is_active: bool
    last_executed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
