"""GDPR domain schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class DataExportRequestResponse(BaseModel):
    """GDPR Article 20 data export request."""

    id: str
    user_id: str
    status: str
    included_entities: list[str]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    file_format: str
    expires_at: Optional[datetime]
    downloaded_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataDeletionRequestCreateRequest(BaseModel):
    """Create GDPR Article 17 deletion request."""

    scope: str = Field(..., description="'account', 'data', 'custom'")
    custom_entities: Optional[list[str]] = None


class DataDeletionRequestResponse(BaseModel):
    """GDPR Article 17 deletion request response."""

    id: str
    user_id: str
    status: str
    scope: str
    grace_period_ends_at: datetime
    cancelled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    verified_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConsentLogResponse(BaseModel):
    """Consent log response."""

    id: str
    user_id: str
    consent_type: str
    version: str
    given: bool
    withdrawn_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    """Audit trail response."""

    id: str
    actor_user_id: Optional[str]
    actor_type: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    resource_owner_id: Optional[str]
    details: dict[str, Any]
    ip_address: Optional[str]
    severity: str
    created_at: datetime

    class Config:
        from_attributes = True


class DeletionVerificationRequest(BaseModel):
    """Verify deletion request with code."""

    verification_code: str = Field(..., min_length=1)
