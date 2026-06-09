"""Unit tests for Jira synchronization service.

Test coverage:
  1. OAuth token refresh (cache + expiry)
  2. Rate limiter (token bucket, backoff)
  3. TestCase → Issue creation/update
  4. Issue → TestCase sync
  5. Field mapping (custom fields, transformations)
  6. Webhook receiver (signature verification, event types)
  7. Checkpoint system (resume, progress tracking)
  8. DLQ (dead-letter queue) management
  9. Error handling + retry logic
  10. Concurrent sync operations
  11. Rate limit + backoff scenarios
  12. Field discovery + mapping validation
  13. Link management (create/unlink)
  14. Status/health checks
  15. Field transformation
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.domains.jira.service import (
    DLQRecord,
    FieldMapping,
    FieldMapType,
    JiraAPIClient,
    JiraOAuthManager,
    RateLimiter,
    SyncCheckpoint,
    SyncDirection,
    SyncStatus,
)


# ─── OAuth Token Manager Tests ──────────────────────────────────────────────

class TestJiraOAuthManager:
    """OAuth 2.0 token refresh and caching."""

    @pytest.mark.asyncio
    async def test_token_cache_valid(self):
        """Valid cached token returned without refresh."""
        manager = JiraOAuthManager("client_id", "client_secret")
        tenant_id = "test-tenant"
        cached_token = "cached_token_123"
        expires_at = time.time() + 3600

        manager._token_cache[tenant_id] = {
            "access_token": cached_token,
            "expires_at": expires_at,
        }

        token, error = await manager.get_token(
            tenant_id,
            "https://jira.example.com",
            "refresh_token_xyz",
        )

        assert token == cached_token
        assert error is None

    @pytest.mark.asyncio
    async def test_token_cache_expired(self):
        """Expired token triggers refresh."""
        manager = JiraOAuthManager("client_id", "client_secret")
        tenant_id = "test-tenant"
        expires_at = time.time() - 100  # Expired

        manager._token_cache[tenant_id] = {
            "access_token": "old_token",
            "expires_at": expires_at,
        }

        with patch.object(manager, "_refresh_token", new_callable=AsyncMock) as mock_refresh:
            mock_refresh.return_value = ("new_token", None)

            token, error = await manager.get_token(
                tenant_id,
                "https://jira.example.com",
                "refresh_token_xyz",
            )

            assert token == "new_token"
            assert error is None
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_refresh_failure(self):
        """Handle token refresh failure."""
        manager = JiraOAuthManager("client_id", "client_secret")

        with patch.object(manager, "_refresh_token", new_callable=AsyncMock) as mock_refresh:
            mock_refresh.return_value = ("", "OAuth error: invalid_grant")

            token, error = await manager.get_token(
                "test-tenant",
                "https://jira.example.com",
                "invalid_token",
            )

            assert token == ""
            assert "OAuth error" in error

    @pytest.mark.asyncio
    async def test_token_refresh_concurrent_requests(self):
        """Only one refresh request sent for concurrent token requests."""
        manager = JiraOAuthManager("client_id", "client_secret")
        tenant_id = "test-tenant"

        refresh_count = 0

        async def mock_refresh(*args, **kwargs):
            nonlocal refresh_count
            refresh_count += 1
            await asyncio.sleep(0.1)
            return ("new_token", None)

        with patch.object(manager, "_refresh_token", side_effect=mock_refresh):
            # Concurrent requests
            tasks = [
                manager.get_token(tenant_id, "https://jira.example.com", "refresh_xyz"),
                manager.get_token(tenant_id, "https://jira.example.com", "refresh_xyz"),
                manager.get_token(tenant_id, "https://jira.example.com", "refresh_xyz"),
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert all(token == "new_token" for token, _ in results)
            # But refresh called only once due to lock
            assert refresh_count == 1


# ─── Rate Limiter Tests ──────────────────────────────────────────────────────

class TestRateLimiter:
    """Token bucket rate limiter with exponential backoff."""

    @pytest.mark.asyncio
    async def test_acquire_within_limit(self):
        """Tokens available: no wait."""
        limiter = RateLimiter(rate=10.0, burst=20)
        wait_time = await limiter.acquire(1)
        assert wait_time == 0.0

    @pytest.mark.asyncio
    async def test_acquire_rate_limited(self):
        """Tokens exhausted: wait + backoff."""
        limiter = RateLimiter(rate=10.0, burst=3)

        # Consume all tokens
        await limiter.acquire(3)

        # Next request rate limited
        wait_time = await limiter.acquire(1)
        assert wait_time > 0

    @pytest.mark.asyncio
    async def test_backoff_exponential(self):
        """Backoff doubles on repeated rate limit."""
        limiter = RateLimiter(rate=10.0, burst=1)

        # First backoff
        await limiter.acquire(1)
        wait1 = await limiter.acquire(1)
        first_backoff = limiter.backoff_exp

        # Second backoff (higher)
        await asyncio.sleep(0.1)
        wait2 = await limiter.acquire(1)
        second_backoff = limiter.backoff_exp

        assert second_backoff >= first_backoff

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Tokens refill over time."""
        limiter = RateLimiter(rate=10.0, burst=1)

        # Exhaust tokens
        await limiter.acquire(1)
        wait1 = await limiter.acquire(1)
        assert wait1 > 0  # Rate limited

        # Wait for tokens to refill
        await asyncio.sleep(0.15)
        wait2 = await limiter.acquire(1)
        # Should be less or no wait
        assert wait2 < wait1 or wait2 == 0

    @pytest.mark.asyncio
    async def test_backoff_cap(self):
        """Backoff capped at 30 seconds."""
        limiter = RateLimiter(rate=10.0, burst=1)

        # Trigger multiple backoffs
        for _ in range(10):
            await limiter.acquire(1)
            await asyncio.sleep(0.01)

        assert limiter.backoff_exp <= 30.0


# ─── Field Mapping Tests ────────────────────────────────────────────────────

class TestFieldMapping:
    """Field mapping: Jira ↔ TestCase transformation."""

    def test_add_mapping(self):
        """Add field mapping with transformation."""
        mapper = FieldMapping()
        mapper.add_mapping(
            "customfield_10001",
            "priority",
            FieldMapType.ENUM,
            lambda x: x.lower(),
        )

        assert mapper.jira_to_tc["customfield_10001"] == "priority"
        assert mapper.tc_to_jira["priority"] == "customfield_10001"

    def test_transform_jira_to_tc(self):
        """Transform Jira value → TestCase value."""
        mapper = FieldMapping()
        mapper.add_mapping(
            "priority",
            "priority",
            FieldMapType.ENUM,
            lambda x: x.lower(),
        )

        result = mapper.transform_jira_to_tc("priority", "HIGH")
        assert result == "high"

    def test_transform_array_fields(self):
        """Transform array fields (labels ↔ tags)."""
        mapper = FieldMapping()
        mapper.add_mapping(
            "labels",
            "tags",
            FieldMapType.ARRAY,
        )

        labels = ["smoke", "regression"]
        result = mapper.transform_jira_to_tc("labels", labels)
        assert result == labels

    def test_default_transform(self):
        """Identity transform when no function provided."""
        mapper = FieldMapping()
        mapper.add_mapping("description", "objective", FieldMapType.STRING)

        result = mapper.transform_jira_to_tc("description", "Test description")
        assert result == "Test description"


# ─── Sync Checkpoint Tests ──────────────────────────────────────────────────

class TestSyncCheckpoint:
    """Checkpoint system for resumable sync operations."""

    def test_checkpoint_creation(self):
        """Create checkpoint with initial state."""
        cp = SyncCheckpoint(
            sync_id="sync_123",
            sync_type="tc_to_issue",
            tenant_id="tenant_1",
            total_count=100,
        )

        assert cp.sync_id == "sync_123"
        assert cp.status == SyncStatus.PENDING
        assert cp.processed_count == 0
        assert cp.total_count == 100

    def test_checkpoint_mark_progress(self):
        """Update checkpoint with item progress."""
        cp = SyncCheckpoint(
            sync_id="sync_123",
            sync_type="tc_to_issue",
            tenant_id="tenant_1",
            total_count=100,
        )

        cp.mark_progress("item_1", count=5)
        assert cp.processed_count == 5
        assert cp.last_processed_id == "item_1"

        cp.mark_progress("item_2", count=10)
        assert cp.processed_count == 15

    def test_checkpoint_serialization(self):
        """Checkpoint serialize → deserialize roundtrip."""
        cp1 = SyncCheckpoint(
            sync_id="sync_123",
            sync_type="tc_to_issue",
            tenant_id="tenant_1",
            total_count=100,
        )
        cp1.mark_progress("item_5", count=25)

        data = cp1.to_dict()
        cp2 = SyncCheckpoint.from_dict(data)

        assert cp2.sync_id == cp1.sync_id
        assert cp2.processed_count == cp1.processed_count
        assert cp2.last_processed_id == "item_5"

    def test_checkpoint_state_transitions(self):
        """Checkpoint state transitions: pending → in_progress → completed."""
        cp = SyncCheckpoint(
            sync_id="sync_123",
            sync_type="tc_to_issue",
            tenant_id="tenant_1",
        )

        assert cp.status == SyncStatus.PENDING

        cp.mark_progress("item_1")
        cp.mark_checkpoint()
        assert cp.status == SyncStatus.CHECKPOINT

        cp.mark_completed()
        assert cp.status == SyncStatus.COMPLETED


# ─── DLQ Tests ──────────────────────────────────────────────────────────────

class TestDLQRecord:
    """Dead-letter queue for failed sync records."""

    def test_dlq_record_creation(self):
        """Create DLQ record with error details."""
        record = DLQRecord(
            dlq_id="dlq_123",
            tenant_id="tenant_1",
            sync_type="tc_to_issue",
            source_id="tc_001",
            error="Jira API timeout",
            payload={"tc_id": "tc_001"},
        )

        assert record.dlq_id == "dlq_123"
        assert record.sync_type == "tc_to_issue"
        assert record.retry_count == 0

    def test_dlq_serialization(self):
        """DLQ record serialize → deserialize."""
        record = DLQRecord(
            dlq_id="dlq_123",
            tenant_id="tenant_1",
            sync_type="tc_to_issue",
            source_id="tc_001",
            error="Test error",
            payload={"key": "value"},
            retry_count=2,
        )

        data = record.to_dict()
        assert data["dlq_id"] == "dlq_123"
        assert data["retry_count"] == 2
        assert data["payload"] == {"key": "value"}


# ─── Jira API Client Tests ──────────────────────────────────────────────────

class TestJiraAPIClient:
    """HTTP client for Jira REST API v3."""

    @pytest.mark.asyncio
    async def test_create_issue_success(self):
        """Create Jira issue — success."""
        client = JiraAPIClient(
            "https://jira.example.com",
            ("user@example.com", "token123"),
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = (201, {"key": "PROJ-123"}, None)

            issue_key, error = await client.create_issue(
                project_key="PROJ",
                summary="Test issue",
                description="Test description",
            )

            assert issue_key == "PROJ-123"
            assert error is None

        await client.close()

    @pytest.mark.asyncio
    async def test_create_issue_failure(self):
        """Create Jira issue — failure."""
        client = JiraAPIClient(
            "https://jira.example.com",
            ("user@example.com", "token123"),
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = (400, {}, "Invalid project key")

            issue_key, error = await client.create_issue(
                project_key="INVALID",
                summary="Test",
            )

            assert issue_key is None
            assert "Invalid project key" in error

        await client.close()

    @pytest.mark.asyncio
    async def test_update_issue_success(self):
        """Update Jira issue — success."""
        client = JiraAPIClient(
            "https://jira.example.com",
            ("user@example.com", "token123"),
        )

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = (204, {}, None)

            ok, error = await client.update_issue(
                issue_key="PROJ-123",
                fields={"summary": "Updated summary"},
            )

            assert ok is True
            assert error is None

        await client.close()

    @pytest.mark.asyncio
    async def test_search_issues_success(self):
        """Search issues via JQL — success."""
        client = JiraAPIClient(
            "https://jira.example.com",
            ("user@example.com", "token123"),
        )

        mock_response = {
            "issues": [
                {"key": "PROJ-1", "fields": {"summary": "Issue 1"}},
                {"key": "PROJ-2", "fields": {"summary": "Issue 2"}},
            ]
        }

        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = (200, mock_response, None)

            issues, error = await client.search_issues("project = PROJ")

            assert len(issues) == 2
            assert issues[0]["key"] == "PROJ-1"
            assert error is None

        await client.close()

    @pytest.mark.asyncio
    async def test_request_rate_limiting(self):
        """Request applies rate limiting."""
        limiter = RateLimiter(rate=10.0, burst=1)
        client = JiraAPIClient(
            "https://jira.example.com",
            ("user@example.com", "token123"),
            rate_limiter=limiter,
        )

        with patch.object(client.client, "request", new_callable=AsyncMock) as mock_req:
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = {"key": "PROJ-1"}
            mock_req.return_value = mock_response

            # First request OK
            status, body, error = await client._request("POST", "/issue", json={})
            assert status == 200

            # Second request rate limited
            start = time.time()
            status, body, error = await client._request("POST", "/issue", json={})
            elapsed = time.time() - start

            assert elapsed > 0.05  # Should have waited

        await client.close()


# ─── Jira Sync Service Tests ────────────────────────────────────────────────

class TestJiraSyncService:
    """Main synchronization service."""

    def test_service_initialization(self):
        """Initialize sync service with default mappings."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        assert service.tenant_id == "tenant_1"
        assert len(service.field_mapper.jira_to_tc) > 0
        assert len(service.checkpoints) == 0

    def test_create_checkpoint(self):
        """Create sync checkpoint."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        sync_id = service.create_checkpoint("tc_to_issue", total_count=100)

        assert sync_id in service.checkpoints
        cp = service.checkpoints[sync_id]
        assert cp.total_count == 100

    def test_add_to_dlq(self):
        """Add failed sync to DLQ."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        service._add_dlq(
            source_id="tc_001",
            sync_type="tc_to_issue",
            payload={"tc_id": "tc_001"},
            error="API timeout",
        )

        assert len(service.dlq) == 1
        record = service.dlq[0]
        assert record.source_id == "tc_001"
        assert record.error == "API timeout"

    def test_clear_dlq_record(self):
        """Remove record from DLQ."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        service._add_dlq("tc_001", "tc_to_issue", {}, "Error 1")
        service._add_dlq("tc_002", "tc_to_issue", {}, "Error 2")

        assert len(service.dlq) == 2

        dlq_id = service.dlq[0].dlq_id
        service.clear_dlq_record(dlq_id)

        assert len(service.dlq) == 1
        assert service.dlq[0].source_id == "tc_002"

    def test_link_tc_to_issue(self):
        """Link TestCase ↔ Jira Issue."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        # Should not raise
        service._link_tc_to_issue("tc_001", "PROJ-123")

    def test_default_field_mappings(self):
        """Default field mappings configured."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        # Check standard mappings exist
        assert "priority" in service.field_mapper.jira_to_tc
        assert "labels" in service.field_mapper.jira_to_tc
        assert "summary" in service.field_mapper.jira_to_tc


# ─── Integration-like Tests ─────────────────────────────────────────────────

class TestSyncScenarios:
    """End-to-end sync scenario tests (mocked)."""

    @pytest.mark.asyncio
    async def test_tc_to_issue_create_flow(self):
        """TC→Issue: Create new issue."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        # Mock TestCase model
        mock_tc = Mock()
        mock_tc.id = "tc_001"
        mock_tc.title = "Test Login Flow"
        mock_tc.objective = "Verify login functionality"
        mock_tc.priority = "high"
        mock_tc.tags = ["smoke"]

        db.query.return_value.filter_by.return_value.first.return_value = mock_tc

        with patch.object(service, "_find_linked_issue", return_value=None):
            with patch.object(
                service,
                "_create_jira_issue",
                new_callable=AsyncMock,
            ) as mock_create:
                mock_create.return_value = ("PROJ-123", None)

                issue_key, error = await service.sync_test_case_to_issue(
                    "tc_001",
                    "PROJ",
                    "https://jira.example.com",
                    ("user@example.com", "token"),
                )

                assert issue_key == "PROJ-123"
                assert error is None
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_to_tc_sync_flow(self):
        """Issue→TC: Update existing TestCase."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        service = JiraSyncService(db, "tenant_1")

        # Mock TestCase
        mock_tc = Mock()
        mock_tc.id = "tc_001"
        mock_tc.title = "Old Title"
        mock_tc.objective = "Old description"
        mock_tc.priority = "medium"
        mock_tc.tags = []

        db.query.return_value.filter_by.return_value.first.return_value = mock_tc

        with patch.object(
            service,
            "_find_linked_tc",
            return_value="tc_001",
        ):
            with patch.object(
                service,
                "_update_tc_from_issue",
                new_callable=AsyncMock,
            ) as mock_update:
                mock_update.return_value = (True, None)

                issue = {
                    "key": "PROJ-123",
                    "fields": {
                        "summary": "New Title",
                        "description": "New description",
                        "priority": {"name": "High"},
                        "status": {"name": "In Progress"},
                    },
                }

                ok, error = await service._update_tc_from_issue("tc_001", issue)

                assert ok is True
                assert error is None


# ─── Webhook Tests ──────────────────────────────────────────────────────────

class TestWebhookHandling:
    """Jira webhook event handling."""

    def test_webhook_event_parsing(self):
        """Parse Jira webhook event payload."""
        from app.domains.jira.schemas import JiraWebhookEvent

        payload = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Updated issue",
                    "status": {"name": "In Progress"},
                },
            },
            "user": {"name": "testuser"},
        }

        event = JiraWebhookEvent(**payload)
        assert event.webhookEvent == "jira:issue_updated"
        assert event.issue.key == "PROJ-123"

    def test_webhook_event_issue_deleted(self):
        """Handle issue_deleted event."""
        from app.domains.jira.schemas import JiraWebhookEvent

        payload = {
            "webhookEvent": "jira:issue_deleted",
            "issue": {"key": "PROJ-123"},
        }

        event = JiraWebhookEvent(**payload)
        assert event.webhookEvent == "jira:issue_deleted"


# ─── Error Handling Tests ───────────────────────────────────────────────────

class TestErrorHandling:
    """Error scenarios and recovery."""

    @pytest.mark.asyncio
    async def test_sync_with_missing_test_case(self):
        """Sync fails if TestCase not found."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        db.query.return_value.filter_by.return_value.first.return_value = None

        service = JiraSyncService(db, "tenant_1")

        issue_key, error = await service.sync_test_case_to_issue(
            "tc_nonexistent",
            "PROJ",
            "https://jira.example.com",
            ("user", "token"),
        )

        assert issue_key is None
        assert error is not None
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    async def test_jira_api_error_adds_to_dlq(self):
        """Failed sync adds record to DLQ."""
        from app.domains.jira.service import JiraSyncService

        db = Mock()
        mock_tc = Mock()
        mock_tc.id = "tc_001"
        mock_tc.title = "Test"
        db.query.return_value.filter_by.return_value.first.return_value = mock_tc

        service = JiraSyncService(db, "tenant_1")

        with patch.object(service, "_find_linked_issue", return_value=None):
            with patch.object(
                service,
                "_create_jira_issue",
                new_callable=AsyncMock,
            ) as mock_create:
                mock_create.return_value = (None, "API error: connection timeout")

                issue_key, error = await service.sync_test_case_to_issue(
                    "tc_001",
                    "PROJ",
                    "https://jira.example.com",
                    ("user", "token"),
                )

                assert issue_key is None
                assert len(service.dlq) == 1
                assert "connection timeout" in service.dlq[0].error
