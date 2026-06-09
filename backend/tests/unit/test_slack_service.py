"""Unit tests for Slack service."""

import pytest
from datetime import datetime, timezone, date
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session

from app.domains.analytics.slack_models import (
    SlackSubscription,
    SlackNotificationQueue,
    SlackDeliveryLog,
)
from app.domains.analytics.slack_service import SlackService
from app.domains.analytics import slack_schemas as domain_schemas


@pytest.fixture
def slack_service(db: Session) -> SlackService:
    """Create Slack service instance."""
    return SlackService(db)


class TestSlackSubscription:
    """Slack subscription tests."""

    def test_create_subscription(self, slack_service: SlackService):
        """Test creating a Slack subscription."""
        tenant_id = "test-tenant-1"

        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            channel_name="test-alerts",
            event_types=["test_run", "defect"],
            webhook_url="https://hooks.slack.com/test",
        )

        result = slack_service.create_subscription(
            tenant_id, subscription_data, created_by="user-1"
        )

        assert result.id is not None
        assert result.tenant_id == tenant_id
        assert result.workspace_id == "W123456"
        assert result.channel_id == "C123456"
        assert result.is_active is True

    def test_get_subscriptions(self, slack_service: SlackService):
        """Test getting subscriptions."""
        tenant_id = "test-tenant-1"

        # Create multiple subscriptions
        for i in range(3):
            subscription_data = domain_schemas.SlackSubscriptionCreate(
                workspace_id="W123456",
                channel_id=f"C{i}",
                event_types=["test_run"],
                webhook_url=f"https://hooks.slack.com/test{i}",
            )
            slack_service.create_subscription(tenant_id, subscription_data)

        results = slack_service.get_subscriptions(tenant_id)

        assert len(results) == 3
        assert all(s.tenant_id == tenant_id for s in results)

    def test_update_subscription(self, slack_service: SlackService):
        """Test updating a subscription."""
        tenant_id = "test-tenant-1"

        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )

        created = slack_service.create_subscription(tenant_id, subscription_data)

        update = domain_schemas.SlackSubscriptionUpdate(
            event_types=["test_run", "defect", "coverage"],
            is_active=False,
        )

        updated = slack_service.update_subscription(created.id, update)

        assert updated.event_types == ["test_run", "defect", "coverage"]
        assert updated.is_active is False

    def test_delete_subscription(self, slack_service: SlackService, db: Session):
        """Test deleting a subscription."""
        tenant_id = "test-tenant-1"

        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )

        created = slack_service.create_subscription(tenant_id, subscription_data)

        slack_service.delete_subscription(created.id)

        # Verify it's deleted
        deleted = db.get(SlackSubscription, created.id)
        assert deleted is None


class TestSlackNotificationQueue:
    """Slack notification queue tests."""

    def test_enqueue_notification(self, slack_service: SlackService):
        """Test enqueueing a notification."""
        tenant_id = "test-tenant-1"

        # Create subscription first
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        # Enqueue notification
        message = {"text": "Test notification"}
        queue_item = slack_service.enqueue_notification(
            tenant_id, subscription.id, "event-123", message
        )

        assert queue_item.id is not None
        assert queue_item.status == "pending"
        assert queue_item.retry_count == 0
        assert queue_item.message_body == message

    def test_get_pending_notifications(self, slack_service: SlackService):
        """Test getting pending notifications."""
        tenant_id = "test-tenant-1"

        # Create subscription
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        # Enqueue multiple notifications
        for i in range(5):
            message = {"text": f"Notification {i}"}
            slack_service.enqueue_notification(
                tenant_id, subscription.id, f"event-{i}", message
            )

        pending = slack_service.get_pending_notifications(tenant_id)

        assert len(pending) == 5
        assert all(p.status == "pending" for p in pending)


class TestSlackDeliveryLog:
    """Slack delivery log tests."""

    def test_get_delivery_logs(self, slack_service: SlackService):
        """Test getting delivery logs."""
        tenant_id = "test-tenant-1"

        # Create subscription
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        # Create delivery logs
        for i in range(3):
            slack_service._log_delivery(
                tenant_id,
                type("QueueItem", (), {
                    "subscription_id": subscription.id,
                    "channel_id": "C123456",
                })(),  # type: ignore
                success=(i % 2 == 0),
                status_code=200 if i % 2 == 0 else 500,
            )

        logs = slack_service.get_delivery_logs(tenant_id, channel_id="C123456")

        assert len(logs) >= 3
        successful = [l for l in logs if l.success]
        assert len(successful) > 0


class TestSlackMessageBuilding:
    """Test Slack message building."""

    def test_build_event_message(self):
        """Test building event message."""
        event = domain_schemas.SlackEventNotification(
            event_id="evt-123",
            event_type="test_run",
            event_name="test_run_completed",
            title="Test Run Completed",
            description="All tests passed",
            details={"duration": "45.5s", "tests": "42"},
            severity="info",
            action_url="https://app.example.com/runs/123",
            timestamp=datetime.now(timezone.utc),
        )

        message = SlackService.build_event_message(event)

        assert "blocks" in message
        assert len(message["blocks"]) > 0
        assert any("Test Run Completed" in str(b) for b in message["blocks"])

    def test_build_digest_message(self):
        """Test building digest message."""
        digest_data = domain_schemas.SlackDailyDigestData(
            date=date.today(),
            summary="Daily QA summary",
            test_executions=42,
            test_pass_rate=95.5,
            defects_created=3,
            defects_resolved=2,
            coverage_change=1.5,
            team_velocity={"velocity": 42},
            top_issues=[
                {"title": "Login timeout", "count": 3},
                {"title": "Memory leak", "count": 2},
            ],
            metrics_snapshot={"coverage": 85.2},
        )

        message = SlackService.build_digest_message(digest_data)

        assert "blocks" in message
        assert len(message["blocks"]) > 0

    def test_message_color_selection(self):
        """Test color selection for different severities."""
        severities = ["info", "warning", "critical"]

        for severity in severities:
            event = domain_schemas.SlackEventNotification(
                event_id="evt-123",
                event_type="test",
                event_name="test",
                title="Test",
                severity=severity,
                timestamp=datetime.now(timezone.utc),
            )

            message = SlackService.build_event_message(event)
            assert "attachments" in message
            assert len(message["attachments"]) > 0


class TestSlackDailyDigest:
    """Test daily digest functionality."""

    def test_create_daily_digest(self, slack_service: SlackService):
        """Test creating daily digest."""
        tenant_id = "test-tenant-1"

        # Create subscription
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["digest"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        digest_data = {
            "summary": "Daily summary",
            "test_count": 42,
        }

        digest = slack_service.create_daily_digest(
            tenant_id, subscription.id, date.today(), digest_data
        )

        assert digest.id is not None
        assert digest.digest_data == digest_data
        assert digest.sent_at is None

    def test_get_unsent_digests(self, slack_service: SlackService):
        """Test getting unsent digests."""
        tenant_id = "test-tenant-1"

        # Create subscription
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["digest"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        # Create multiple digests
        for i in range(3):
            digest_data = {"summary": f"Summary {i}"}
            slack_service.create_daily_digest(
                tenant_id,
                subscription.id,
                date.today().replace(day=i + 1),
                digest_data,
            )

        unsent = slack_service.get_unsent_digests(tenant_id)

        assert len(unsent) == 3
        assert all(d.sent_at is None for d in unsent)


class TestSlackIntegration:
    """Integration tests for Slack service."""

    def test_subscription_lifecycle(self, slack_service: SlackService):
        """Test complete subscription lifecycle."""
        tenant_id = "test-tenant-1"

        # Create
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        # Update
        update = domain_schemas.SlackSubscriptionUpdate(
            event_types=["test_run", "defect"]
        )
        updated = slack_service.update_subscription(subscription.id, update)
        assert len(updated.event_types) == 2

        # Delete
        slack_service.delete_subscription(subscription.id)

    def test_notification_queue_and_logging(self, slack_service: SlackService):
        """Test notification queuing and logging."""
        tenant_id = "test-tenant-1"

        # Create subscription
        subscription_data = domain_schemas.SlackSubscriptionCreate(
            workspace_id="W123456",
            channel_id="C123456",
            event_types=["test_run"],
            webhook_url="https://hooks.slack.com/test",
        )
        subscription = slack_service.create_subscription(tenant_id, subscription_data)

        # Enqueue
        message = {"text": "Test"}
        queue_item = slack_service.enqueue_notification(
            tenant_id, subscription.id, "evt-1", message
        )

        # Log delivery
        slack_service._log_delivery(
            tenant_id, queue_item, success=True, status_code=200
        )

        # Verify
        logs = slack_service.get_delivery_logs(tenant_id)
        assert len(logs) > 0
        assert logs[0].success is True
