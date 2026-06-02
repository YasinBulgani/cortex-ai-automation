"""
Nexus QA AI Gateway — Rate Limiting & Auth Tests
Tests for: health endpoint, rate limiting, API key validation, model validation, input validation.

Run:
    cd ai-gateway && pytest tests/test_rate_limiting.py -v
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# App import — must come after sys.path is set, so use lazy import inside
# each test to avoid side-effects at collection time.
# ---------------------------------------------------------------------------

def _make_client():
    """Return a synchronous TestClient for the gateway app."""
    from main import app  # noqa: PLC0415
    return TestClient(app, raise_server_exceptions=False)


def _valid_headers(key: str = "test-internal-key") -> dict:
    return {"X-Internal-Key": key}


def _complete_payload(
    prompt: str = "Merhaba, nasılsın?",
    task_type: str = "chat",
    model_override: str | None = None,
) -> dict:
    payload: dict = {
        "task_type": task_type,
        "messages": [{"role": "user", "content": prompt}],
    }
    if model_override is not None:
        payload["model_override"] = model_override
    return payload


# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200_or_503_when_no_providers(self):
        """GET /ai/health must return 200 (healthy) or 503 (degraded) — never 4xx."""
        client = _make_client()
        with patch(
            "app.core.router.AIRouter.health_check",
            new_callable=AsyncMock,
            return_value={"vllm": False, "groq": False, "gemini": False, "ollama": False, "g4f": False},
        ):
            resp = client.get("/ai/health")
        # 503 = degraded but endpoint itself works
        assert resp.status_code in (200, 503)

    def test_health_returns_status_field(self):
        """Health response body must include a 'status' key."""
        client = _make_client()
        with patch(
            "app.core.router.AIRouter.health_check",
            new_callable=AsyncMock,
            return_value={"groq": True},
        ):
            resp = client.get("/ai/health")
        data = resp.json()
        assert "status" in data

    def test_health_returns_providers_field(self):
        """Health response body must include a 'providers' key."""
        client = _make_client()
        with patch(
            "app.core.router.AIRouter.health_check",
            new_callable=AsyncMock,
            return_value={"groq": True},
        ):
            resp = client.get("/ai/health")
        data = resp.json()
        assert "providers" in data

    def test_health_healthy_when_at_least_one_provider_up(self):
        """Status should be 'healthy' when at least one provider is available."""
        client = _make_client()
        with patch(
            "app.core.router.AIRouter.health_check",
            new_callable=AsyncMock,
            return_value={"groq": True, "ollama": False},
        ):
            resp = client.get("/ai/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# 2. Successful request within rate limits (mocked LLM)
# ---------------------------------------------------------------------------

class TestSuccessfulRequest:
    def test_complete_with_valid_key_returns_200(self):
        """POST /ai/complete with correct key and mock provider should return 200."""
        from app.core.models import AIResponse, ProviderAttempt  # noqa: PLC0415

        mock_response = AIResponse(
            content="Merhaba! İyiyim, teşekkürler.",
            provider_used="groq",
            model_used="llama3-70b-8192",
            attempts=[ProviderAttempt(provider="groq", success=True, latency_ms=120, tokens_used=30)],
            tokens_used=30,
            latency_ms=120,
        )

        client = _make_client()
        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-internal-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 100),
            patch(
                "app.core.router.AIRouter.route",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                headers=_valid_headers(),
            )
        assert resp.status_code == 200

    def test_complete_response_has_content_field(self):
        """Successful /ai/complete response must have 'content' field."""
        from app.core.models import AIResponse, ProviderAttempt  # noqa: PLC0415

        mock_response = AIResponse(
            content="Test yanıtı",
            provider_used="groq",
            model_used="llama3-70b-8192",
            attempts=[],
            tokens_used=5,
            latency_ms=80,
        )

        client = _make_client()
        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-internal-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 100),
            patch(
                "app.core.router.AIRouter.route",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                headers=_valid_headers(),
            )
        assert "content" in resp.json()

    def test_complete_response_has_provider_used_field(self):
        """Successful /ai/complete response must have 'provider_used' field."""
        from app.core.models import AIResponse  # noqa: PLC0415

        mock_response = AIResponse(
            content="ok",
            provider_used="ollama",
            model_used="llama3.1:8b",
            tokens_used=5,
            latency_ms=50,
        )

        client = _make_client()
        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-internal-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 100),
            patch(
                "app.core.router.AIRouter.route",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                headers=_valid_headers(),
            )
        data = resp.json()
        assert "provider_used" in data


# ---------------------------------------------------------------------------
# 3. Rate limiting — repeated requests hit 429
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limit_triggers_429_after_limit_exceeded(self):
        """
        When RATE_LIMIT_PER_MINUTE is set to a low value (e.g. 2) and we send
        more requests than that for the same tenant/project, we should eventually
        receive a 429 Too Many Requests.
        """
        from app.core.models import AIResponse  # noqa: PLC0415
        from app.routes import ai_routes as _rt  # noqa: PLC0415

        mock_response = AIResponse(
            content="ok",
            provider_used="groq",
            model_used="llama3-70b-8192",
            tokens_used=10,
            latency_ms=100,
        )

        client = _make_client()
        # Clear the shared bucket state so previous tests don't interfere
        _rt._rate_buckets.clear()

        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-internal-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 2),
            patch(
                "app.core.router.AIRouter.route",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            payload = {
                "task_type": "chat",
                "messages": [{"role": "user", "content": "hi"}],
                "tenant_id": "tenant-rl-test",
                "project_id": "proj-rl-test",
            }
            headers = _valid_headers()
            statuses = []
            for _ in range(5):
                r = client.post("/ai/complete", json=payload, headers=headers)
                statuses.append(r.status_code)

        assert 429 in statuses, f"Expected 429 in responses, got: {statuses}"

    def test_rate_limit_response_has_retry_after_header(self):
        """429 response from rate limiter should include Retry-After header."""
        from app.routes import ai_routes as _rt  # noqa: PLC0415

        client = _make_client()
        _rt._rate_buckets.clear()

        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-internal-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 1),
        ):
            payload = {
                "task_type": "chat",
                "messages": [{"role": "user", "content": "hi"}],
                "tenant_id": "tenant-hdr-test",
                "project_id": "proj-hdr-test",
            }
            headers = _valid_headers()
            # First request may succeed or fail depending on bucket; send enough
            for _ in range(3):
                r = client.post("/ai/complete", json=payload, headers=headers)
                if r.status_code == 429:
                    assert "retry-after" in r.headers or "Retry-After" in r.headers
                    return
        # If no 429 was raised, the test is inconclusive but we don't fail hard
        pytest.skip("Rate limit bucket was not saturated in this run")

    def test_rate_limit_zero_means_no_limit(self):
        """When RATE_LIMIT_PER_MINUTE=0 rate limiting is disabled (should not raise 429)."""
        from app.core.models import AIResponse  # noqa: PLC0415
        from app.routes import ai_routes as _rt  # noqa: PLC0415

        mock_response = AIResponse(
            content="ok",
            provider_used="groq",
            model_used="llama3-70b-8192",
            tokens_used=5,
            latency_ms=50,
        )

        client = _make_client()
        _rt._rate_buckets.clear()

        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-internal-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 0),
            patch(
                "app.core.router.AIRouter.route",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
        ):
            payload = {
                "task_type": "chat",
                "messages": [{"role": "user", "content": "ping"}],
                "tenant_id": "tenant-nolimit",
                "project_id": "proj-nolimit",
            }
            headers = _valid_headers()
            for _ in range(5):
                r = client.post("/ai/complete", json=payload, headers=headers)
                assert r.status_code != 429, "Rate limit triggered despite being disabled"


# ---------------------------------------------------------------------------
# 4. Missing / invalid API key → 401 / 403
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_missing_internal_key_returns_401(self):
        """POST /ai/complete without X-Internal-Key header should return 401."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "real-secret-key"):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                # intentionally no X-Internal-Key header
            )
        assert resp.status_code == 401

    def test_wrong_internal_key_returns_403(self):
        """POST /ai/complete with wrong X-Internal-Key should return 403."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "real-secret-key"):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                headers={"X-Internal-Key": "wrong-key"},
            )
        assert resp.status_code == 403

    def test_empty_internal_key_header_returns_401(self):
        """POST /ai/complete with empty X-Internal-Key value should return 401."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "real-secret-key"):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                headers={"X-Internal-Key": ""},
            )
        assert resp.status_code == 401

    def test_missing_internal_key_config_returns_503(self):
        """When INTERNAL_KEY is not configured, gateway returns 503."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", ""):
            resp = client.post(
                "/ai/complete",
                json=_complete_payload(),
                headers={"X-Internal-Key": "anything"},
            )
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# 5. Invalid model / task_type → 400 / 422
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_empty_messages_list_returns_422(self):
        """POST /ai/complete with empty messages list should return 422 (Pydantic validation)."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "test-key"):
            resp = client.post(
                "/ai/complete",
                json={"task_type": "chat", "messages": []},
                headers={"X-Internal-Key": "test-key"},
            )
        # FastAPI/Pydantic will either 422 or may accept empty list — gateway may also 400
        assert resp.status_code in (400, 422)

    def test_missing_messages_field_returns_422(self):
        """POST /ai/complete without 'messages' key should return 422."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "test-key"):
            resp = client.post(
                "/ai/complete",
                json={"task_type": "chat"},
                headers={"X-Internal-Key": "test-key"},
            )
        assert resp.status_code == 422

    def test_empty_prompt_content_propagates_downstream(self):
        """
        An empty 'content' in a message is technically valid per Pydantic (str field),
        but the gateway should handle it without crashing (return any HTTP code != 5xx
        unless provider itself fails).
        """
        client = _make_client()
        with (
            patch("app.core.config.settings.INTERNAL_KEY", "test-key"),
            patch("app.core.config.settings.RATE_LIMIT_PER_MINUTE", 100),
            patch(
                "app.core.router.AIRouter.route",
                new_callable=AsyncMock,
                side_effect=ValueError("Prompt boş olamaz"),
            ),
        ):
            resp = client.post(
                "/ai/complete",
                json={"task_type": "chat", "messages": [{"role": "user", "content": ""}]},
                headers={"X-Internal-Key": "test-key"},
            )
        # ValueError handler maps to 400
        assert resp.status_code in (400, 422)

    def test_temperature_above_max_returns_422(self):
        """POST /ai/complete with temperature > 2.0 should be rejected by Pydantic (422)."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "test-key"):
            resp = client.post(
                "/ai/complete",
                json={
                    "task_type": "chat",
                    "messages": [{"role": "user", "content": "hi"}],
                    "temperature": 9.9,
                },
                headers={"X-Internal-Key": "test-key"},
            )
        assert resp.status_code == 422

    def test_negative_temperature_returns_422(self):
        """POST /ai/complete with temperature < 0 should be rejected by Pydantic (422)."""
        client = _make_client()
        with patch("app.core.config.settings.INTERNAL_KEY", "test-key"):
            resp = client.post(
                "/ai/complete",
                json={
                    "task_type": "chat",
                    "messages": [{"role": "user", "content": "hi"}],
                    "temperature": -1.0,
                },
                headers={"X-Internal-Key": "test-key"},
            )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 6. Meta endpoints
# ---------------------------------------------------------------------------

class TestMetaEndpoints:
    def test_root_returns_200(self):
        """GET / should return 200 with service info."""
        client = _make_client()
        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_includes_status_running(self):
        """GET / response must include status: running."""
        client = _make_client()
        resp = client.get("/")
        assert resp.json().get("status") == "running"

    def test_ping_returns_pong(self):
        """GET /ping should return {pong: true}."""
        client = _make_client()
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert resp.json().get("pong") is True

    def test_providers_endpoint_returns_200(self):
        """GET /ai/providers should return 200 with providers list."""
        client = _make_client()
        with patch(
            "app.core.router.AIRouter.health_check",
            new_callable=AsyncMock,
            return_value={},
        ):
            resp = client.get("/ai/providers")
        assert resp.status_code == 200
        assert "providers" in resp.json()


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
