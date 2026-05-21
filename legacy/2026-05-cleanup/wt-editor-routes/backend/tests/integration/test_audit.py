"""Audit trail integration tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.infra.database import SessionLocal
from app.infra.models import AuditEvent


def _seed_audit_event(*, actor_user_id: str | None, action: str, resource_type: str, resource_id: str) -> str:
    with SessionLocal() as db:
        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload={"resource_id": resource_id},
            ts=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.id


class TestAudit:
    PREFIX = "/api/v1/audit/events"

    def test_requires_auth(self, client: TestClient) -> None:
        r = client.get(self.PREFIX)
        assert r.status_code == 401

    def test_list_audit_logs(self, client: TestClient, auth_headers: dict[str, str], db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        me = client.get("/api/v1/auth/me", headers=auth_headers)
        actor_id = me.json()["id"]
        event_id = _seed_audit_event(
            actor_user_id=actor_id,
            action="project.create",
            resource_type="project",
            resource_id="audit-project-1",
        )

        r = client.get(self.PREFIX, headers=auth_headers)
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()]
        assert event_id in ids

    def test_audit_log_filter(self, client: TestClient, auth_headers: dict[str, str], db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        me = client.get("/api/v1/auth/me", headers=auth_headers)
        actor_id = me.json()["id"]
        _seed_audit_event(actor_user_id=actor_id, action="project.update", resource_type="project", resource_id="p-1")
        _seed_audit_event(actor_user_id=actor_id, action="scenario.delete", resource_type="scenario", resource_id="s-1")

        r = client.get(
            f"{self.PREFIX}?action=project&resource_type=project",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()
        assert all("project" in item["action"] for item in r.json())
        assert all(item["resource_type"] == "project" for item in r.json())

    def test_audit_log_pagination(self, client: TestClient, auth_headers: dict[str, str], db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        me = client.get("/api/v1/auth/me", headers=auth_headers)
        actor_id = me.json()["id"]
        for idx in range(3):
            _seed_audit_event(
                actor_user_id=actor_id,
                action=f"pagination.test.{idx}",
                resource_type="project",
                resource_id=f"pag-{idx}",
            )

        first = client.get(f"{self.PREFIX}?page=1&per_page=1", headers=auth_headers)
        second = client.get(f"{self.PREFIX}?page=2&per_page=1", headers=auth_headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert len(first.json()) == 1
        assert len(second.json()) == 1
        assert first.json()[0]["id"] != second.json()[0]["id"]

    def test_audit_requires_admin_role(
        self,
        client: TestClient,
        operator_headers: dict[str, str],
        db_ready: bool,
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        r = client.get(self.PREFIX, headers=operator_headers)
        assert r.status_code == 403
