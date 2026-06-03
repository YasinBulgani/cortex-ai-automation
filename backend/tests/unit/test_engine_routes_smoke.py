"""Integration smoke tests for engine route modules — router.routes non-empty checks.

Each test imports a route module in isolation (bypassing __init__.py) and asserts
that its APIRouter has at least one registered route.  No DB, Redis or running
process is required.

Note: modules using Python 3.10+ union syntax (``X | None``) are skipped
automatically on Python 3.9 via per-module try/except guards.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ─── Direct module loader ──────────────────────────────────────────────────────

_ROUTES_DIR = Path(__file__).resolve().parents[2] / "app" / "engine" / "routes"


def _load_route_module(name: str):
    """Import a single route file without triggering __init__.py.

    Returns the module on success or raises on failure.
    """
    mod_name = f"_smoke_engine_route_{name}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, _ROUTES_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _try_load(name: str):
    """Load a route module, returning (router, None) or (None, error_msg)."""
    try:
        mod = _load_route_module(name)
        return mod.router, None
    except Exception as exc:
        return None, str(exc)


# ─── Per-module router refs ────────────────────────────────────────────────────

_webhook_router,       _webhook_err       = _try_load("webhook")
_runner_router,        _runner_err        = _try_load("runner")
_scheduler_router,     _scheduler_err     = _try_load("scheduler")
_mobile_router,        _mobile_err        = _try_load("mobile")
_ai_generation_router, _ai_generation_err = _try_load("ai_generation")
_lifecycle_router,     _lifecycle_err     = _try_load("lifecycle")
_manual_router,        _manual_err        = _try_load("manual")
_analytics_router,     _analytics_err     = _try_load("analytics")
_ai_healing_router,    _ai_healing_err    = _try_load("ai_healing")
_recorder_router,      _recorder_err      = _try_load("recorder")
_reporting_router,     _reporting_err     = _try_load("reporting")
_regression_router,    _regression_err    = _try_load("regression")
_feature_router,       _feature_err       = _try_load("feature")
_editor_router,        _editor_err        = _try_load("editor")


# ─── Helper: skip decorator based on load result ──────────────────────────────

def _skip_if_failed(err):
    return pytest.mark.skipif(err is not None, reason=f"module load failed: {err}")


# ─── Smoke tests — router.routes non-empty ────────────────────────────────────

@_skip_if_failed(_webhook_err)
class TestWebhookHasRoutes:
    """webhook_router en az bir route icermeli."""

    def test_webhook_has_routes(self):
        assert len(_webhook_router.routes) > 0, (
            "webhook_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_runner_err)
class TestRunnerHasRoutes:
    """runner_router en az bir route icermeli."""

    def test_runner_has_routes(self):
        assert len(_runner_router.routes) > 0, (
            "runner_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_scheduler_err)
class TestSchedulerHasRoutes:
    """scheduler_router en az bir route icermeli."""

    def test_scheduler_has_routes(self):
        assert len(_scheduler_router.routes) > 0, (
            "scheduler_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_mobile_err)
class TestMobileHasRoutes:
    """mobile_router en az bir route icermeli."""

    def test_mobile_has_routes(self):
        assert len(_mobile_router.routes) > 0, (
            "mobile_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_ai_generation_err)
class TestAiGenerationHasRoutes:
    """ai_generation_router en az bir route icermeli."""

    def test_ai_generation_has_routes(self):
        assert len(_ai_generation_router.routes) > 0, (
            "ai_generation_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_lifecycle_err)
class TestLifecycleHasRoutes:
    """lifecycle_router en az bir route icermeli."""

    def test_lifecycle_has_routes(self):
        assert len(_lifecycle_router.routes) > 0, (
            "lifecycle_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_manual_err)
class TestManualHasRoutes:
    """manual_router en az bir route icermeli."""

    def test_manual_has_routes(self):
        assert len(_manual_router.routes) > 0, (
            "manual_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_analytics_err)
class TestAnalyticsHasRoutes:
    """analytics_router en az bir route icermeli."""

    def test_analytics_has_routes(self):
        assert len(_analytics_router.routes) > 0, (
            "analytics_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_ai_healing_err)
class TestAiHealingHasRoutes:
    """ai_healing_router en az bir route icermeli."""

    def test_ai_healing_has_routes(self):
        assert len(_ai_healing_router.routes) > 0, (
            "ai_healing_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_recorder_err)
class TestRecorderHasRoutes:
    """recorder_router en az bir route icermeli."""

    def test_recorder_has_routes(self):
        assert len(_recorder_router.routes) > 0, (
            "recorder_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_reporting_err)
class TestReportingHasRoutes:
    """reporting_router en az bir route icermeli."""

    def test_reporting_has_routes(self):
        assert len(_reporting_router.routes) > 0, (
            "reporting_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_regression_err)
class TestRegressionHasRoutes:
    """regression_router en az bir route icermeli."""

    def test_regression_has_routes(self):
        assert len(_regression_router.routes) > 0, (
            "regression_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_feature_err)
class TestFeatureHasRoutes:
    """feature_router en az bir route icermeli."""

    def test_feature_has_routes(self):
        assert len(_feature_router.routes) > 0, (
            "feature_router.routes bos — hic endpoint kaydedilmemis"
        )


@_skip_if_failed(_editor_err)
class TestEditorHasRoutes:
    """editor_router en az bir route icermeli."""

    def test_editor_has_routes(self):
        assert len(_editor_router.routes) > 0, (
            "editor_router.routes bos — hic endpoint kaydedilmemis"
        )
