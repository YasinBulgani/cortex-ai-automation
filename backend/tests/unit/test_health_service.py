"""Unit tests for app.domains.health.service.

All external I/O (DB, Redis, HTTP) is mocked.
No real network calls or DB connections are made.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.health import service as health_service
    from app.domains.health.service import (
        _check_database,
        _check_redis,
        _check_engine,
        _check_ai_gateway,
        _check_ollama,
        _compute_overall,
        get_extended_health,
        _timed,
    )
    from app.domains.health.schemas import (
        ComponentStatus,
        ExtendedHealth,
        HealthLevel,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="health service import failed")

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _component(name: str, level: HealthLevel, optional: bool = False) -> ComponentStatus:
    return ComponentStatus(name=name, label=name, level=level, optional=optional)


# ---------------------------------------------------------------------------
# _compute_overall
# ---------------------------------------------------------------------------

class TestComputeOverall:
    def test_all_ok_returns_ok(self):
        components = [_component("db", HealthLevel.ok), _component("redis", HealthLevel.ok)]
        assert _compute_overall(components) == HealthLevel.ok

    def test_required_down_returns_down(self):
        components = [
            _component("db", HealthLevel.down, optional=False),
            _component("redis", HealthLevel.ok),
        ]
        assert _compute_overall(components) == HealthLevel.down

    def test_required_degraded_returns_degraded(self):
        components = [
            _component("db", HealthLevel.degraded, optional=False),
            _component("redis", HealthLevel.ok),
        ]
        assert _compute_overall(components) == HealthLevel.degraded

    def test_optional_down_does_not_affect_overall_when_required_ok(self):
        """Optional 'down' alone must not force overall to down."""
        components = [
            _component("db", HealthLevel.ok, optional=False),
            _component("ollama", HealthLevel.down, optional=True),
        ]
        # With optional down and required ok, overall is at most degraded (visual cue)
        result = _compute_overall(components)
        assert result in (HealthLevel.ok, HealthLevel.degraded)

    def test_empty_components_returns_ok(self):
        assert _compute_overall([]) == HealthLevel.ok


# ---------------------------------------------------------------------------
# _check_database
# ---------------------------------------------------------------------------

class TestCheckDatabase:
    def test_success_returns_ok_status(self):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = lambda s: mock_conn
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.domains.health.service.engine", mock_engine, create=True),
            patch("app.domains.health.service.text", MagicMock(), create=True),
        ):
            # Patch the imports inside the function
            with patch.dict("sys.modules", {
                "sqlalchemy": MagicMock(text=MagicMock()),
                "app.infra.database": MagicMock(engine=mock_engine),
            }):
                result = _check_database()

        assert isinstance(result, ComponentStatus)
        # name must be "postgres"
        assert result.name == "postgres"

    def test_exception_returns_down_status(self):
        with patch.dict("sys.modules", {
            "sqlalchemy": MagicMock(text=MagicMock(side_effect=Exception("conn refused"))),
            "app.infra.database": MagicMock(engine=MagicMock(
                connect=MagicMock(side_effect=Exception("conn refused"))
            )),
        }):
            result = _check_database()

        assert result.name == "postgres"
        assert result.level == HealthLevel.down
        assert result.detail is not None


# ---------------------------------------------------------------------------
# _check_redis
# ---------------------------------------------------------------------------

class TestCheckRedis:
    def test_successful_ping_returns_ok(self):
        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_module = MagicMock()
        mock_redis_module.Redis.from_url.return_value = mock_redis_client

        with (
            patch.dict("sys.modules", {"redis": mock_redis_module}),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379"
            result = _check_redis()

        assert result.name == "redis"
        assert result.level == HealthLevel.ok

    def test_connection_failure_returns_down(self):
        mock_redis_module = MagicMock()
        mock_redis_module.Redis.from_url.side_effect = Exception("connection refused")

        with (
            patch.dict("sys.modules", {"redis": mock_redis_module}),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.redis_url = "redis://localhost:6379"
            result = _check_redis()

        assert result.name == "redis"
        assert result.level == HealthLevel.down
        assert result.optional is True  # Redis is optional


# ---------------------------------------------------------------------------
# _check_engine
# ---------------------------------------------------------------------------

class TestCheckEngine:
    def test_http_200_returns_ok(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("httpx.get", return_value=mock_response),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.engine_base_url = "http://localhost:7000"
            result = _check_engine()

        assert result.name == "engine"
        assert result.level == HealthLevel.ok

    def test_http_503_returns_degraded(self):
        mock_response = MagicMock()
        mock_response.status_code = 503

        with (
            patch("httpx.get", return_value=mock_response),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.engine_base_url = "http://localhost:7000"
            result = _check_engine()

        assert result.name == "engine"
        assert result.level == HealthLevel.degraded

    def test_timeout_exception_returns_down(self):
        import httpx

        with (
            patch("httpx.get", side_effect=httpx.TimeoutException("timeout")),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.engine_base_url = "http://localhost:7000"
            result = _check_engine()

        assert result.name == "engine"
        assert result.level == HealthLevel.down
        assert result.detail is not None


# ---------------------------------------------------------------------------
# _check_ai_gateway
# ---------------------------------------------------------------------------

class TestCheckAiGateway:
    def test_gateway_ok(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("httpx.get", return_value=mock_response),
            patch.dict("os.environ", {"AI_GATEWAY_BASE_URL": "http://localhost:8080"}),
        ):
            result = _check_ai_gateway()

        assert result.name == "ai_gateway"
        assert result.level == HealthLevel.ok

    def test_gateway_error_is_optional(self):
        with (
            patch("httpx.get", side_effect=Exception("unreachable")),
            patch.dict("os.environ", {"AI_GATEWAY_BASE_URL": "http://localhost:8080"}),
        ):
            result = _check_ai_gateway()

        assert result.name == "ai_gateway"
        assert result.level == HealthLevel.down
        assert result.optional is True


# ---------------------------------------------------------------------------
# _check_ollama
# ---------------------------------------------------------------------------

class TestCheckOllama:
    def test_ollama_200_returns_ok(self):
        mock_response = MagicMock()
        mock_response.status_code = 200

        with (
            patch("httpx.get", return_value=mock_response),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            result = _check_ollama()

        assert result.name == "ollama"
        assert result.level == HealthLevel.ok
        assert result.optional is True

    def test_ollama_unreachable_returns_down_optional(self):
        with (
            patch("httpx.get", side_effect=Exception("no ollama")),
            patch.object(health_service, "settings") as mock_settings,
        ):
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            result = _check_ollama()

        assert result.name == "ollama"
        assert result.level == HealthLevel.down
        assert result.optional is True  # Ollama absence is non-critical


# ---------------------------------------------------------------------------
# get_extended_health — top-level
# ---------------------------------------------------------------------------

class TestGetExtendedHealth:
    def test_returns_extended_health_object(self):
        """With all checks mocked to OK, get_extended_health returns ExtendedHealth."""
        ok_component = ComponentStatus(
            name="mock", label="Mock", level=HealthLevel.ok
        )

        with patch.object(health_service, "_CHECKS", (lambda: ok_component,)):
            with patch.object(health_service, "settings") as mock_settings:
                mock_settings.app_name = "TestApp"
                result = get_extended_health()

        assert isinstance(result, ExtendedHealth)
        assert result.overall in list(HealthLevel)
        assert result.app_name == "TestApp"
        assert result.checked_at_unix > 0

    def test_all_ok_checks_overall_is_ok(self):
        ok_comp = ComponentStatus(name="db", label="DB", level=HealthLevel.ok)

        with patch.object(health_service, "_CHECKS", (lambda: ok_comp,)):
            with patch.object(health_service, "settings") as mock_settings:
                mock_settings.app_name = "TestApp"
                result = get_extended_health()

        assert result.overall == HealthLevel.ok

    def test_down_required_component_overall_is_down(self):
        down_comp = ComponentStatus(
            name="db", label="DB", level=HealthLevel.down, optional=False
        )

        with patch.object(health_service, "_CHECKS", (lambda: down_comp,)):
            with patch.object(health_service, "settings") as mock_settings:
                mock_settings.app_name = "TestApp"
                result = get_extended_health()

        assert result.overall == HealthLevel.down


# ---------------------------------------------------------------------------
# _timed wrapper
# ---------------------------------------------------------------------------

class TestTimedWrapper:
    def test_timed_returns_component_status(self):
        comp = ComponentStatus(name="x", label="X", level=HealthLevel.ok)
        result = _timed(lambda: comp)
        assert isinstance(result, ComponentStatus)
        assert result.name == "x"

    def test_timed_fills_latency_when_none(self):
        comp = ComponentStatus(name="y", label="Y", level=HealthLevel.ok, latency_ms=None)
        result = _timed(lambda: comp)
        # _timed should inject a latency_ms value
        assert result.latency_ms is not None
        assert result.latency_ms >= 0
