"""GDPR domain models — compliance, data deletion, consent tracking."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Any, Optional

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(_tz.utc)


class DataExportRequest(Base):
    """GDPR Article 20 — right to access personal data (machine-readable)."""

    __tablename__ = "data_export_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Status: "pending", "processing", "ready", "expired", "downloaded"
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # Export scope: all personal data related to user
    included_entities: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)  # ["profile", "activity_logs", "test_runs"]

    # File storage
    file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # S3/MinIO path
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_format: Mapped[str] = mapped_column(String(32), default="json", nullable=False)

    # Expiration: data available for 30 days
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    request_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_data_export_requests_tenant_id", "tenant_id"),
        Index("ix_data_export_requests_user_id", "user_id"),
        Index("ix_data_export_requests_status", "status"),
        Index("ix_data_export_requests_created_at", "created_at"),
    )


class DataDeletionRequest(Base):
    """GDPR Article 17 — right to be forgotten (data deletion)."""

    __tablename__ = "data_deletion_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    requested_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)  # User or admin

    # Status: "pending", "processing", "completed", "failed", "cancelled"
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    # Deletion scope
    scope: Mapped[str] = mapped_column(String(32), nullable=False)  # "account" (full), "data" (anonymize), "custom"
    custom_entities: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)  # If scope="custom"

    # Grace period: 30 days to cancel (GDPR requirement)
    grace_period_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Processing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Verification
    verification_code: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # Sent to email
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_data_deletion_requests_tenant_id", "tenant_id"),
        Index("ix_data_deletion_requests_user_id", "user_id"),
        Index("ix_data_deletion_requests_status", "status"),
        Index("ix_data_deletion_requests_grace_period_ends_at", "grace_period_ends_at"),
        Index("ix_data_deletion_requests_created_at", "created_at"),
    )


class ConsentLog(Base):
    """Consent tracking — T&C, privacy policy, cookie consent."""

    __tablename__ = "consent_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Consent type
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "terms_of_service", "privacy_policy", "cookies", "marketing"

    # Version of document (T&C version hash or date)
    version: Mapped[str] = mapped_column(String(128), nullable=False)

    # Consent status
    given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Withdrawal
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_consent_logs_tenant_id", "tenant_id"),
        Index("ix_consent_logs_user_id", "user_id"),
        Index("ix_consent_logs_consent_type", "consent_type"),
        Index("ix_consent_logs_given", "given"),
    )


class AuditTrail(Base):
    """Audit trail — who accessed what, when, why (GDPR compliance)."""

    __tablename__ = "audit_trails"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "user", "service", "admin"

    # Action
    action: Mapped[str] = mapped_column(String(128), nullable=False)  # "view_user_data", "export_data", "delete_record", "update_settings"
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "user", "test_run", "defect", "webhook"
    resource_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    resource_owner_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Details
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Risk classification
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False)  # "info", "warning", "high", "critical"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_trails_tenant_id", "tenant_id"),
        Index("ix_audit_trails_actor_user_id", "actor_user_id"),
        Index("ix_audit_trails_resource_type", "resource_type"),
        Index("ix_audit_trails_resource_id", "resource_id"),
        Index("ix_audit_trails_action", "action"),
        Index("ix_audit_trails_severity", "severity"),
        Index("ix_audit_trails_created_at", "created_at"),
    )
