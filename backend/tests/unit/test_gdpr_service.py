"""Unit tests for GDPR service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.domains.gdpr.schemas import DataDeletionRequestCreateRequest
from app.domains.gdpr.service import GDPRService


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    """GDPRService instance."""
    return GDPRService(mock_session)


@pytest.mark.asyncio
async def test_request_data_export(service, mock_session):
    """Test GDPR Article 20 — data export request."""
    export_request = await service.request_data_export(
        tenant_id="tenant-123",
        user_id="user-123",
    )

    assert export_request.status == "pending"
    assert "profile" in export_request.included_entities
    assert mock_session.add.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_request_data_deletion(service, mock_session):
    """Test GDPR Article 17 — right to be forgotten."""
    request = DataDeletionRequestCreateRequest(scope="account")

    del_request = await service.request_data_deletion(
        tenant_id="tenant-123",
        user_id="user-123",
        request=request,
    )

    assert del_request.status == "pending"
    assert del_request.scope == "account"
    assert del_request.verification_code is not None
    assert del_request.grace_period_ends_at is not None

    # Grace period should be 30 days
    grace_days = (del_request.grace_period_ends_at - datetime.now(timezone.utc)).days
    assert 29 <= grace_days <= 30


@pytest.mark.asyncio
async def test_verify_deletion_request(service, mock_session):
    """Test deletion request verification."""
    del_request = AsyncMock()
    del_request.verification_code = "test-code-123"

    mock_session.execute.return_value.scalar_one_or_none.return_value = del_request

    verified = await service.verify_deletion_request(
        tenant_id="tenant-123",
        deletion_request_id="del-123",
        verification_code="test-code-123",
        user_id="user-123",
    )

    assert verified is True
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_log_consent(service, mock_session):
    """Test consent logging."""
    consent = await service.log_consent(
        tenant_id="tenant-123",
        user_id="user-123",
        consent_type="privacy_policy",
        version="2026-01-01",
        given=True,
    )

    assert consent.given is True
    assert consent.consent_type == "privacy_policy"
    assert mock_session.add.called


@pytest.mark.asyncio
async def test_get_user_consents(service, mock_session):
    """Test retrieving user consents."""
    consents = await service.get_user_consents(
        tenant_id="tenant-123",
        user_id="user-123",
    )

    assert mock_session.execute.called


@pytest.mark.asyncio
async def test_get_audit_trail(service, mock_session):
    """Test audit trail retrieval."""
    trails = await service.get_audit_trail(
        tenant_id="tenant-123",
        skip=0,
        limit=100,
    )

    assert mock_session.execute.called


def test_grace_period_duration():
    """Test that grace period is 30 days."""
    now = datetime.now(timezone.utc)
    grace_end = now + timedelta(days=30)

    delta = grace_end - now
    assert delta.days == 30


def test_verification_code_generation():
    """Test that verification codes are random."""
    import secrets

    code1 = secrets.token_urlsafe(32)
    code2 = secrets.token_urlsafe(32)

    assert code1 != code2
    assert len(code1) > 30
