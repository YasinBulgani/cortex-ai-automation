"""Reporting domain router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, get_session, CurrentUserDep, SessionDep
from app.domains.reporting.schemas import (
    DataExportJobCreateRequest,
    DataExportJobResponse,
    ReportTemplateCreateRequest,
    ReportTemplateResponse,
    RetentionPolicyCreateRequest,
    RetentionPolicyResponse,
    ScheduledReportCreateRequest,
    ScheduledReportResponse,
)
from app.domains.reporting.service import ReportingService

router = APIRouter(prefix="/api/v1/reporting", tags=["reporting"])


# Report Templates
@router.post("/templates", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: ReportTemplateCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ReportTemplateResponse:
    """Create report template."""
    service = ReportingService(session)
    template = await service.create_template(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        request=request,
    )
    await session.commit()
    return ReportTemplateResponse.model_validate(template)


@router.get("/templates", response_model=list[ReportTemplateResponse])
async def list_templates(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[ReportTemplateResponse]:
    """List report templates."""
    service = ReportingService(session)
    templates = await service.list_templates(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return [ReportTemplateResponse.model_validate(t) for t in templates]


# Scheduled Reports
@router.post("/scheduled", response_model=ScheduledReportResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_report(
    request: ScheduledReportCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> ScheduledReportResponse:
    """Create scheduled report."""
    service = ReportingService(session)
    report = await service.create_scheduled_report(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        request=request,
    )
    await session.commit()
    return ScheduledReportResponse.model_validate(report)


@router.get("/scheduled", response_model=list[ScheduledReportResponse])
async def list_scheduled_reports(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[ScheduledReportResponse]:
    """List scheduled reports."""
    service = ReportingService(session)
    reports = await service.list_scheduled_reports(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return [ScheduledReportResponse.model_validate(r) for r in reports]


# Data Export
@router.post("/export", response_model=DataExportJobResponse, status_code=status.HTTP_201_CREATED)
async def create_export(
    request: DataExportJobCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DataExportJobResponse:
    """Create data export job."""
    service = ReportingService(session)
    job = await service.create_export_job(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        request=request,
    )
    await session.commit()
    return DataExportJobResponse.model_validate(job)


@router.get("/export", response_model=list[DataExportJobResponse])
async def list_exports(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[DataExportJobResponse]:
    """List data export jobs."""
    service = ReportingService(session)
    jobs = await service.list_export_jobs(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return [DataExportJobResponse.model_validate(j) for j in jobs]


@router.get("/export/{job_id}", response_model=DataExportJobResponse)
async def get_export(
    job_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DataExportJobResponse:
    """Get export job details."""
    job = await session.get(DataExportJob, job_id)
    if not job or job.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export job not found")
    return DataExportJobResponse.model_validate(job)


# Retention Policies
@router.post("/retention", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_retention_policy(
    request: RetentionPolicyCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> RetentionPolicyResponse:
    """Create retention policy."""
    service = ReportingService(session)
    policy = await service.create_retention_policy(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        request=request,
    )
    await session.commit()
    return RetentionPolicyResponse.model_validate(policy)


@router.get("/retention", response_model=list[RetentionPolicyResponse])
async def list_retention_policies(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[RetentionPolicyResponse]:
    """List retention policies."""
    service = ReportingService(session)
    policies = await service.list_retention_policies(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return [RetentionPolicyResponse.model_validate(p) for p in policies]


# Import DataExportJob for router
from app.domains.reporting.models import DataExportJob
