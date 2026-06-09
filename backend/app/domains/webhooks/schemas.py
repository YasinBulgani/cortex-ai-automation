"""Webhooks domain schemas — request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, HttpUrl


class WebhookConfigCreateRequest(BaseModel):
    """Create webhook configuration."""

    webhook_type: str = Field(..., description="'outgoing' or 'incoming'")
    provider: Optional[str] = Field(None, description="Provider for incoming webhooks (jira, github, etc.)")
    target_url: str = Field(..., description="Webhook URL target")
    secret: str = Field(..., description="HMAC secret key")
    events: list[str] = Field(default_factory=list, description="Event subscriptions")
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_per_day: int = Field(default=1000)
    max_retries: int = Field(default=7)
    retry_backoff_seconds: int = Field(default=60)
    description: Optional[str] = None
    auth_method: Optional[str] = Field(None, description="'basic', 'bearer', 'hmac'")
    auth_credentials: Optional[dict[str, Any]] = None


class WebhookConfigUpdateRequest(BaseModel):
    """Update webhook configuration."""

    target_url: Optional[str] = None
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    description: Optional[str] = None


class WebhookConfigResponse(BaseModel):
    """Webhook configuration response."""

    id: str
    webhook_type: str
    provider: Optional[str]
    target_url: str
    events: list[str]
    is_active: bool
    rate_limit_per_minute: int
    rate_limit_per_day: int
    max_retries: int
    retry_backoff_seconds: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery response."""

    id: str
    webhook_config_id: str
    event_type: str
    entity_id: Optional[str]
    entity_type: Optional[str]
    attempt_number: int
    status: str
    http_status_code: Optional[int]
    error_message: Optional[str]
    delivered_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookTestRequest(BaseModel):
    """Test webhook delivery."""

    event_type: str = Field(..., description="Test event type")
    test_data: dict[str, Any] = Field(default_factory=dict, description="Test payload")


class WebhookTestResponse(BaseModel):
    """Webhook test result."""

    delivery_id: str
    status: str
    http_status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
