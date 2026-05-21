"""Unit tests for CI/CD event persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domains.cicd import router


class _FakeMappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _FakeSession:
    def __init__(self, rows=None, total=0):
        self.rows = rows or []
        self.total = total
        self.committed = False
        self.rolled_back = False
        self.calls = []

    def execute(self, statement, params):
        sql = str(statement)
        self.calls.append((sql, params))
        if "COUNT(*)" in sql:
            return _FakeScalarResult(self.total)
        return _FakeMappingsResult(self.rows)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_store_event_persists_audit_fields_and_preserves_shape():
    db = _FakeSession()
    payload = {
        "ref": "refs/heads/main",
        "after": "abc123",
        "repository": {"full_name": "bgts/repo"},
        "sender": {"login": "octocat"},
        "action": "completed",
    }

    event = router._store_event(
        db,
        source="github",
        event_type="workflow_run",
        payload=payload,
        project_ref="bgts/repo",
    )

    assert db.committed is True
    sql, params = db.calls[0]
    assert "INSERT INTO cicd_webhook_events" in sql
    assert params["source"] == "github"
    assert params["branch"] == "main"
    assert params["commit_sha"] == "abc123"
    assert params["author"] == "octocat"
    assert params["repo_name"] == "bgts/repo"
    assert event["source"] == "github"
    assert event["event_type"] == "workflow_run"
    assert event["project_ref"] == "bgts/repo"
    assert isinstance(event["payload_summary"], dict)
    assert len(event["id"]) == 12


def test_list_events_returns_legacy_response_shape():
    db = _FakeSession(
        rows=[
            {
                "id": "evt123456789",
                "source": "gitlab",
                "event_type": "pipeline",
                "project_ref": "group/project",
                "received_at": datetime(2026, 4, 16, 12, 30, tzinfo=timezone.utc),
                "payload_summary": '{"ref": "main", "status": "success"}',
            }
        ],
        total=1,
    )

    result = router._list_events(db, source="gitlab", limit=25)

    assert result["total"] == 1
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["id"] == "evt123456789"
    assert event["source"] == "gitlab"
    assert event["project_ref"] == "group/project"
    assert event["payload_summary"] == {"ref": "main", "status": "success"}
    assert event["received_at"].startswith("2026-04-16T12:30:00")
