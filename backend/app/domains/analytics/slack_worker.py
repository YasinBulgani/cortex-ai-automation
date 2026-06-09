"""Slack notification worker — background task processor."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infra.database import SessionLocal
from app.domains.analytics.slack_service import SlackService
from app.domains.analytics.service import AnalyticsService
from app.domains.analytics.slack_models import SlackSubscription
from app.domains.analytics.models import AnalyticsEvent

logger = logging.getLogger(__name__)


class SlackNotificationWorker:
    """Background worker for processing Slack notifications."""

    def __init__(self):
        self.db: Optional[Session] = None

    def start(self):
        """Start the worker."""
        logger.info("Slack notification worker started")

    async def process_pending_notifications(self) -> int:
        """Process pending notifications with retries."""
        db = SessionLocal()
        try:
            slack_service = SlackService(db)

            # Get all active tenants with pending notifications
            query = select(SlackSubscription.tenant_id).distinct()
            tenant_ids = db.scalars(query).all()

            total_processed = 0
            for tenant_id in tenant_ids:
                pending = slack_service.get_pending_notifications(tenant_id, limit=50)
                for queue_item in pending:
                    success = await slack_service.send_notification(queue_item)
                    if success:
                        total_processed += 1
                        logger.info(f"Notification sent: {queue_item.id}")
                    await asyncio.sleep(0.1)  # Rate limiting

            logger.info(f"Processed {total_processed} notifications")
            return total_processed

        except Exception as e:
            logger.error(f"Error processing notifications: {e}")
            return 0

        finally:
            db.close()

    async def send_daily_digest(self, tenant_id: str, subscription_id: str) -> bool:
        """Send daily digest for a subscription."""
        db = SessionLocal()
        try:
            slack_service = SlackService(db)
            analytics_service = AnalyticsService(db)

            subscription = db.get(SlackSubscription, subscription_id)
            if not subscription or subscription.tenant_id != tenant_id:
                logger.warning(f"Subscription {subscription_id} not found")
                return False

            today = date.today()

            # Get event summary for today
            start = datetime.combine(today, datetime.min.time(), timezone.utc)
            end = datetime.combine(today, datetime.max.time(), timezone.utc)

            test_runs = analytics_service.get_event_count(
                tenant_id, event_type="test_run", start_date=start, end_date=end
            )
            defects_created = analytics_service.get_event_count(
                tenant_id, event_name="defect_created", start_date=start, end_date=end
            )
            defects_resolved = analytics_service.get_event_count(
                tenant_id, event_name="defect_resolved", start_date=start, end_date=end
            )

            # Get latest metrics
            pass_rate_metric = analytics_service.get_latest_metric(
                tenant_id, "test_pass_rate"
            )
            coverage_metric = analytics_service.get_latest_metric(
                tenant_id, "coverage_percentage"
            )

            pass_rate = float(pass_rate_metric.metric_value) if pass_rate_metric else 0.0
            coverage = float(coverage_metric.metric_value) if coverage_metric else 0.0

            digest_data = {
                "date": today.isoformat(),
                "summary": f"Daily test execution summary for {today}",
                "test_executions": test_runs,
                "test_pass_rate": pass_rate,
                "defects_created": defects_created,
                "defects_resolved": defects_resolved,
                "coverage_change": 0.0,
                "team_velocity": {"count": test_runs},
                "top_issues": [],
                "metrics_snapshot": {
                    "pass_rate": pass_rate,
                    "coverage": coverage,
                },
            }

            message = SlackService.build_digest_message(
                type("SlackDailyDigestData", (), digest_data)()  # type: ignore
            )

            # Create digest record
            slack_service.create_daily_digest(
                tenant_id, subscription_id, today, digest_data
            )

            # Enqueue notification
            # Queue a synthetic event for digest
            queue_item = slack_service.db.query(
                SlackNotificationQueue
            ).filter_by(subscription_id=subscription_id).first()

            if not queue_item:
                from app.domains.analytics.slack_models import SlackNotificationQueue
                queue_item = SlackNotificationQueue(
                    tenant_id=tenant_id,
                    subscription_id=subscription_id,
                    event_id="digest-" + today.isoformat(),
                    webhook_url=subscription.webhook_url,
                    message_body=message,
                    status="pending",
                )
                db.add(queue_item)
                db.commit()

            # Send immediately
            success = await slack_service.send_notification(queue_item)
            logger.info(f"Daily digest sent: {subscription_id} ({success})")
            return success

        except Exception as e:
            logger.error(f"Error sending daily digest: {e}")
            return False

        finally:
            db.close()

    async def run(self, interval_seconds: int = 300):
        """Run the worker loop."""
        logger.info(f"Starting Slack worker loop (interval: {interval_seconds}s)")

        while True:
            try:
                await self.process_pending_notifications()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(interval_seconds)


# Singleton instance
_worker: Optional[SlackNotificationWorker] = None


def get_worker() -> SlackNotificationWorker:
    """Get or create worker instance."""
    global _worker
    if _worker is None:
        _worker = SlackNotificationWorker()
    return _worker


async def start_worker(interval: int = 300):
    """Start background worker."""
    worker = get_worker()
    worker.start()
    await worker.run(interval)
