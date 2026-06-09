"""Reporting domain service."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone as _tz
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.reporting.models import (
    DataExportJob,
    ReportTemplate,
    ScheduledReport,
    RetentionPolicy,
)
from app.domains.reporting.schemas import (
    DataExportJobCreateRequest,
    ReportTemplateCreateRequest,
    RetentionPolicyCreateRequest,
    ScheduledReportCreateRequest,
)

logger = logging.getLogger(__name__)


class ReportingService:
    """Service for report management and export."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Report Templates
    async def create_template(
        self,
        tenant_id: str,
        created_by: str,
        request: ReportTemplateCreateRequest,
    ) -> ReportTemplate:
        """Create report template."""
        template = ReportTemplate(
            tenant_id=tenant_id,
            created_by=created_by,
            name=request.name,
            template_type=request.template_type,
            description=request.description,
            configuration=request.configuration,
            is_global=request.is_global,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def list_templates(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ReportTemplate]:
        """List report templates."""
        result = await self.db.execute(
            select(ReportTemplate)
            .where(
                (ReportTemplate.tenant_id == tenant_id) | (ReportTemplate.is_global),
                ReportTemplate.is_archived == False,
            )
            .order_by(ReportTemplate.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # Scheduled Reports
    async def create_scheduled_report(
        self,
        tenant_id: str,
        created_by: str,
        request: ScheduledReportCreateRequest,
    ) -> ScheduledReport:
        """Create scheduled report."""
        report = ScheduledReport(
            tenant_id=tenant_id,
            created_by=created_by,
            name=request.name,
            template_id=request.template_id,
            cron_schedule=request.cron_schedule,
            delivery_channels=request.delivery_channels,
            delivery_recipients=request.delivery_recipients,
            project_ids=request.project_ids,
            filters=request.filters,
        )
        self.db.add(report)
        await self.db.flush()
        return report

    async def list_scheduled_reports(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ScheduledReport]:
        """List scheduled reports."""
        result = await self.db.execute(
            select(ScheduledReport)
            .where(ScheduledReport.tenant_id == tenant_id)
            .order_by(ScheduledReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # Data Export
    async def create_export_job(
        self,
        tenant_id: str,
        created_by: str,
        request: DataExportJobCreateRequest,
    ) -> DataExportJob:
        """Create data export job."""
        job = DataExportJob(
            tenant_id=tenant_id,
            created_by=created_by,
            export_format=request.export_format,
            entity_types=request.entity_types,
            project_ids=request.project_ids,
            date_range=request.date_range,
            filters=request.filters,
            status="pending",
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def list_export_jobs(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[DataExportJob]:
        """List export jobs for tenant."""
        result = await self.db.execute(
            select(DataExportJob)
            .where(DataExportJob.tenant_id == tenant_id)
            .order_by(DataExportJob.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update_export_job_status(
        self,
        job_id: str,
        status: str,
        progress_percent: int = 0,
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[DataExportJob]:
        """Update export job status."""
        job = await self.db.get(DataExportJob, job_id)
        if not job:
            return None

        job.status = status
        job.progress_percent = progress_percent
        job.file_path = file_path
        job.error_message = error_message

        if status == "processing" and not job.started_at:
            job.started_at = datetime.now(_tz.utc)
        elif status in ("completed", "failed"):
            job.completed_at = datetime.now(_tz.utc)

        await self.db.flush()
        return job

    # Retention Policies
    async def create_retention_policy(
        self,
        tenant_id: str,
        created_by: str,
        request: RetentionPolicyCreateRequest,
    ) -> RetentionPolicy:
        """Create retention policy."""
        policy = RetentionPolicy(
            tenant_id=tenant_id,
            created_by=created_by,
            entity_type=request.entity_type,
            retention_days=request.retention_days,
            archive_before_delete=request.archive_before_delete,
            archive_location=request.archive_location,
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def get_retention_policy(
        self,
        tenant_id: str,
        entity_type: str,
    ) -> Optional[RetentionPolicy]:
        """Get retention policy for entity type."""
        result = await self.db.execute(
            select(RetentionPolicy).where(
                RetentionPolicy.tenant_id == tenant_id,
                RetentionPolicy.entity_type == entity_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_retention_policies(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[RetentionPolicy]:
        """List retention policies for tenant."""
        result = await self.db.execute(
            select(RetentionPolicy)
            .where(RetentionPolicy.tenant_id == tenant_id)
            .order_by(RetentionPolicy.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
