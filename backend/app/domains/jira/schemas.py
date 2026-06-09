"""Pydantic schemas for Jira synchronization domain."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Configuration Schemas ──────────────────────────────────────────────────

class FieldMappingRule(BaseModel):
    """Single field mapping rule: Jira field ↔ TestCase field."""

    jira_field_id: str = Field(..., description="Jira custom field ID (e.g., customfield_10001)")
    tc_field_name: str = Field(..., description="TestCase field name (e.g., priority, tags)")
    field_type: str = Field(
        default="string",
        description="Field type: string, number, boolean, enum, date, array",
    )
    transform_fn: Optional[str] = Field(
        default=None,
        description="Optional transformation function name",
    )


class SyncConfig(BaseModel):
    """Jira ↔ TestCase synchronization configuration."""

    tenant_id: str = Field(..., description="Tenant ID")
    enabled: bool = Field(default=True, description="Enable/disable sync")
    direction: str = Field(
        default="both",
        description="Sync direction: to_jira, from_jira, or both",
    )
    field_mappings: list[FieldMappingRule] = Field(
        default_factory=list,
        description="Custom field mappings",
    )
    auto_create_issues: bool = Field(
        default=False,
        description="Auto-create Jira issues from new TestCases",
    )
    auto_update_issues: bool = Field(
        default=True,
        description="Auto-update Jira issues when TestCase changes",
    )
    auto_create_test_cases: bool = Field(
        default=False,
        description="Auto-create TestCases from new Jira issues",
    )
    sync_statuses: list[str] = Field(
        default_factory=lambda: ["draft", "in_review", "approved"],
        description="TestCase statuses to sync",
    )
    jira_project_key: Optional[str] = Field(
        default=None,
        description="Default Jira project key for new issues",
    )
    rate_limit_per_second: float = Field(
        default=10.0,
        description="Rate limit: requests per second",
    )
    max_retries: int = Field(
        default=3,
        description="Max retries for failed syncs",
    )
    retry_backoff_secs: int = Field(
        default=60,
        description="Exponential backoff base (seconds)",
    )

    class Config:
        from_attributes = True


class SyncStatus(BaseModel):
    """Status/progress of an ongoing sync operation."""

    sync_id: str = Field(..., description="Unique sync operation ID")
    sync_type: str = Field(..., description="Type: tc_to_issue, issue_to_tc, bidirectional")
    tenant_id: str
    status: str = Field(
        description="Status: pending, in_progress, completed, failed, checkpoint",
    )
    processed_count: int = Field(default=0)
    total_count: int = Field(default=0)
    last_processed_id: Optional[str] = Field(default=None)
    error_details: Optional[str] = Field(default=None)
    created_at: datetime
    updated_at: datetime

    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.processed_count / self.total_count) * 100


# ─── Jira Webhook Schemas ───────────────────────────────────────────────────

class JiraWebhookIssue(BaseModel):
    """Jira issue from webhook event."""

    key: str = Field(..., description="Jira issue key (e.g., PROJ-123)")
    fields: dict[str, Any] = Field(default_factory=dict)


class JiraWebhookEvent(BaseModel):
    """Jira webhook event payload."""

    webhookEvent: str = Field(..., description="Event type (e.g., jira:issue_updated)")
    issue: Optional[JiraWebhookIssue] = None
    user: Optional[dict[str, Any]] = None
    timestamp: Optional[int] = None

    class Config:
        extra = "allow"  # Allow additional Jira fields


class JiraWebhookEventIn(BaseModel):
    """Request body for /webhook/jira-incoming endpoint."""

    webhookEvent: str
    issue: Optional[dict[str, Any]] = None
    user: Optional[dict[str, Any]] = None


class WebhookEventResponse(BaseModel):
    """Response from webhook receiver."""

    received: bool
    event: Optional[str] = None
    error: Optional[str] = None


# ─── Sync Request/Response Schemas ──────────────────────────────────────────

class SyncTestCaseToIssueRequest(BaseModel):
    """Request to sync TestCase → Jira Issue."""

    test_case_id: str = Field(..., description="TestCase ID to sync")
    project_key: str = Field(..., description="Target Jira project key")
    create_if_not_exists: bool = Field(
        default=True,
        description="Create new issue if not already linked",
    )


class SyncTestCaseToIssueResponse(BaseModel):
    """Response from TC→Issue sync."""

    success: bool
    issue_key: Optional[str] = None
    error: Optional[str] = None
    created: bool = Field(
        default=False,
        description="True if new issue created, False if updated",
    )


class SyncIssueToTestCaseRequest(BaseModel):
    """Request to sync Jira Issue → TestCase."""

    issue_key: str = Field(..., description="Jira issue key to sync")
    test_case_id: Optional[str] = Field(
        default=None,
        description="Link to existing TC; if empty, create new",
    )


class SyncIssueToTestCaseResponse(BaseModel):
    """Response from Issue→TC sync."""

    success: bool
    test_case_id: Optional[str] = None
    error: Optional[str] = None
    created: bool = Field(
        default=False,
        description="True if new TestCase created",
    )


class BulkSyncRequest(BaseModel):
    """Request for bulk sync operation."""

    direction: str = Field(
        description="Sync direction: to_jira, from_jira",
    )
    filters: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional filters (e.g., status, priority, project_key)",
    )
    max_items: int = Field(
        default=100,
        description="Max items to sync in this batch",
    )
    resume_from_checkpoint: Optional[str] = Field(
        default=None,
        description="Resume previous failed sync from checkpoint ID",
    )


class BulkSyncResponse(BaseModel):
    """Response from bulk sync."""

    sync_id: str = Field(..., description="Sync operation ID")
    status: str = Field(description="Status: in_progress, completed, failed")
    synced_count: int = Field(default=0)
    error_count: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
    checkpoint_id: Optional[str] = Field(
        default=None,
        description="Checkpoint ID if paused",
    )


class SyncCheckpointResponse(BaseModel):
    """Response with sync checkpoint details."""

    sync_id: str
    sync_type: str
    status: str
    processed_count: int
    total_count: int
    progress_percent: float
    last_processed_id: Optional[str]
    error_details: Optional[str]
    created_at: datetime
    updated_at: datetime


# ─── DLQ (Dead-Letter Queue) Schemas ────────────────────────────────────────

class DLQRecord(BaseModel):
    """Dead-letter queue record for failed sync."""

    dlq_id: str
    tenant_id: str
    sync_type: str
    source_id: str
    error: str
    payload: dict[str, Any]
    retry_count: int
    created_at: datetime


class DLQListResponse(BaseModel):
    """List of DLQ records."""

    total_count: int
    records: list[DLQRecord]


class DLQRetryRequest(BaseModel):
    """Request to retry a DLQ record."""

    dlq_id: str = Field(..., description="DLQ record ID to retry")
    field_overrides: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional field value overrides for retry",
    )


class DLQRetryResponse(BaseModel):
    """Response from DLQ retry."""

    success: bool
    dlq_id: str
    error: Optional[str] = None
    message: Optional[str] = None


# ─── Link Management Schemas ────────────────────────────────────────────────

class LinkTestCaseToIssueRequest(BaseModel):
    """Request to link TestCase ↔ Jira Issue."""

    test_case_id: str
    issue_key: str
    bidirectional: bool = Field(
        default=True,
        description="Enable bidirectional sync for this link",
    )


class LinkTestCaseToIssueResponse(BaseModel):
    """Response from link creation."""

    success: bool
    test_case_id: str
    issue_key: str
    error: Optional[str] = None


class UnlinkTestCaseFromIssueRequest(BaseModel):
    """Request to unlink TestCase ↔ Jira Issue."""

    test_case_id: str
    issue_key: str


class UnlinkTestCaseFromIssueResponse(BaseModel):
    """Response from link deletion."""

    success: bool
    test_case_id: str
    issue_key: str
    error: Optional[str] = None


# ─── Status Check Schemas ───────────────────────────────────────────────────

class SyncHealthResponse(BaseModel):
    """Health status of sync service."""

    enabled: bool
    jira_connected: bool
    last_sync_at: Optional[datetime] = None
    dlq_count: int
    active_syncs: int
    config_valid: bool
    error_details: Optional[str] = None


# ─── Field Discovery Schemas ────────────────────────────────────────────────

class JiraFieldInfo(BaseModel):
    """Info about a Jira field for mapping."""

    id: str
    name: str
    field_type: str
    is_custom: bool
    is_editable: bool
    allowed_values: Optional[list[str]] = None


class JiraFieldDiscoveryResponse(BaseModel):
    """Response with discovered Jira fields."""

    project_key: str
    fields: list[JiraFieldInfo]
    custom_fields: list[JiraFieldInfo]
    total_count: int
