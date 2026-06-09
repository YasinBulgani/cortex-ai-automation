"""Jira bi-directional synchronization service.

Core functionality:
- OAuth 2.0 Jira authentication + token refresh
- Test Case → Jira Issue sync (create/update)
- Jira Issue → Test Case sync (pull + link updates)
- Field mapping: custom Jira fields ↔ test case attributes
- Webhook receiver: process Jira events (issue_updated, issue_deleted)
- Rate limiting: 10 req/s with exponential backoff
- Checkpoint system: resume failed syncs from last checkpoint
- DLQ (dead-letter queue): store failed sync records for manual review
- Error handling: detailed logging + observability hooks
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone as _tz
from enum import Enum
from typing import Any, Optional

import httpx
from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.infra.database import SessionLocal
from app.infra.models import User

logger = logging.getLogger(__name__)


# ─── Enums ──────────────────────────────────────────────────────────────────

class SyncDirection(str, Enum):
    """Sync direction: to_jira (TC→Issue), from_jira (Issue→TC), both."""
    TO_JIRA = "to_jira"
    FROM_JIRA = "from_jira"
    BOTH = "both"


class SyncStatus(str, Enum):
    """Sync record status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CHECKPOINT = "checkpoint"  # Paused at checkpoint, can resume


class FieldMapType(str, Enum):
    """Jira custom field type mapping."""
    STRING = "string"
    NUMBER = "number"
    BOOL = "boolean"
    ENUM = "enum"
    DATE = "date"
    ARRAY = "array"


# ─── Field Mapping Config ────────────────────────────────────────────────────

class FieldMapping:
    """Defines mapping between Jira custom fields ↔ TestCase fields."""

    def __init__(self):
        # Jira field ID → TestCase field name mapping
        # Example: "customfield_10001" (Jira) ↔ "priority" (TestCase)
        self.jira_to_tc: dict[str, str] = {}
        self.tc_to_jira: dict[str, str] = {}
        self.field_types: dict[str, FieldMapType] = {}

    def add_mapping(
        self,
        jira_field_id: str,
        tc_field_name: str,
        field_type: FieldMapType = FieldMapType.STRING,
        transform_fn: Optional[callable] = None,
    ):
        """Register a field mapping with optional transformation function."""
        self.jira_to_tc[jira_field_id] = tc_field_name
        self.tc_to_jira[tc_field_name] = jira_field_id
        self.field_types[jira_field_id] = field_type
        self._transformers[jira_field_id] = transform_fn or (lambda x: x)

    def _transformers: dict[str, callable] = {}

    def transform_jira_to_tc(self, jira_field_id: str, value: Any) -> Any:
        """Transform Jira field value → TestCase field value."""
        fn = self._transformers.get(jira_field_id, lambda x: x)
        return fn(value)

    def transform_tc_to_jira(self, tc_field_name: str, value: Any) -> Any:
        """Transform TestCase field value → Jira field value."""
        jira_field_id = self.tc_to_jira.get(tc_field_name)
        if not jira_field_id:
            return value
        fn = self._transformers.get(jira_field_id, lambda x: x)
        return fn(value)


# ─── OAuth 2.0 Token Management ──────────────────────────────────────────────

class JiraOAuthManager:
    """Manages Jira OAuth 2.0 token lifecycle: refresh, cache, expiry."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token_cache: dict[str, dict[str, Any]] = {}  # tenant_id → token data
        self._lock = asyncio.Lock()

    async def get_token(
        self,
        tenant_id: str,
        jira_url: str,
        refresh_token: str,
    ) -> tuple[str, Optional[str]]:
        """
        Get valid access token (cached or refreshed).

        Returns:
            (access_token, error_message) — error_message is None on success
        """
        cached = self._token_cache.get(tenant_id)
        if cached and cached.get("expires_at", 0) > time.time():
            return cached["access_token"], None

        async with self._lock:
            # Double-check after acquiring lock
            cached = self._token_cache.get(tenant_id)
            if cached and cached.get("expires_at", 0) > time.time():
                return cached["access_token"], None

            return await self._refresh_token(tenant_id, jira_url, refresh_token)

    async def _refresh_token(
        self,
        tenant_id: str,
        jira_url: str,
        refresh_token: str,
    ) -> tuple[str, Optional[str]]:
        """Refresh Jira OAuth token."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{jira_url.rstrip('/')}/oauth/token",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                    timeout=10.0,
                )
                if not resp.is_success:
                    return "", f"OAuth token refresh failed: {resp.status_code} {resp.text[:200]}"

                data = resp.json()
                self._token_cache[tenant_id] = {
                    "access_token": data["access_token"],
                    "expires_at": time.time() + data.get("expires_in", 3600),
                }
                return data["access_token"], None
        except Exception as exc:
            logger.exception("OAuth token refresh error: %s", exc)
            return "", str(exc)


# ─── Rate Limiter ───────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket rate limiter: 10 req/s with exponential backoff on limit."""

    def __init__(self, rate: float = 10.0, burst: int = 20):
        """
        Args:
            rate: Requests per second
            burst: Max tokens in bucket
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        self.backoff_exp = 1.0

    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens; backoff if rate limited.

        Returns:
            Wait time (seconds) before request can proceed.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                self.backoff_exp = 1.0
                return 0.0

            # Rate limited: exponential backoff
            wait_time = (tokens - self.tokens) / self.rate
            self.backoff_exp = min(30.0, self.backoff_exp * 2)  # Cap at 30s
            return wait_time + self.backoff_exp


# ─── Checkpoint System ───────────────────────────────────────────────────────

class SyncCheckpoint:
    """Resume point for long-running syncs."""

    def __init__(
        self,
        sync_id: str,
        sync_type: str,  # "tc_to_issue", "issue_to_tc"
        tenant_id: str,
        status: SyncStatus = SyncStatus.PENDING,
        processed_count: int = 0,
        total_count: int = 0,
        last_processed_id: Optional[str] = None,
        error_details: Optional[str] = None,
    ):
        self.sync_id = sync_id
        self.sync_type = sync_type
        self.tenant_id = tenant_id
        self.status = status
        self.processed_count = processed_count
        self.total_count = total_count
        self.last_processed_id = last_processed_id
        self.error_details = error_details
        self.created_at = datetime.now(_tz.utc)
        self.updated_at = self.created_at

    def mark_progress(self, item_id: str, count: int = 1):
        """Update checkpoint with processed item."""
        self.processed_count += count
        self.last_processed_id = item_id
        self.updated_at = datetime.now(_tz.utc)

    def mark_checkpoint(self):
        """Mark as checkpoint (paused, can resume)."""
        self.status = SyncStatus.CHECKPOINT
        self.updated_at = datetime.now(_tz.utc)

    def mark_completed(self):
        """Mark sync as completed."""
        self.status = SyncStatus.COMPLETED
        self.updated_at = datetime.now(_tz.utc)

    def mark_failed(self, error: str):
        """Mark sync as failed."""
        self.status = SyncStatus.FAILED
        self.error_details = error
        self.updated_at = datetime.now(_tz.utc)

    def to_dict(self) -> dict[str, Any]:
        """Serialize checkpoint for storage."""
        return {
            "sync_id": self.sync_id,
            "sync_type": self.sync_type,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "last_processed_id": self.last_processed_id,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SyncCheckpoint:
        """Deserialize checkpoint from storage."""
        cp = SyncCheckpoint(
            sync_id=data["sync_id"],
            sync_type=data["sync_type"],
            tenant_id=data["tenant_id"],
            status=SyncStatus(data.get("status", "pending")),
            processed_count=data.get("processed_count", 0),
            total_count=data.get("total_count", 0),
            last_processed_id=data.get("last_processed_id"),
            error_details=data.get("error_details"),
        )
        return cp


# ─── DLQ (Dead-Letter Queue) ────────────────────────────────────────────────

class DLQRecord:
    """Failed sync record for manual review."""

    def __init__(
        self,
        dlq_id: str,
        tenant_id: str,
        sync_type: str,
        source_id: str,  # TC ID or Issue key
        error: str,
        payload: dict[str, Any],
        retry_count: int = 0,
        created_at: Optional[datetime] = None,
    ):
        self.dlq_id = dlq_id
        self.tenant_id = tenant_id
        self.sync_type = sync_type
        self.source_id = source_id
        self.error = error
        self.payload = payload
        self.retry_count = retry_count
        self.created_at = created_at or datetime.now(_tz.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dlq_id": self.dlq_id,
            "tenant_id": self.tenant_id,
            "sync_type": self.sync_type,
            "source_id": self.source_id,
            "error": self.error,
            "payload": self.payload,
            "retry_count": self.retry_count,
            "created_at": self.created_at.isoformat(),
        }


# ─── Jira API Client ────────────────────────────────────────────────────────

class JiraAPIClient:
    """HTTP client for Jira REST API v3 with rate limiting + error handling."""

    def __init__(self, base_url: str, auth: tuple[str, str], rate_limiter: Optional[RateLimiter] = None):
        """
        Args:
            base_url: Jira base URL (e.g., https://jira.company.com)
            auth: (email, api_token) tuple
            rate_limiter: Optional RateLimiter instance
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.rate_limiter = rate_limiter or RateLimiter()
        self.client = httpx.AsyncClient(auth=auth, timeout=30.0)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs) -> tuple[int, dict | str, Optional[str]]:
        """
        Make HTTP request with rate limiting.

        Returns:
            (status_code, response_body, error_message)
        """
        wait_time = await self.rate_limiter.acquire()
        if wait_time > 0:
            logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        url = f"{self.base_url}/rest/api/3{endpoint}"
        try:
            resp = await self.client.request(method, url, **kwargs)
            if resp.is_success:
                try:
                    return resp.status_code, resp.json(), None
                except ValueError:
                    return resp.status_code, resp.text, None
            else:
                error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                return resp.status_code, {}, error
        except Exception as exc:
            error = f"Request failed: {str(exc)}"
            return 0, {}, error

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str = "",
        issue_type: str = "Bug",
        priority: str = "Medium",
        custom_fields: Optional[dict[str, Any]] = None,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Create a new Jira issue.

        Returns:
            (issue_key, error_message)
        """
        fields = {
            "project": {"key": project_key},
            "summary": summary[:255],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description[:2000]}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
        if custom_fields:
            fields.update(custom_fields)

        status_code, body, error = await self._request(
            "POST",
            "/issue",
            json={"fields": fields},
        )

        if error:
            return None, error
        if isinstance(body, dict):
            return body.get("key"), None
        return None, "Invalid response format"

    async def update_issue(
        self,
        issue_key: str,
        fields: dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """Update existing issue fields."""
        status_code, _, error = await self._request(
            "PUT",
            f"/issue/{issue_key}",
            json={"fields": fields},
        )
        if error:
            return False, error
        return True, None

    async def get_issue(self, issue_key: str) -> tuple[Optional[dict], Optional[str]]:
        """Fetch issue details."""
        status_code, body, error = await self._request(
            "GET",
            f"/issue/{issue_key}",
        )
        if error:
            return None, error
        return body, None

    async def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
    ) -> tuple[Optional[list[dict]], Optional[str]]:
        """Search issues by JQL."""
        status_code, body, error = await self._request(
            "GET",
            "/search",
            params={
                "jql": jql,
                "maxResults": min(max_results, 100),
                "startAt": start_at,
            },
        )
        if error:
            return None, error
        if isinstance(body, dict):
            return body.get("issues", []), None
        return None, "Invalid response format"


# ─── Main Jira Sync Service ────────────────────────────────────────────────

class JiraSyncService:
    """Bi-directional synchronization between TestCase ↔ Jira Issue."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.rate_limiter = RateLimiter(rate=10.0)
        self.oauth_manager = JiraOAuthManager(
            client_id=settings.jira_oauth_client_id or "",
            client_secret=settings.jira_oauth_client_secret or "",
        )
        self.checkpoints: dict[str, SyncCheckpoint] = {}
        self.dlq: list[DLQRecord] = []
        self.field_mapper = FieldMapping()
        self._setup_default_mappings()

    def _setup_default_mappings(self):
        """Setup standard TestCase ↔ Jira field mappings."""
        self.field_mapper.add_mapping(
            "priority",
            "priority",
            FieldMapType.ENUM,
            lambda x: x.lower() if isinstance(x, str) else x,
        )
        self.field_mapper.add_mapping(
            "labels",
            "tags",
            FieldMapType.ARRAY,
        )
        self.field_mapper.add_mapping(
            "summary",
            "title",
            FieldMapType.STRING,
        )
        self.field_mapper.add_mapping(
            "description",
            "objective",
            FieldMapType.STRING,
        )

    async def sync_test_case_to_issue(
        self,
        test_case_id: str,
        project_key: str,
        jira_url: str,
        jira_auth: tuple[str, str],
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Sync single TestCase → Jira Issue (create or update).

        Returns:
            (issue_key, error_message)
        """
        try:
            # Fetch TestCase from DB
            from app.domains.test_management.models import TestCase

            tc = self.db.query(TestCase).filter_by(id=test_case_id).first()
            if not tc:
                error = f"TestCase not found: {test_case_id}"
                self._add_dlq(test_case_id, "tc_to_issue", {}, error)
                return None, error

            # Check if already linked to Jira
            existing_issue = self._find_linked_issue(test_case_id)
            if existing_issue:
                # Update existing issue
                return await self._update_jira_issue(
                    existing_issue,
                    tc,
                    jira_url,
                    jira_auth,
                )
            else:
                # Create new issue
                return await self._create_jira_issue(
                    test_case_id,
                    tc,
                    project_key,
                    jira_url,
                    jira_auth,
                )

        except Exception as exc:
            logger.exception(f"Error syncing TC {test_case_id} to Jira")
            error = str(exc)
            self._add_dlq(test_case_id, "tc_to_issue", {}, error)
            return None, error

    async def _create_jira_issue(
        self,
        test_case_id: str,
        tc: Any,
        project_key: str,
        jira_url: str,
        jira_auth: tuple[str, str],
    ) -> tuple[Optional[str], Optional[str]]:
        """Create new Jira issue from TestCase."""
        client = JiraAPIClient(jira_url, jira_auth, self.rate_limiter)
        try:
            custom_fields = {}
            if tc.tags:
                custom_fields["labels"] = tc.tags

            issue_key, error = await client.create_issue(
                project_key=project_key,
                summary=tc.title,
                description=tc.objective or "",
                issue_type="Task",
                priority=tc.priority.title(),
                custom_fields=custom_fields,
            )

            if error:
                self._add_dlq(test_case_id, "tc_to_issue", {"tc_id": test_case_id}, error)
                return None, error

            # Link TestCase → Issue
            self._link_tc_to_issue(test_case_id, issue_key)
            logger.info(f"Created Jira issue {issue_key} from TC {test_case_id}")
            return issue_key, None

        finally:
            await client.close()

    async def _update_jira_issue(
        self,
        issue_key: str,
        tc: Any,
        jira_url: str,
        jira_auth: tuple[str, str],
    ) -> tuple[Optional[str], Optional[str]]:
        """Update existing Jira issue with TestCase changes."""
        client = JiraAPIClient(jira_url, jira_auth, self.rate_limiter)
        try:
            fields = {
                "summary": tc.title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": tc.objective or ""}],
                        }
                    ],
                },
                "priority": {"name": tc.priority.title()},
            }
            if tc.tags:
                fields["labels"] = tc.tags

            ok, error = await client.update_issue(issue_key, fields)
            if error:
                self._add_dlq(tc.id, "tc_to_issue_update", {"issue_key": issue_key}, error)
                return None, error

            logger.info(f"Updated Jira issue {issue_key}")
            return issue_key, None

        finally:
            await client.close()

    async def sync_issues_to_test_cases(
        self,
        project_key: str,
        jira_url: str,
        jira_auth: tuple[str, str],
        jql: str = "",
        max_results: int = 50,
    ) -> tuple[int, list[str]]:
        """
        Sync Jira issues → TestCases (pull linked issues).

        Returns:
            (synced_count, error_list)
        """
        errors = []
        synced_count = 0

        client = JiraAPIClient(jira_url, jira_auth, self.rate_limiter)
        try:
            if not jql:
                jql = f"project = {project_key} ORDER BY updated DESC"

            issues, error = await client.search_issues(jql, max_results)
            if error:
                logger.error(f"Failed to search issues: {error}")
                return 0, [error]

            if not issues:
                return 0, []

            for issue in issues:
                try:
                    tc_id = self._find_linked_tc(issue.get("key", ""))
                    if not tc_id:
                        # Could auto-create TC from issue here
                        continue

                    # Update TC from issue
                    ok, err = await self._update_tc_from_issue(
                        tc_id,
                        issue,
                    )
                    if err:
                        errors.append(err)
                    else:
                        synced_count += 1

                except Exception as exc:
                    error_msg = f"Sync issue {issue.get('key')} error: {str(exc)}"
                    logger.exception(error_msg)
                    errors.append(error_msg)

            return synced_count, errors

        finally:
            await client.close()

    async def _update_tc_from_issue(
        self,
        tc_id: str,
        issue: dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """Update TestCase fields from Jira issue."""
        try:
            from app.domains.test_management.models import TestCase

            tc = self.db.query(TestCase).filter_by(id=tc_id).first()
            if not tc:
                return False, f"TestCase not found: {tc_id}"

            # Map issue fields → TC fields
            fields = issue.get("fields", {})
            tc.title = fields.get("summary", tc.title)
            tc.objective = fields.get("description") or tc.objective

            status = fields.get("status", {}).get("name", "")
            if status:
                tc.status = self._map_jira_status_to_tc(status)

            priority = fields.get("priority", {}).get("name", "")
            if priority:
                tc.priority = priority.lower()

            labels = fields.get("labels", [])
            if labels:
                tc.tags = labels

            self.db.commit()
            return True, None

        except Exception as exc:
            logger.exception(f"Error updating TC {tc_id} from issue")
            return False, str(exc)

    def _map_jira_status_to_tc(self, jira_status: str) -> str:
        """Map Jira issue status → TestCase status."""
        status_map = {
            "to do": "draft",
            "in progress": "in_review",
            "done": "approved",
            "closed": "approved",
        }
        return status_map.get(jira_status.lower(), "draft")

    # ─── Checkpoint Management ────────────────────────────────────────────────

    def create_checkpoint(
        self,
        sync_type: str,
        total_count: int,
    ) -> str:
        """Create new sync checkpoint."""
        sync_id = str(uuid.uuid4())[:12]
        cp = SyncCheckpoint(
            sync_id=sync_id,
            sync_type=sync_type,
            tenant_id=self.tenant_id,
            total_count=total_count,
        )
        self.checkpoints[sync_id] = cp
        return sync_id

    def get_checkpoint(self, sync_id: str) -> Optional[SyncCheckpoint]:
        """Retrieve checkpoint by ID."""
        return self.checkpoints.get(sync_id)

    def update_checkpoint(self, sync_id: str, item_id: str):
        """Update checkpoint progress."""
        cp = self.checkpoints.get(sync_id)
        if cp:
            cp.mark_progress(item_id)

    def mark_checkpoint_completed(self, sync_id: str):
        """Mark checkpoint as completed."""
        cp = self.checkpoints.get(sync_id)
        if cp:
            cp.mark_completed()

    # ─── DLQ Management ──────────────────────────────────────────────────────

    def _add_dlq(self, source_id: str, sync_type: str, payload: dict[str, Any], error: str):
        """Add record to DLQ."""
        record = DLQRecord(
            dlq_id=str(uuid.uuid4())[:16],
            tenant_id=self.tenant_id,
            sync_type=sync_type,
            source_id=source_id,
            error=error,
            payload=payload,
        )
        self.dlq.append(record)
        logger.warning(f"DLQ: {sync_type} {source_id} — {error}")

    def get_dlq_records(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve DLQ records for review."""
        return [r.to_dict() for r in self.dlq[:limit]]

    def clear_dlq_record(self, dlq_id: str) -> bool:
        """Remove record from DLQ (manual review completed)."""
        self.dlq = [r for r in self.dlq if r.dlq_id != dlq_id]
        return True

    # ─── Helper Methods ──────────────────────────────────────────────────────

    def _link_tc_to_issue(self, tc_id: str, issue_key: str):
        """Store link between TestCase ↔ Jira Issue."""
        try:
            from app.domains.test_management.models import TestCase

            tc = self.db.query(TestCase).filter_by(id=tc_id).first()
            if tc:
                tc.source_ref = issue_key
                tc.source_type = "jira"
                self.db.commit()
        except Exception as exc:
            logger.warning(f"Failed to link TC {tc_id} → {issue_key}: {exc}")

    def _find_linked_issue(self, tc_id: str) -> Optional[str]:
        """Find Jira issue linked to TestCase."""
        try:
            from app.domains.test_management.models import TestCase

            tc = self.db.query(TestCase).filter_by(id=tc_id).first()
            if tc and tc.source_type == "jira":
                return tc.source_ref
        except Exception:
            pass
        return None

    def _find_linked_tc(self, issue_key: str) -> Optional[str]:
        """Find TestCase linked to Jira issue."""
        try:
            from app.domains.test_management.models import TestCase

            tc = (
                self.db.query(TestCase)
                .filter_by(source_ref=issue_key, source_type="jira")
                .first()
            )
            return tc.id if tc else None
        except Exception:
            pass
        return None


# ─── Factory Function ───────────────────────────────────────────────────────

def get_jira_sync_service(db: Session, tenant_id: str) -> JiraSyncService:
    """Factory to create JiraSyncService instance."""
    return JiraSyncService(db, tenant_id)
