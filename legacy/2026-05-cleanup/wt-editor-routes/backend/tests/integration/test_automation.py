"""Automation engine proxy integration tests."""

from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from app.domains.automation import router as automation_router


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json={"status": "ok", "engine_url": url})

    async def request(self, method, url, headers=None, params=None, content=None):
        request = httpx.Request(method, url)
        body = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else ""
        return httpx.Response(
            200,
            request=request,
            json={
                "method": method,
                "url": url,
                "params": dict(params or {}),
                "body": body,
                "headers": dict(headers or {}),
            },
            headers={"content-type": "application/json"},
        )


class TestAutomation:
    PREFIX = "/api/v1/automation"

    def test_health_endpoint_is_public(self, client: TestClient) -> None:
        r = client.get(f"{self.PREFIX}/health")
        assert r.status_code == 200
        assert "status" in r.json()

    def test_health_endpoint_with_mocked_engine(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.get(f"{self.PREFIX}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_proxy_requires_auth(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.get(f"{self.PREFIX}/proxy/api/features?limit=5")
        assert r.status_code == 401

    def test_proxy_get(self, client: TestClient, auth_headers: dict[str, str], monkeypatch) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.get(f"{self.PREFIX}/proxy/api/features?limit=5", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["method"] == "GET"
        assert body["params"]["limit"] == "5"
        assert "authorization" not in body["headers"]

    def test_proxy_post(self, client: TestClient, auth_headers: dict[str, str], monkeypatch) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.post(
            f"{self.PREFIX}/proxy/api/run",
            json={"run_id": "run-1", "browser": "chromium"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["method"] == "POST"
        assert '"run_id":"run-1"' in body["body"].replace(" ", "")

    def test_proxy_rejects_non_allowlisted_path(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.get(f"{self.PREFIX}/proxy/api/editor/run-command", headers=auth_headers)
        assert r.status_code == 403

    def test_proxy_rejects_path_traversal(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.get(f"{self.PREFIX}/proxy/api/../features", headers=auth_headers)
        assert r.status_code == 403

    def test_proxy_overrides_user_supplied_internal_key(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(automation_router.httpx, "AsyncClient", _FakeAsyncClient)
        headers = {
            **auth_headers,
            "X-Internal-Key": "attacker-controlled",
        }
        r = client.get(f"{self.PREFIX}/proxy/api/features", headers=headers)
        assert r.status_code == 200
        forwarded = r.json()["headers"]
        assert forwarded["x-internal-key"] == automation_router._INTERNAL_KEY
