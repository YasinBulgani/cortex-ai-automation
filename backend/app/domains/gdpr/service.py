"""GDPR domain service."""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone as _tz
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.gdpr.models import (
    AuditTrail,
    ConsentLog,
    DataDeletionRequest,
    DataExportRequest,
)
from app.domains.gdpr.schemas import DataDeletionRequestCreateRequest

logger = logging.getLogger(__name__)


class GDPRService:
    """Service for GDPR compliance (Articles 17, 20, etc.)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Article 20 — Data Export Right
    async def request_data_export(
        self,
        tenant_id: str,
        user_id: str,
        included_entities: Optional[list[str]] = None,
    ) -> DataExportRequest:
        """Create GDPR Article 20 data export request."""
        if not included_entities:
            included_entities = ["profile", "activity_logs", "test_runs", "defects"]

        request = DataExportRequest(
            tenant_id=tenant_id,
            user_id=user_id,
            status="pending",
            included_entities=included_entities,
            file_format="json",
            expires_at=datetime.now(_tz.utc) + timedelta(days=30),
        )
        self.db.add(request)
        await self.db.flush()

        # Log audit trail
        await self._log_audit(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            actor_type="user",
            action="request_data_export",
            resource_type="user",
            resource_id=user_id,
            severity="info",
        )

        return request

    async def get_data_export_request(
        self,
        tenant_id: str,
        request_id: str,
        user_id: str,
    ) -> Optional[DataExportRequest]:
        """Get data export request (user can only view their own)."""
        result = await self.db.execute(
            select(DataExportRequest).where(
                DataExportRequest.id == request_id,
                DataExportRequest.tenant_id == tenant_id,
                DataExportRequest.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_data_export_requests(
        self,
        tenant_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> list[DataExportRequest]:
        """List user's data export requests."""
        result = await self.db.execute(
            select(DataExportRequest)
            .where(
                DataExportRequest.tenant_id == tenant_id,
                DataExportRequest.user_id == user_id,
            )
            .order_by(DataExportRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    # Article 17 — Right to be Forgotten
    async def request_data_deletion(
        self,
        tenant_id: str,
        user_id: str,
        request: DataDeletionRequestCreateRequest,
    ) -> DataDeletionRequest:
        """Create GDPR Article 17 deletion request."""
        # 30-day grace period
        grace_period = datetime.now(_tz.utc) + timedelta(days=30)

        deletion_request = DataDeletionRequest(
            tenant_id=tenant_id,
            user_id=user_id,
            requested_by=user_id,
            status="pending",
            scope=request.scope,
            custom_entities=request.custom_entities,
            grace_period_ends_at=grace_period,
            verification_code=secrets.token_urlsafe(32),
        )
        self.db.add(deletion_request)
        await self.db.flush()

        # Log audit trail
        await self._log_audit(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            actor_type="user",
            action="request_data_deletion",
            resource_type="user",
            resource_id=user_id,
            details={"scope": request.scope},
            severity="warning",
        )

        return deletion_request

    async def verify_deletion_request(
        self,
        tenant_id: str,
        deletion_request_id: str,
        verification_code: str,
        user_id: str,
    ) -> bool:
        """Verify deletion request with code (must be current user)."""
        result = await self.db.execute(
            select(DataDeletionRequest).where(
                DataDeletionRequest.id == deletion_request_id,
                DataDeletionRequest.tenant_id == tenant_id,
                DataDeletionRequest.user_id == user_id,
            )
        )
        del_request = result.scalar_one_or_none()
        if not del_request:
            return False

        if del_request.verification_code == verification_code:
            del_request.verified_at = datetime.now(_tz.utc)
            await self.db.flush()

            await self._log_audit(
                tenant_id=tenant_id,
                actor_user_id=user_id,
                actor_type="user",
                action="verify_deletion",
                resource_type="user",
                resource_id=user_id,
                severity="warning",
            )

            return True

        return False

    async def cancel_deletion_request(
        self,
        tenant_id: str,
        deletion_request_id: str,
        user_id: str,
    ) -> bool:
        """Cancel deletion request (within grace period)."""
        result = await self.db.execute(
            select(DataDeletionRequest).where(
                DataDeletionRequest.id == deletion_request_id,
                DataDeletionRequest.tenant_id == tenant_id,
                DataDeletionRequest.user_id == user_id,
            )
        )
        del_request = result.scalar_one_or_none()
        if not del_request:
            return False

        now = datetime.now(_tz.utc)
        if now < del_request.grace_period_ends_at:
            del_request.cancelled_at = now
            await self.db.flush()

            await self._log_audit(
                tenant_id=tenant_id,
                actor_user_id=user_id,
                actor_type="user",
                action="cancel_deletion",
                resource_type="user",
                resource_id=user_id,
                severity="info",
            )

            return True

        return False

    async def get_deletion_request(
        self,
        tenant_id: str,
        deletion_request_id: str,
        user_id: str,
    ) -> Optional[DataDeletionRequest]:
        """Get deletion request."""
        result = await self.db.execute(
            select(DataDeletionRequest).where(
                DataDeletionRequest.id == deletion_request_id,
                DataDeletionRequest.tenant_id == tenant_id,
                DataDeletionRequest.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    # Consent Tracking
    async def log_consent(
        self,
        tenant_id: str,
        user_id: str,
        consent_type: str,
        version: str,
        given: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentLog:
        """Log consent (T&C, privacy policy, cookies)."""
        consent = ConsentLog(
            tenant_id=tenant_id,
            user_id=user_id,
            consent_type=consent_type,
            version=version,
            given=given,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(consent)
        await self.db.flush()

        await self._log_audit(
            tenant_id=tenant_id,
            actor_user_id=user_id,
            actor_type="user",
            action="consent_logged",
            resource_type="consent",
            details={"consent_type": consent_type, "given": given},
            severity="info",
        )

        return consent

    async def get_user_consents(
        self,
        tenant_id: str,
        user_id: str,
    ) -> list[ConsentLog]:
        """Get all consents for user."""
        result = await self.db.execute(
            select(ConsentLog)
            .where(
                ConsentLog.tenant_id == tenant_id,
                ConsentLog.user_id == user_id,
            )
            .order_by(ConsentLog.created_at.desc())
        )
        return result.scalars().all()

    # Audit Trail
    async def get_audit_trail(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        resource_type: Optional[str] = None,
        action: Optional[str] = None,
    ) -> list[AuditTrail]:
        """Get audit trail for compliance."""
        query = select(AuditTrail).where(AuditTrail.tenant_id == tenant_id)

        if resource_type:
            query = query.where(AuditTrail.resource_type == resource_type)
        if action:
            query = query.where(AuditTrail.action == action)

        result = await self.db.execute(
            query.order_by(AuditTrail.created_at.desc()).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def _log_audit(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        actor_type: str,
        resource_id: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        resource_owner_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "info",
    ) -> None:
        """Log audit trail entry."""
        if details is None:
            details = {}

        trail = AuditTrail(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_owner_id=resource_owner_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            severity=severity,
        )
        self.db.add(trail)
        await self.db.flush()
