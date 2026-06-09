"""Slack integration service."""

from __future__ import annotations

import logging
import httpx
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Any
from enum import Enum

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from app.domains.analytics.slack_models import (
    SlackSubscription,
    SlackNotificationQueue,
    SlackDeliveryLog,
    SlackDailyDigest,
)
from app.domains.analytics.models import AnalyticsEvent
from . import slack_schemas as domain_schemas

logger = logging.getLogger(__name__)

SLACK_API_TIMEOUT = 10
SLACK_RETRY_BACKOFF = [1, 2, 5]  # Exponential backoff: 1s, 2s, 5s


class SlackMessageColor(str, Enum):
    """Slack message colors."""

    INFO = "#36a64f"
    WARNING = "#ff9900"
    CRITICAL = "#e74c3c"
    DEFAULT = "#5289c3"


class SlackService:
    """Service for Slack integration."""

    def __init__(self, db: Session):
        self.db = db

    # Subscription Management

    def create_subscription(
        self, tenant_id: str, subscription: domain_schemas.SlackSubscriptionCreate, created_by: Optional[str] = None
    ) -> SlackSubscription:
        """Create Slack subscription."""
        db_subscription = SlackSubscription(
            tenant_id=tenant_id,
            workspace_id=subscription.workspace_id,
            channel_id=subscription.channel_id,
            channel_name=subscription.channel_name,
            event_types=subscription.event_types,
            webhook_url=subscription.webhook_url,
            created_by=created_by,
        )
        self.db.add(db_subscription)
        self.db.commit()
        self.db.refresh(db_subscription)

        logger.info(f"Slack subscription created: {subscription.channel_id} ({db_subscription.id})")
        return db_subscription

    def get_subscriptions(
        self, tenant_id: str, workspace_id: Optional[str] = None, is_active: bool = True
    ) -> list[SlackSubscription]:
        """Get Slack subscriptions."""
        query = select(SlackSubscription).where(SlackSubscription.tenant_id == tenant_id)

        if workspace_id:
            query = query.where(SlackSubscription.workspace_id == workspace_id)

        query = query.where(SlackSubscription.is_active == is_active)

        return self.db.scalars(query).all()

    def update_subscription(
        self, subscription_id: str, update: domain_schemas.SlackSubscriptionUpdate
    ) -> SlackSubscription:
        """Update Slack subscription."""
        subscription = self.db.get(SlackSubscription, subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        if update.channel_name is not None:
            subscription.channel_name = update.channel_name
        if update.event_types is not None:
            subscription.event_types = update.event_types
        if update.is_active is not None:
            subscription.is_active = update.is_active

        subscription.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(subscription)

        return subscription

    def delete_subscription(self, subscription_id: str) -> None:
        """Delete Slack subscription."""
        subscription = self.db.get(SlackSubscription, subscription_id)
        if subscription:
            self.db.delete(subscription)
            self.db.commit()
            logger.info(f"Slack subscription deleted: {subscription_id}")

    # Notification Queue Management

    def enqueue_notification(
        self, tenant_id: str, subscription_id: str, event_id: str, message: dict[str, Any]
    ) -> SlackNotificationQueue:
        """Enqueue Slack notification."""
        subscription = self.db.get(SlackSubscription, subscription_id)
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        queue_item = SlackNotificationQueue(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            event_id=event_id,
            webhook_url=subscription.webhook_url,
            message_body=message,
            status="pending",
        )
        self.db.add(queue_item)
        self.db.commit()
        self.db.refresh(queue_item)

        logger.info(f"Notification queued: {queue_item.id}")
        return queue_item

    def get_pending_notifications(self, tenant_id: str, limit: int = 100) -> list[SlackNotificationQueue]:
        """Get pending notifications for processing."""
        query = (
            select(SlackNotificationQueue)
            .where(
                and_(
                    SlackNotificationQueue.tenant_id == tenant_id,
                    SlackNotificationQueue.status == "pending",
                    SlackNotificationQueue.retry_count < SlackNotificationQueue.max_retries,
                )
            )
            .order_by(SlackNotificationQueue.created_at.asc())
            .limit(limit)
        )

        return self.db.scalars(query).all()

    async def send_notification(self, queue_item: SlackNotificationQueue) -> bool:
        """Send notification to Slack."""
        try:
            async with httpx.AsyncClient(timeout=SLACK_API_TIMEOUT) as client:
                response = await client.post(queue_item.webhook_url, json=queue_item.message_body)
                response.raise_for_status()

                queue_item.status = "sent"
                queue_item.last_attempt_at = datetime.now(timezone.utc)
                self.db.commit()

                # Log delivery
                self._log_delivery(queue_item.tenant_id, queue_item, True, response.status_code)

                logger.info(f"Notification sent: {queue_item.id}")
                return True

        except httpx.HTTPError as e:
            queue_item.retry_count += 1
            queue_item.last_error = str(e)
            queue_item.last_attempt_at = datetime.now(timezone.utc)

            if queue_item.retry_count >= queue_item.max_retries:
                queue_item.status = "dlq"  # Dead letter queue
                logger.error(f"Notification failed after {queue_item.max_retries} retries: {queue_item.id}")
            else:
                queue_item.status = "pending"
                logger.warning(f"Notification retry {queue_item.retry_count}: {queue_item.id}")

            self.db.commit()

            # Log failed delivery
            self._log_delivery(
                queue_item.tenant_id,
                queue_item,
                False,
                None,
                error=str(e),
            )

            return False

        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            queue_item.status = "dlq"
            queue_item.last_error = str(e)
            self.db.commit()
            return False

    # Delivery Logging

    def _log_delivery(
        self,
        tenant_id: str,
        queue_item: SlackNotificationQueue,
        success: bool,
        status_code: Optional[int] = None,
        error: Optional[str] = None,
    ) -> SlackDeliveryLog:
        """Log Slack delivery."""
        subscription = self.db.get(SlackSubscription, queue_item.subscription_id)

        log = SlackDeliveryLog(
            tenant_id=tenant_id,
            notification_queue_id=queue_item.id,
            channel_id=subscription.channel_id if subscription else "unknown",
            channel_name=subscription.channel_name if subscription else None,
            success=success,
            status_code=status_code,
            error_message=error,
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()

        return log

    def get_delivery_logs(
        self,
        tenant_id: str,
        channel_id: Optional[str] = None,
        success: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[SlackDeliveryLog]:
        """Get delivery logs."""
        query = select(SlackDeliveryLog).where(SlackDeliveryLog.tenant_id == tenant_id)

        if channel_id:
            query = query.where(SlackDeliveryLog.channel_id == channel_id)
        if success is not None:
            query = query.where(SlackDeliveryLog.success == success)
        if start_time:
            query = query.where(SlackDeliveryLog.timestamp >= start_time)
        if end_time:
            query = query.where(SlackDeliveryLog.timestamp <= end_time)

        query = query.order_by(SlackDeliveryLog.timestamp.desc()).limit(limit)

        return self.db.scalars(query).all()

    # Daily Digest

    def create_daily_digest(
        self, tenant_id: str, subscription_id: str, digest_date: date, digest_data: dict[str, Any]
    ) -> SlackDailyDigest:
        """Create daily digest."""
        digest = SlackDailyDigest(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            digest_date=digest_date,
            digest_data=digest_data,
        )
        self.db.add(digest)
        self.db.commit()
        self.db.refresh(digest)

        return digest

    def get_unsent_digests(self, tenant_id: str) -> list[SlackDailyDigest]:
        """Get unsent daily digests."""
        query = (
            select(SlackDailyDigest)
            .where(
                and_(
                    SlackDailyDigest.tenant_id == tenant_id,
                    SlackDailyDigest.sent_at.is_(None),
                )
            )
            .order_by(SlackDailyDigest.digest_date.asc())
        )

        return self.db.scalars(query).all()

    # Message Building

    @staticmethod
    def build_event_message(event: domain_schemas.SlackEventNotification) -> dict[str, Any]:
        """Build Slack message for event notification."""
        color = {
            "info": SlackMessageColor.INFO,
            "warning": SlackMessageColor.WARNING,
            "critical": SlackMessageColor.CRITICAL,
        }.get(event.severity, SlackMessageColor.DEFAULT)

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{event.title}*\n{event.description or ''}",
                },
            },
        ]

        if event.details:
            details_text = "\n".join(f"• *{k}*: {v}" for k, v in event.details.items())
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": details_text,
                    },
                }
            )

        if event.action_url:
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "url": event.action_url,
                        }
                    ],
                }
            )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": event.timestamp.isoformat(),
                    }
                ],
            }
        )

        return {
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "mrkdwn_in": ["text"],
                }
            ],
        }

    @staticmethod
    def build_digest_message(digest_data: domain_schemas.SlackDailyDigestData) -> dict[str, Any]:
        """Build Slack message for daily digest."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Daily Summary - {digest_data.date.isoformat()}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": digest_data.summary,
                },
            },
            {
                "type": "divider",
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Test Executions*\n{digest_data.test_executions}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Pass Rate*\n{digest_data.test_pass_rate:.1f}%",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Defects Created*\n{digest_data.defects_created}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Defects Resolved*\n{digest_data.defects_resolved}",
                    },
                ],
            },
        ]

        if digest_data.top_issues:
            issues_text = "\n".join(
                f"• {issue.get('title', 'Unknown')} - {issue.get('count', 0)} occurrences"
                for issue in digest_data.top_issues[:5]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Issues*\n{issues_text}",
                    },
                }
            )

        return {"blocks": blocks}
