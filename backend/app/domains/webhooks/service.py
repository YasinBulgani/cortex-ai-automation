"""Webhooks domain service — webhook management, delivery, retries."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone as _tz
from typing import Any, Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.webhooks.models import WebhookConfig, WebhookDelivery, WebhookLog
from app.domains.webhooks.schemas import (
    WebhookConfigCreateRequest,
    WebhookConfigUpdateRequest,
)

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for webhook management and delivery."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook(
        self,
        tenant_id: str,
        created_by: str,
        request: WebhookConfigCreateRequest,
    ) -> WebhookConfig:
        """Create webhook configuration."""
        webhook = WebhookConfig(
            tenant_id=tenant_id,
            created_by=created_by,
            webhook_type=request.webhook_type,
            provider=request.provider,
            target_url=request.target_url,
            secret=request.secret,
            events=request.events,
            rate_limit_per_minute=request.rate_limit_per_minute,
            rate_limit_per_day=request.rate_limit_per_day,
            max_retries=request.max_retries,
            retry_backoff_seconds=request.retry_backoff_seconds,
            description=request.description,
            auth_method=request.auth_method,
            auth_credentials=request.auth_credentials,
        )
        self.db.add(webhook)
        await self.db.flush()

        # Log creation
        await self._log_action(
            tenant_id=tenant_id,
            webhook_config_id=webhook.id,
            user_id=created_by,
            action="created",
            details={"webhook_type": webhook.webhook_type, "target_url": webhook.target_url},
        )

        return webhook

    async def update_webhook(
        self,
        tenant_id: str,
        webhook_id: str,
        request: WebhookConfigUpdateRequest,
        updated_by: str,
    ) -> Optional[WebhookConfig]:
        """Update webhook configuration."""
        result = await self.db.execute(
            select(WebhookConfig).where(
                WebhookConfig.id == webhook_id,
                WebhookConfig.tenant_id == tenant_id,
            )
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            return None

        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(webhook, key, value)

        webhook.updated_at = datetime.now(_tz.utc)
        await self.db.flush()

        await self._log_action(
            tenant_id=tenant_id,
            webhook_config_id=webhook_id,
            user_id=updated_by,
            action="updated",
            details=update_data,
        )

        return webhook

    async def get_webhook(self, tenant_id: str, webhook_id: str) -> Optional[WebhookConfig]:
        """Get webhook by ID."""
        result = await self.db.execute(
            select(WebhookConfig).where(
                WebhookConfig.id == webhook_id,
                WebhookConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_webhooks(self, tenant_id: str, skip: int = 0, limit: int = 50) -> list[WebhookConfig]:
        """List webhooks for tenant."""
        result = await self.db.execute(
            select(WebhookConfig)
            .where(WebhookConfig.tenant_id == tenant_id)
            .order_by(WebhookConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def delete_webhook(self, tenant_id: str, webhook_id: str, deleted_by: str) -> bool:
        """Delete webhook configuration."""
        result = await self.db.execute(
            select(WebhookConfig).where(
                WebhookConfig.id == webhook_id,
                WebhookConfig.tenant_id == tenant_id,
            )
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            return False

        await self.db.delete(webhook)
        await self._log_action(
            tenant_id=tenant_id,
            webhook_config_id=webhook_id,
            user_id=deleted_by,
            action="deleted",
            details={},
        )

        return True

    async def trigger_webhook(
        self,
        webhook_config_id: str,
        event_type: str,
        event_data: dict[str, Any],
        entity_id: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> WebhookDelivery:
        """Trigger webhook delivery."""
        webhook = await self.db.get(WebhookConfig, webhook_config_id)
        if not webhook or not webhook.is_active:
            raise ValueError(f"Webhook {webhook_config_id} not found or inactive")

        # Check event subscription
        if event_type not in webhook.events:
            raise ValueError(f"Webhook not subscribed to event {event_type}")

        # Create delivery record
        delivery = WebhookDelivery(
            webhook_config_id=webhook_config_id,
            tenant_id=webhook.tenant_id,
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type,
            attempt_number=1,
            status="pending",
            request_body=event_data,
        )
        self.db.add(delivery)
        await self.db.flush()

        # Attempt delivery
        await self._deliver_webhook(webhook, delivery)

        return delivery

    async def _deliver_webhook(
        self,
        webhook: WebhookConfig,
        delivery: WebhookDelivery,
    ) -> None:
        """Deliver webhook with retries."""
        payload = {
            "event_type": delivery.event_type,
            "entity_id": delivery.entity_id,
            "entity_type": delivery.entity_type,
            "timestamp": datetime.now(_tz.utc).isoformat(),
            "data": delivery.request_body,
        }

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": self._sign_payload(webhook.secret, payload),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.target_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    delivery.http_status_code = response.status
                    delivery.response_body = await response.text()

                    if response.status in (200, 201, 202):
                        delivery.status = "success"
                        delivery.delivered_at = datetime.now(_tz.utc)
                    else:
                        delivery.status = "failed"
                        delivery.next_retry_at = datetime.now(_tz.utc) + timedelta(
                            seconds=webhook.retry_backoff_seconds
                        )

        except Exception as exc:
            logger.exception(f"Failed to deliver webhook {webhook.id}: {exc}")
            delivery.status = "failed"
            delivery.error_message = str(exc)
            delivery.next_retry_at = datetime.now(_tz.utc) + timedelta(
                seconds=webhook.retry_backoff_seconds
            )

        await self.db.flush()

    async def retry_failed_deliveries(self) -> None:
        """Retry failed webhook deliveries."""
        result = await self.db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.status.in_(["failed", "retrying"]),
                WebhookDelivery.next_retry_at <= datetime.now(_tz.utc),
                WebhookDelivery.attempt_number < 7,
            )
        )
        deliveries = result.scalars().all()

        for delivery in deliveries:
            webhook = await self.db.get(WebhookConfig, delivery.webhook_config_id)
            if not webhook:
                continue

            delivery.attempt_number += 1
            delivery.status = "retrying"

            await self._deliver_webhook(webhook, delivery)

    def _sign_payload(self, secret: str, payload: dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for webhook payload."""
        payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={signature}"

    async def _log_action(
        self,
        tenant_id: str,
        action: str,
        details: dict[str, Any],
        webhook_config_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Log webhook action."""
        log = WebhookLog(
            tenant_id=tenant_id,
            webhook_config_id=webhook_config_id,
            user_id=user_id,
            action=action,
            details=details,
        )
        self.db.add(log)
        await self.db.flush()
