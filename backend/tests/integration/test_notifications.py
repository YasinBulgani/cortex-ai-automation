"""Notification preferences and websocket integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domains.notifications.service import manager


class TestNotifications:
    PREFIX = "/api/v1/notifications/prefs"
    WS_PATH = "/api/v1/ws/notifications"

    def test_requires_auth(self, client: TestClient) -> None:
        get_resp = client.get(self.PREFIX)
        put_resp = client.put(self.PREFIX, json={"notify_on_complete": False})
        assert get_resp.status_code == 401
        assert put_resp.status_code == 401

    def test_list_notification_prefs(self, client: TestClient, auth_headers: dict[str, str], db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        r = client.get(self.PREFIX, headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "notify_on_complete" in body
        assert "notify_on_failure" in body
        assert "slack_webhook_url" in body

    def test_update_notification_prefs(self, client: TestClient, auth_headers: dict[str, str], db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        update = client.put(
            self.PREFIX,
            json={
                "notify_on_complete": False,
                "notify_on_failure": True,
                "slack_webhook_url": "https://hooks.slack.com/services/T123/B456/testtoken",
            },
            headers=auth_headers,
        )
        assert update.status_code == 200
        assert update.json()["notify_on_complete"] is False

        read_back = client.get(self.PREFIX, headers=auth_headers)
        assert read_back.status_code == 200
        assert read_back.json()["slack_webhook_url"] is not None

    def test_websocket_connection(self, client: TestClient, admin_token: str, db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        user_count_before = sum(len(v) for v in manager.active_connections.values())
        with client.websocket_connect(f"{self.WS_PATH}?token={admin_token}") as websocket:
            websocket.send_text("ping")
            user_count_during = sum(len(v) for v in manager.active_connections.values())
            assert user_count_during >= user_count_before + 1

        user_count_after = sum(len(v) for v in manager.active_connections.values())
        assert user_count_after == user_count_before
