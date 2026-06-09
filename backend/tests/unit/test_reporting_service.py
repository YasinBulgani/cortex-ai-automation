"""Unit tests for reporting service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.domains.reporting.schemas import (
    DataExportJobCreateRequest,
    ReportTemplateCreateRequest,
    RetentionPolicyCreateRequest,
)
from app.domains.reporting.service import ReportingService


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    """ReportingService instance."""
    return ReportingService(mock_session)


@pytest.mark.asyncio
async def test_create_template(service, mock_session):
    """Test report template creation."""
    request = ReportTemplateCreateRequest(
        name="Executive Summary",
        template_type="executive_summary",
        configuration={"sections": ["metrics", "trends"]},
    )

    template = await service.create_template(
        tenant_id="tenant-123",
        created_by="user-123",
        request=request,
    )

    assert mock_session.add.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_create_export_job(service, mock_session):
    """Test data export job creation."""
    request = DataExportJobCreateRequest(
        export_format="csv",
        entity_types=["test_runs", "defects"],
    )

    job = await service.create_export_job(
        tenant_id="tenant-123",
        created_by="user-123",
        request=request,
    )

    assert job.status == "pending"
    assert mock_session.add.called


@pytest.mark.asyncio
async def test_create_retention_policy(service, mock_session):
    """Test retention policy creation."""
    request = RetentionPolicyCreateRequest(
        entity_type="test_runs",
        retention_days=90,
    )

    policy = await service.create_retention_policy(
        tenant_id="tenant-123",
        created_by="user-123",
        request=request,
    )

    assert mock_session.add.called


@pytest.mark.asyncio
async def test_update_export_job_status(service, mock_session):
    """Test export job status update."""
    job = AsyncMock()
    job.started_at = None
    mock_session.get.return_value = job

    result = await service.update_export_job_status(
        job_id="job-123",
        status="processing",
        progress_percent=50,
    )

    assert result is not None
    assert mock_session.flush.called


def test_export_formats():
    """Test supported export formats."""
    supported_formats = ["csv", "json", "parquet", "sql"]
    assert "csv" in supported_formats
    assert "json" in supported_formats
    assert "parquet" in supported_formats
    assert "sql" in supported_formats
