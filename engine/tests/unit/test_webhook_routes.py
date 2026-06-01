"""
tests/unit/test_webhook_routes.py
===================================
webhook_bp (/api/webhooks/*) için birim testler.

Endpoints:
  POST /api/webhooks/github    — GitHub PR & push event handler
  POST /api/webhooks/gitlab    — GitLab MR & push event handler
  POST /api/webhooks/generic   — Generic CI webhook
  GET  /api/webhooks/events    — Son webhook event'leri
  GET  /api/webhooks/config    — Webhook config görüntüle
  PUT  /api/webhooks/config    — Webhook config güncelle

Dış bağımlılıklar (dosya G/Ç, threading, HTTP) stub'lanır.
HMAC imza doğrulaması test ortamında (APP_ENV=development, secret boş)
atlanır; production modunu test eden testler env var ile kontrol edilir.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import sys
import threading
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def webhook_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — dosya I/O ve thread stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-webhook-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-webhook-internal")

    # core.db stubs
    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    # Dosya sistemi stub'ları — webhook_routes._EVENTS_FILE / _CONFIG_FILE
    import routes.webhook_routes as wr
    monkeypatch.setattr(wr, "_EVENTS_FILE", tmp_path / "webhook_events.json", raising=True)
    monkeypatch.setattr(wr, "_CONFIG_FILE", tmp_path / "webhook_config.json", raising=True)

    # threading stub — test sırasında arka plan thread'leri başlatma
    monkeypatch.setattr(threading.Thread, "start", lambda self, *a, **kw: None)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


def _github_sig(payload: bytes, secret: str) -> str:
    """GitHub tarzı HMAC-SHA256 imzası üretir."""
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# ── /api/webhooks/github ─────────────────────────────────────────────────────

class TestGithubWebhook:
    """POST /api/webhooks/github testleri."""

    def test_github_ping_event_returns_200(self, webhook_client):
        """ping event'i kabul edilmeli (status=skipped)."""
        resp = webhook_client.post(
            "/api/webhooks/github",
            data=json.dumps({"zen": "Keep it logically awesome."}),
            content_type="application/json",
            headers={"X-GitHub-Event": "ping"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True

    def test_github_push_event_auto_run_off_returns_skipped(self, webhook_client):
        """push event'inde auto_run_on_push=False (default) → status=skipped."""
        payload = json.dumps({"commits": [{"added": ["src/test.py"], "modified": []}]}).encode()
        resp = webhook_client.post(
            "/api/webhooks/github",
            data=payload,
            content_type="application/json",
            headers={"X-GitHub-Event": "push"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
        assert data.get("status") == "skipped"

    def test_github_pr_open_event_returns_queued(self, webhook_client):
        """PR opened event'i queued dönmeli (auto_run_on_pr default=True)."""
        payload = json.dumps({
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "Add new feature",
                "url": "https://api.github.com/repos/org/repo/pulls/42",
                "head": {"ref": "feature/my-branch"},
            },
            "repository": {"full_name": "org/repo"},
            "files": [],
        }).encode()

        resp = webhook_client.post(
            "/api/webhooks/github",
            data=payload,
            content_type="application/json",
            headers={"X-GitHub-Event": "pull_request"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
        assert data.get("status") == "queued"

    def test_github_invalid_signature_in_production_returns_401(self, webhook_client, monkeypatch):
        """Üretim ortamında geçersiz imza 401 dönmeli."""
        monkeypatch.setenv("APP_ENV", "production")
        import routes.webhook_routes as wr
        # Gerçek secret ayarlı config simüle et
        monkeypatch.setattr(
            wr,
            "_load_config",
            lambda: {
                **wr._DEFAULT_CONFIG,
                "github_secret": "real-secret-key",
                "auto_run_on_pr": True,
                "auto_run_on_push": False,
            },
        )

        payload = b'{"action": "opened"}'
        resp = webhook_client.post(
            "/api/webhooks/github",
            data=payload,
            content_type="application/json",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": "sha256=invalidsignature",
            },
        )
        assert resp.status_code == 401

    def test_github_valid_hmac_signature_accepted(self, webhook_client, monkeypatch):
        """Doğru HMAC imzası ile istek kabul edilmeli."""
        secret = "my-webhook-secret-123"
        import routes.webhook_routes as wr
        monkeypatch.setattr(
            wr,
            "_load_config",
            lambda: {
                **wr._DEFAULT_CONFIG,
                "github_secret": secret,
                "auto_run_on_pr": True,
                "auto_run_on_push": False,
            },
        )

        payload = json.dumps({"action": "synchronize", "repository": {"full_name": "org/repo"}}).encode()
        sig = _github_sig(payload, secret)

        resp = webhook_client.post(
            "/api/webhooks/github",
            data=payload,
            content_type="application/json",
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True

    def test_github_event_id_in_response(self, webhook_client):
        """Her webhook yanıtı event_id içermeli."""
        resp = webhook_client.post(
            "/api/webhooks/github",
            data=json.dumps({}),
            content_type="application/json",
            headers={"X-GitHub-Event": "issues"},
        )
        data = resp.get_json()
        assert "event_id" in data


# ── /api/webhooks/gitlab ─────────────────────────────────────────────────────

class TestGitlabWebhook:
    """POST /api/webhooks/gitlab testleri."""

    def test_gitlab_push_hook_returns_200(self, webhook_client):
        """GitLab push event'i kabul edilmeli."""
        payload = json.dumps({
            "object_kind": "push",
            "commits": [],
            "project": {"path_with_namespace": "group/project"},
        })
        resp = webhook_client.post(
            "/api/webhooks/gitlab",
            data=payload,
            content_type="application/json",
            headers={"X-Gitlab-Event": "Push Hook"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True

    def test_gitlab_mr_open_event_returns_queued(self, webhook_client):
        """GitLab MR açılma eventi queued dönmeli (auto_run_on_pr default=True)."""
        payload = json.dumps({
            "object_kind": "merge_request",
            "object_attributes": {
                "action": "open",
                "title": "MR başlığı",
                "source_branch": "feature/x",
            },
            "project": {"path_with_namespace": "group/project"},
        })
        resp = webhook_client.post(
            "/api/webhooks/gitlab",
            data=payload,
            content_type="application/json",
            headers={"X-Gitlab-Event": "Merge Request Hook"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("status") == "queued"

    def test_gitlab_invalid_token_in_production_returns_401(self, webhook_client, monkeypatch):
        """Üretim ortamında geçersiz GitLab token 401 dönmeli."""
        monkeypatch.setenv("GITLAB_WEBHOOK_TOKEN", "expected-token")
        monkeypatch.setenv("APP_ENV", "production")

        resp = webhook_client.post(
            "/api/webhooks/gitlab",
            data=json.dumps({}),
            content_type="application/json",
            headers={"X-Gitlab-Token": "wrong-token"},
        )
        assert resp.status_code == 401


# ── /api/webhooks/generic ────────────────────────────────────────────────────

class TestGenericWebhook:
    """POST /api/webhooks/generic testleri."""

    def test_generic_webhook_returns_queued(self, webhook_client):
        """Generic webhook isteği queued dönmeli."""
        resp = webhook_client.post(
            "/api/webhooks/generic",
            json={"markers": "smoke", "browser": "chromium"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
        assert data.get("status") == "queued"

    def test_generic_webhook_invalid_token_returns_401(self, webhook_client, monkeypatch):
        """Geçersiz generic token 401 dönmeli."""
        monkeypatch.setenv("GENERIC_WEBHOOK_TOKEN", "valid-token")
        monkeypatch.setenv("APP_ENV", "production")

        resp = webhook_client.post(
            "/api/webhooks/generic",
            json={},
            content_type="application/json",
            headers={"X-Webhook-Token": "wrong-token"},
        )
        assert resp.status_code == 401


# ── /api/webhooks/events ─────────────────────────────────────────────────────

class TestWebhookEvents:
    """GET /api/webhooks/events testleri."""

    def test_events_returns_200(self, webhook_client):
        """Events endpoint 200 dönmeli."""
        resp = webhook_client.get("/api/webhooks/events")
        assert resp.status_code == 200

    def test_events_returns_list(self, webhook_client):
        """Events yanıtı events listesi içermeli."""
        resp = webhook_client.get("/api/webhooks/events")
        data = resp.get_json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_events_limit_param_honored(self, webhook_client):
        """limit parametresi sonuç sayısını sınırlamalı."""
        resp = webhook_client.get("/api/webhooks/events?limit=5")
        assert resp.status_code == 200


# ── /api/webhooks/config ─────────────────────────────────────────────────────

class TestWebhookConfig:
    """GET/PUT /api/webhooks/config testleri."""

    def test_get_config_returns_200(self, webhook_client):
        """Config GET 200 dönmeli."""
        resp = webhook_client.get("/api/webhooks/config")
        assert resp.status_code == 200

    def test_get_config_masks_sensitive_fields(self, webhook_client, monkeypatch):
        """Token alanları maskelenerek dönmeli."""
        import routes.webhook_routes as wr
        monkeypatch.setattr(
            wr,
            "_load_config",
            lambda: {**wr._DEFAULT_CONFIG, "github_token": "ghp_abcd1234efgh5678", "github_secret": "my-secret"},
        )

        resp = webhook_client.get("/api/webhooks/config")
        data = resp.get_json()
        token = data.get("github_token", "")
        # Full token kesinlikle dönmemeli
        assert token != "ghp_abcd1234efgh5678"
        # Secret maskeli olmalı
        assert data.get("github_secret") == "****"

    def test_put_config_updates_auto_run(self, webhook_client):
        """PUT config ayarları güncellemeli."""
        resp = webhook_client.put(
            "/api/webhooks/config",
            json={"auto_run_on_push": True, "run_browser": "firefox"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("ok") is True
