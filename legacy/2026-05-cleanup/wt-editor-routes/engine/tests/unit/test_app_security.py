import importlib
import sys

import pytest


@pytest.fixture
def engine_client(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


def test_manual_api_requires_auth(engine_client):
    response = engine_client.get("/api/manual-tests")
    assert response.status_code == 401


def test_internal_key_allows_engine_api(engine_client):
    response = engine_client.get(
        "/api/manual-tests",
        headers={"X-Internal-Key": "test-engine-internal"},
    )
    assert response.status_code == 200


def test_internal_key_cannot_bypass_editor_routes(engine_client):
    response = engine_client.get(
        "/api/editor/tree",
        headers={"X-Internal-Key": "test-engine-internal"},
    )
    assert response.status_code == 401


def test_metrics_requires_auth(engine_client):
    response = engine_client.get("/metrics")
    assert response.status_code == 401


def test_allure_report_requires_auth(engine_client):
    response = engine_client.get("/reports/allure-report/")
    assert response.status_code == 401


def test_internal_key_allows_metrics(engine_client):
    response = engine_client.get(
        "/metrics",
        headers={"X-Internal-Key": "test-engine-internal"},
    )
    assert response.status_code in {200, 503}


def test_cors_blocks_unlisted_origin(engine_client):
    response = engine_client.get(
        "/health",
        headers={"Origin": "https://evil.example"},
    )
    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_cors_allows_configured_origin(engine_client):
    response = engine_client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"


def test_run_maven_rejects_path_outside_allowed_roots(engine_client):
    response = engine_client.post(
        "/api/run-maven",
        json={"maven_path": "../../"},
        headers={"X-Internal-Key": "test-engine-internal"},
    )
    assert response.status_code == 400
    assert "izinli kok dizinlerinin disinda" in response.get_json()["error"]


def test_flask_debug_disabled_in_ci_even_if_requested(monkeypatch):
    monkeypatch.setenv("APP_ENV", "ci")
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("ENGINE_DEBUG", "1")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")
    sys.modules.pop("app", None)

    module = importlib.import_module("app")
    assert module._should_enable_flask_debug() is False


def test_webhook_secret_required_in_strict_mode(engine_client, monkeypatch):
    import routes.webhook_routes as webhook_routes

    monkeypatch.setenv("WEBHOOK_REQUIRE_SECRETS", "1")
    monkeypatch.setattr(
        webhook_routes,
        "_load_config",
        lambda: {
            **webhook_routes._DEFAULT_CONFIG,
            "github_secret": "",
            "github_token": "",
        },
    )

    response = engine_client.post(
        "/api/webhooks/github",
        json={"repository": {"full_name": "bgts/repo"}},
        headers={"X-GitHub-Event": "push"},
    )
    assert response.status_code == 503
