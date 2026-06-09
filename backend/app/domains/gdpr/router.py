"""GDPR domain router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, get_session, CurrentUserDep, SessionDep
from app.domains.gdpr.schemas import (
    AuditTrailResponse,
    ConsentLogResponse,
    DataDeletionRequestCreateRequest,
    DataDeletionRequestResponse,
    DataExportRequestResponse,
    DeletionVerificationRequest,
)
from app.domains.gdpr.service import GDPRService

router = APIRouter(prefix="/api/v1/gdpr", tags=["gdpr"])


# Article 20 — Data Export
@router.post("/export-request", response_model=DataExportRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_data_export(
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DataExportRequestResponse:
    """Request personal data export (GDPR Article 20)."""
    service = GDPRService(session)
    export_request = await service.request_data_export(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await session.commit()
    return DataExportRequestResponse.model_validate(export_request)


@router.get("/export-request", response_model=list[DataExportRequestResponse])
async def list_data_exports(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[DataExportRequestResponse]:
    """List user's data export requests."""
    service = GDPRService(session)
    requests = await service.list_data_export_requests(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return [DataExportRequestResponse.model_validate(r) for r in requests]


@router.get("/export-request/{request_id}", response_model=DataExportRequestResponse)
async def get_data_export(
    request_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DataExportRequestResponse:
    """Get data export request details."""
    service = GDPRService(session)
    export_request = await service.get_data_export_request(
        tenant_id=current_user.tenant_id,
        request_id=request_id,
        user_id=current_user.id,
    )
    if not export_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export request not found")
    return DataExportRequestResponse.model_validate(export_request)


# Article 17 — Right to be Forgotten
@router.post("/deletion-request", response_model=DataDeletionRequestResponse, status_code=status.HTTP_201_CREATED)
async def request_data_deletion(
    request: DataDeletionRequestCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DataDeletionRequestResponse:
    """Request data deletion (GDPR Article 17 — Right to be Forgotten)."""
    service = GDPRService(session)
    deletion_request = await service.request_data_deletion(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        request=request,
    )
    await session.commit()
    return DataDeletionRequestResponse.model_validate(deletion_request)


@router.get("/deletion-request/{request_id}", response_model=DataDeletionRequestResponse)
async def get_deletion_request(
    request_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> DataDeletionRequestResponse:
    """Get deletion request details."""
    service = GDPRService(session)
    deletion_request = await service.get_deletion_request(
        tenant_id=current_user.tenant_id,
        deletion_request_id=request_id,
        user_id=current_user.id,
    )
    if not deletion_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deletion request not found")
    return DataDeletionRequestResponse.model_validate(deletion_request)


@router.post("/deletion-request/{request_id}/verify")
async def verify_deletion(
    request_id: str,
    verify_request: DeletionVerificationRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Verify deletion request with verification code."""
    service = GDPRService(session)
    verified = await service.verify_deletion_request(
        tenant_id=current_user.tenant_id,
        deletion_request_id=request_id,
        verification_code=verify_request.verification_code,
        user_id=current_user.id,
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or request not found",
        )
    await session.commit()
    return {"status": "verified"}


@router.post("/deletion-request/{request_id}/cancel")
async def cancel_deletion(
    request_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Cancel deletion request (within grace period)."""
    service = GDPRService(session)
    cancelled = await service.cancel_deletion_request(
        tenant_id=current_user.tenant_id,
        deletion_request_id=request_id,
        user_id=current_user.id,
    )
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel — grace period expired or request not found",
        )
    await session.commit()
    return {"status": "cancelled"}


# Consent Tracking
@router.post("/consent", response_model=ConsentLogResponse, status_code=status.HTTP_201_CREATED)
async def log_consent(
    consent_type: str,
    version: str,
    given: bool,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> ConsentLogResponse:
    """Log user consent (T&C, privacy policy, cookies)."""
    service = GDPRService(session)
    consent = await service.log_consent(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        consent_type=consent_type,
        version=version,
        given=given,
    )
    await session.commit()
    return ConsentLogResponse.model_validate(consent)


@router.get("/consent", response_model=list[ConsentLogResponse])
async def get_user_consents(
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[ConsentLogResponse]:
    """Get user's consent history."""
    service = GDPRService(session)
    consents = await service.get_user_consents(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    return [ConsentLogResponse.model_validate(c) for c in consents]


# Audit Trail
@router.get("/audit-trail", response_model=list[AuditTrailResponse])
async def get_audit_trail(
    skip: int = 0,
    limit: int = 100,
    resource_type: str | None = None,
    action: str | None = None,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[AuditTrailResponse]:
    """Get audit trail (admin only)."""
    service = GDPRService(session)
    trails = await service.get_audit_trail(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
        resource_type=resource_type,
        action=action,
    )
    return [AuditTrailResponse.model_validate(t) for t in trails]
