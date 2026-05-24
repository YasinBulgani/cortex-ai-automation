"""Unit tests for audit log export endpoints (SOC 2 / DPA evidence).

Tests the new /audit/export/json, /audit/export/csv, and /audit/export/summary
endpoints added to app/domains/audit/router.py.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ── Schema tests ───────────────────────────────────────────────────────────────


class TestAuditEventOutSchema:
    def test_minimal_construction(self) -> None:
        from app.domains.audit.router import AuditEventOut

        ev = AuditEventOut(
            id="abc123",
            ts="2026-01-01T00:00:00+00:00",
            action="user.login",
            resource_type="user",
        )
        assert ev.id == "abc123"
        assert ev.action == "user.login"
        assert ev.actor_email is None
        assert ev.ip is None
        assert ev.seq is None

    def test_full_construction(self) -> None:
        from app.domains.audit.router import AuditEventOut

        ev = AuditEventOut(
            id="def456",
            ts="2026-06-01T12:00:00+00:00",
            actor_email="admin@example.com",
            actor_name="Admin User",
            action="mfa.enabled",
            resource_type="user",
            resource_id="user-001",
            ip="10.0.0.1",
            tenant_id="tenant-1",
            seq=42,
            prev_hash="aabbcc",
            hash="ddeeff",
        )
        assert ev.actor_name == "Admin User"
        assert ev.seq == 42
        assert ev.hash == "ddeeff"


class TestAuditExportSummarySchema:
    def test_construction(self) -> None:
        from app.domains.audit.router import AuditExportSummary

        s = AuditExportSummary(
            exported_at="2026-01-01T00:00:00+00:00",
            total_events=150,
            date_from="2026-01-01Z",
            date_to="2026-01-31Z",
            format="summary",
        )
        assert s.total_events == 150
        assert s.format == "summary"

    def test_optional_dates(self) -> None:
        from app.domains.audit.router import AuditExportSummary

        s = AuditExportSummary(
            exported_at="2026-01-01T00:00:00+00:00",
            total_events=0,
            format="summary",
        )
        assert s.date_from is None
        assert s.date_to is None


# ── _require_admin helper ──────────────────────────────────────────────────────


class TestRequireAdmin:
    def test_admin_passes(self) -> None:
        from fastapi import HTTPException
        from app.domains.audit.router import _require_admin

        mock_user = MagicMock()
        with patch("app.domains.audit.router._user_permissions", return_value={"admin.*"}):
            # Should not raise
            _require_admin(mock_user)

    def test_non_admin_raises_403(self) -> None:
        from fastapi import HTTPException
        from app.domains.audit.router import _require_admin

        mock_user = MagicMock()
        with patch("app.domains.audit.router._user_permissions", return_value={"test.read"}):
            with pytest.raises(HTTPException) as exc_info:
                _require_admin(mock_user)
        assert exc_info.value.status_code == 403


# ── _build_query date parsing ─────────────────────────────────────────────────


class TestBuildQueryDateParsing:
    def test_valid_date_from(self) -> None:
        from fastapi import HTTPException
        from app.domains.audit.router import _build_query

        mock_db = MagicMock()
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        # Should not raise for valid ISO date
        stmt = _build_query(mock_db, date_from="2026-01-01T00:00:00Z")
        assert stmt is not None

    def test_valid_date_to(self) -> None:
        from app.domains.audit.router import _build_query

        mock_db = MagicMock()
        stmt = _build_query(mock_db, date_to="2026-12-31T23:59:59Z")
        assert stmt is not None

    def test_invalid_date_from_raises_400(self) -> None:
        from fastapi import HTTPException
        from app.domains.audit.router import _build_query

        mock_db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _build_query(mock_db, date_from="not-a-date")
        assert exc_info.value.status_code == 400

    def test_invalid_date_to_raises_400(self) -> None:
        from fastapi import HTTPException
        from app.domains.audit.router import _build_query

        mock_db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            _build_query(mock_db, date_to="bad-date-format")
        assert exc_info.value.status_code == 400

    def test_no_filters_returns_stmt(self) -> None:
        from app.domains.audit.router import _build_query

        mock_db = MagicMock()
        stmt = _build_query(mock_db)
        assert stmt is not None


# ── _enrich helper ────────────────────────────────────────────────────────────


class TestEnrichHelper:
    def _make_event(self, **kwargs):
        e = MagicMock()
        e.id = kwargs.get("id", "evt-1")
        e.ts = kwargs.get("ts", datetime(2026, 1, 1, tzinfo=timezone.utc))
        e.actor_user_id = kwargs.get("actor_user_id", None)
        e.action = kwargs.get("action", "user.login")
        e.resource_type = kwargs.get("resource_type", "user")
        e.resource_id = kwargs.get("resource_id", None)
        e.payload = kwargs.get("payload", None)
        e.ip = kwargs.get("ip", None)
        e.tenant_id = kwargs.get("tenant_id", None)
        e.seq = kwargs.get("seq", None)
        e.prev_hash = kwargs.get("prev_hash", None)
        e.hash = kwargs.get("hash", None)
        return e

    def test_no_actor(self) -> None:
        from app.domains.audit.router import _enrich

        mock_db = MagicMock()
        events = [self._make_event()]
        result = _enrich(mock_db, events)
        assert len(result) == 1
        assert result[0].actor_email is None

    def test_with_actor(self) -> None:
        from app.domains.audit.router import _enrich

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "alice@example.com"
        mock_user.full_name = "Alice"
        mock_db.get.return_value = mock_user

        events = [self._make_event(actor_user_id="user-001")]
        result = _enrich(mock_db, events)
        assert result[0].actor_email == "alice@example.com"
        assert result[0].actor_name == "Alice"

    def test_actor_not_found_in_db(self) -> None:
        from app.domains.audit.router import _enrich

        mock_db = MagicMock()
        mock_db.get.return_value = None  # User deleted

        events = [self._make_event(actor_user_id="deleted-user-id")]
        result = _enrich(mock_db, events)
        assert result[0].actor_email is None

    def test_ts_isoformat_used(self) -> None:
        from app.domains.audit.router import _enrich

        mock_db = MagicMock()
        ts = datetime(2026, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        events = [self._make_event(ts=ts)]
        result = _enrich(mock_db, events)
        assert "2026-06-15" in result[0].ts

    def test_empty_events_returns_empty(self) -> None:
        from app.domains.audit.router import _enrich

        mock_db = MagicMock()
        result = _enrich(mock_db, [])
        assert result == []

    def test_multiple_events_same_actor_batched(self) -> None:
        """Actor lookup should be done once per unique actor_user_id."""
        from app.domains.audit.router import _enrich

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "bob@example.com"
        mock_user.full_name = "Bob"
        mock_db.get.return_value = mock_user

        events = [
            self._make_event(id=f"evt-{i}", actor_user_id="user-bob")
            for i in range(5)
        ]
        result = _enrich(mock_db, events)
        assert all(r.actor_email == "bob@example.com" for r in result)
        # db.get should be called once (batched by unique actor_id)
        assert mock_db.get.call_count == 1


# ── Audit router endpoint surface ─────────────────────────────────────────────


class TestAuditRouterEndpointSurface:
    def test_expected_routes_registered(self) -> None:
        from app.domains.audit.router import router

        paths = {route.path for route in router.routes}
        assert "/audit/events" in paths
        assert "/audit/export/json" in paths
        assert "/audit/export/csv" in paths
        assert "/audit/export/summary" in paths

    def test_events_route_is_get(self) -> None:
        from app.domains.audit.router import router

        for route in router.routes:
            if route.path == "/audit/events":
                assert "GET" in route.methods
                break

    def test_export_routes_are_get(self) -> None:
        from app.domains.audit.router import router

        export_paths = {"/audit/export/json", "/audit/export/csv", "/audit/export/summary"}
        for route in router.routes:
            if route.path in export_paths:
                assert "GET" in route.methods
