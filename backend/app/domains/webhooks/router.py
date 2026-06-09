"""Webhooks domain router — webhook management endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user, get_session, CurrentUserDep, SessionDep
from app.domains.webhooks.schemas import (
    WebhookConfigCreateRequest,
    WebhookConfigResponse,
    WebhookConfigUpdateRequest,
    WebhookDeliveryResponse,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.domains.webhooks.service import WebhookService

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("", response_model=WebhookConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: WebhookConfigCreateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> WebhookConfigResponse:
    """Create webhook configuration."""
    service = WebhookService(session)
    webhook = await service.create_webhook(
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        request=request,
    )
    await session.commit()
    return WebhookConfigResponse.model_validate(webhook)


@router.get("/{webhook_id}", response_model=WebhookConfigResponse)
async def get_webhook(
    webhook_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> WebhookConfigResponse:
    """Get webhook configuration."""
    service = WebhookService(session)
    webhook = await service.get_webhook(
        tenant_id=current_user.tenant_id,
        webhook_id=webhook_id,
    )
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return WebhookConfigResponse.model_validate(webhook)


@router.get("", response_model=list[WebhookConfigResponse])
async def list_webhooks(
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[WebhookConfigResponse]:
    """List webhooks for tenant."""
    service = WebhookService(session)
    webhooks = await service.list_webhooks(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return [WebhookConfigResponse.model_validate(w) for w in webhooks]


@router.put("/{webhook_id}", response_model=WebhookConfigResponse)
async def update_webhook(
    webhook_id: str,
    request: WebhookConfigUpdateRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> WebhookConfigResponse:
    """Update webhook configuration."""
    service = WebhookService(session)
    webhook = await service.update_webhook(
        tenant_id=current_user.tenant_id,
        webhook_id=webhook_id,
        request=request,
        updated_by=current_user.id,
    )
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await session.commit()
    return WebhookConfigResponse.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> None:
    """Delete webhook configuration."""
    service = WebhookService(session)
    deleted = await service.delete_webhook(
        tenant_id=current_user.tenant_id,
        webhook_id=webhook_id,
        deleted_by=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await session.commit()


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    request: WebhookTestRequest,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> WebhookTestResponse:
    """Test webhook delivery."""
    service = WebhookService(session)

    webhook = await service.get_webhook(
        tenant_id=current_user.tenant_id,
        webhook_id=webhook_id,
    )
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    try:
        delivery = await service.trigger_webhook(
            webhook_config_id=webhook_id,
            event_type=request.event_type,
            event_data=request.test_data,
        )
        await session.commit()
        return WebhookTestResponse(
            delivery_id=delivery.id,
            status=delivery.status,
            http_status_code=delivery.http_status_code,
            response_body=delivery.response_body,
            error_message=delivery.error_message,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_deliveries(
    webhook_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: CurrentUserDep = Depends(get_current_user),
    session: SessionDep = Depends(get_session),
) -> list[WebhookDeliveryResponse]:
    """List webhook delivery attempts."""
    from sqlalchemy import select

    result = await session.execute(
        select(WebhookDelivery)
        .where(
            WebhookDelivery.webhook_config_id == webhook_id,
            WebhookDelivery.tenant_id == current_user.tenant_id,
        )
        .order_by(WebhookDelivery.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    deliveries = result.scalars().all()
    return [WebhookDeliveryResponse.model_validate(d) for d in deliveries]


# Import models for SQLAlchemy query
from app.domains.webhooks.models import WebhookDelivery
