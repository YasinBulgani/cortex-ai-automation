"""Slack integration schemas."""

from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional

from pydantic import BaseModel, Field


class SlackSubscriptionCreate(BaseModel):
    """Create Slack subscription."""

    workspace_id: str
    channel_id: str
    channel_name: Optional[str] = None
    event_types: list[str]
    webhook_url: str


class SlackSubscriptionUpdate(BaseModel):
    """Update Slack subscription."""

    channel_name: Optional[str] = None
    event_types: Optional[list[str]] = None
    is_active: Optional[bool] = None


class SlackSubscriptionResponse(BaseModel):
    """Slack subscription response."""

    id: str
    tenant_id: str
    workspace_id: str
    channel_id: str
    channel_name: Optional[str]
    event_types: list[str]
    is_active: bool
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SlackNotificationQueueResponse(BaseModel):
    """Slack notification queue response."""

    id: str
    subscription_id: str
    event_id: str
    status: str
    retry_count: int
    max_retries: int
    last_error: Optional[str]
    last_attempt_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SlackDeliveryLogResponse(BaseModel):
    """Slack delivery log response."""

    id: str
    channel_id: str
    channel_name: Optional[str]
    message_ts: Optional[str]
    success: bool
    status_code: Optional[int]
    error_message: Optional[str]
    timestamp: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class SlackDailyDigestResponse(BaseModel):
    """Slack daily digest response."""

    id: str
    subscription_id: str
    digest_date: date
    digest_data: dict[str, Any]
    message_ts: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SlackMessage(BaseModel):
    """Slack message block format."""

    text: Optional[str] = None
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    thread_ts: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SlackEventNotification(BaseModel):
    """Event notification for Slack."""

    event_id: str
    event_type: str
    event_name: str
    title: str
    description: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"  # "info", "warning", "critical"
    action_url: Optional[str] = None
    timestamp: datetime


class SlackDailyDigestData(BaseModel):
    """Daily digest data structure."""

    date: date
    summary: str
    test_executions: int
    test_pass_rate: float
    defects_created: int
    defects_resolved: int
    coverage_change: float
    team_velocity: dict[str, Any]
    top_issues: list[dict[str, Any]]
    metrics_snapshot: dict[str, Any]
