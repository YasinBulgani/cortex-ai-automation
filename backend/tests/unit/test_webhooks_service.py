"""Unit tests for webhooks service."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.webhooks.models import WebhookConfig, WebhookDelivery
from app.domains.webhooks.schemas import WebhookConfigCreateRequest
from app.domains.webhooks.service import WebhookService


@pytest.fixture
def mock_session():
    """Mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    """WebhookService instance."""
    return WebhookService(mock_session)


@pytest.mark.asyncio
async def test_sign_payload():
    """Test HMAC-SHA256 signature generation."""
    service = WebhookService(AsyncMock())
    secret = "test-secret"
    payload = {
        "event_type": "test.event",
        "timestamp": "2026-01-01T00:00:00Z",
        "data": {"key": "value"},
    }

    signature = service._sign_payload(secret, payload)

    assert signature.startswith("sha256=")
    assert len(signature) > 10


@pytest.mark.asyncio
async def test_create_webhook(service, mock_session):
    """Test webhook creation."""
    request = WebhookConfigCreateRequest(
        webhook_type="outgoing",
        target_url="https://example.com/webhook",
        secret="test-secret",
        events=["test.completed"],
    )

    webhook = await service.create_webhook(
        tenant_id="tenant-123",
        created_by="user-123",
        request=request,
    )

    assert mock_session.add.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_webhook_not_found(service, mock_session):
    """Test webhook not found."""
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    webhook = await service.get_webhook("tenant-123", "webhook-999")
    assert webhook is None


def test_webhook_signature_deterministic():
    """Test that webhook signatures are deterministic."""
    service = WebhookService(AsyncMock())
    secret = "secret"
    payload = {"a": 1, "b": 2}

    sig1 = service._sign_payload(secret, payload)
    sig2 = service._sign_payload(secret, payload)

    assert sig1 == sig2
