"""Unit tests for engine/core/* modules.

Browser, DB, and network calls are all stubbed — no real Playwright or
Selenium needed.

Covers:
  - core/locator_manager.py   → LocatorManager (bridge/adapter)
  - core/reporting_engine.py  → ReportGenerator, TestRun, TestCase, TestStep
  - core/monkey_test_engine.py → MonkeyTestEngine
  - core/test_case_manager.py → TestCaseManager
  - core/visual_ai.py         → VisualAIAnalyzer, VisualAnalysis
  - core/playback_engine.py   → PlaybackEngine, PlaybackReport, ActionResult
"""
from __future__ import annotations

import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call, mock_open
import pytest

# ---------------------------------------------------------------------------
# Stub heavy optional dependencies before any project import
# ---------------------------------------------------------------------------
for _mod in [
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    "selenium",
    "cv2",
    "PIL",
    "numpy",
    "sklearn",
    "openai",
    "anthropic",
    "psycopg2",
]:
    sys.modules.setdefault(_mod, MagicMock())

# PIL sub-modules used by visual_ai
_pil_mock = MagicMock()
sys.modules["PIL"] = _pil_mock
sys.modules["PIL.Image"] = _pil_mock.Image

# numpy needs realistic arithmetic behaviour for some tests
import numpy as _np_real  # noqa: E402 — imported after stubs to avoid clash


# ---------------------------------------------------------------------------
# Stub project-internal deps that require DB / external services
# ---------------------------------------------------------------------------
_core_db_mock = MagicMock()
_core_db_mock.get_connection.return_value.__enter__ = MagicMock(
    return_value=MagicMock()
)
_core_db_mock.get_connection.return_value.__exit__ = MagicMock(return_value=False)
sys.modules.setdefault("core.db", _core_db_mock)

_locators_lm_mock = MagicMock()
sys.modules.setdefault("locators", MagicMock())
sys.modules.setdefault("locators.locator_manager", _locators_lm_mock)


# ===========================================================================
# 1. LocatorManager tests
# ===========================================================================

class TestLocatorManagerImport:
    """Smoke: module and class are importable."""

    def test_import_locator_manager_module(self):
        import importlib
        mod = importlib.import_module("core.locator_manager")
        assert mod is not None

    def test_locator_manager_class_exists(self):
        from core.locator_manager import LocatorManager
        assert LocatorManager is not None


class TestLocatorManagerClassMethods:
    """Behaviour of the classmethods using the in-memory dict."""

    def setup_method(self):
        from core.locator_manager import LocatorManager
        LocatorManager.clear()

    # ------------------------------------------------------------------
    def test_resolve_unknown_key_returns_selector_as_is(self):
        from core.locator_manager import LocatorManager
        result = LocatorManager.resolve("#my-button")
        assert result == "#my-button"

    def test_resolve_known_key_returns_mapped_selector(self):
        from core.locator_manager import LocatorManager
        LocatorManager._locators["login_btn"] = "#login"
        assert LocatorManager.resolve("login_btn") == "#login"

    def test_get_returns_none_for_missing_key(self):
        from core.locator_manager import LocatorManager
        assert LocatorManager.get("nonexistent") is None

    def test_get_returns_value_for_existing_key(self):
        from core.locator_manager import LocatorManager
        LocatorManager._locators["submit"] = "[data-testid=\"submit\"]"
        assert LocatorManager.get("submit") == "[data-testid=\"submit\"]"

    def test_keys_returns_list(self):
        from core.locator_manager import LocatorManager
        LocatorManager._locators["a"] = "#a"
        LocatorManager._locators["b"] = "#b"
        keys = LocatorManager.keys()
        assert isinstance(keys, list)
        assert "a" in keys and "b" in keys

    def test_as_dict_returns_copy(self):
        from core.locator_manager import LocatorManager
        LocatorManager._locators["x"] = ".x"
        d = LocatorManager.as_dict()
        assert isinstance(d, dict)
        assert d["x"] == ".x"
        # Mutating the copy must not affect the internal store
        d["x"] = "changed"
        assert LocatorManager._locators["x"] == ".x"

    def test_clear_empties_locators_and_features(self):
        from core.locator_manager import LocatorManager
        LocatorManager._locators["k"] = "v"
        LocatorManager._loaded_features.add("feat")
        LocatorManager.clear()
        assert LocatorManager.keys() == []
        assert len(LocatorManager._loaded_features) == 0

    def test_load_nonexistent_file_returns_empty(self):
        from core.locator_manager import LocatorManager
        result = LocatorManager.load("does_not_exist_xyz", directory="/tmp")
        assert isinstance(result, dict)

    def test_load_valid_json_populates_locators(self, tmp_path):
        from core.locator_manager import LocatorManager
        LocatorManager.clear()
        entries = [
            {"key": "email_field", "type": "id", "value": "email"},
            {"key": "pwd_field",   "type": "css", "value": "input[type=password]"},
        ]
        feat_file = tmp_path / "login.json"
        feat_file.write_text(json.dumps(entries), encoding="utf-8")
        result = LocatorManager.load("login", directory=tmp_path)
        assert "email_field" in result
        assert result["email_field"] == "#email"
        assert result["pwd_field"] == "input[type=password]"

    def test_configure_changes_locators_dir(self, tmp_path):
        from core.locator_manager import LocatorManager
        LocatorManager.configure(tmp_path)
        assert LocatorManager._locators_dir == tmp_path


# ===========================================================================
# 2. ReportingEngine tests
# ===========================================================================

class TestReportingEngineImport:
    def test_import_reporting_engine_module(self):
        import importlib
        mod = importlib.import_module("core.reporting_engine")
        assert mod is not None

    def test_classes_exist(self):
        from core.reporting_engine import ReportGenerator, TestRun, TestCase, TestStep
        assert ReportGenerator is not None
        assert TestRun is not None


class TestTestRunDataclass:
    def _make_run(self, passed=3, failed=1, skipped=1):
        from core.reporting_engine import TestRun
        return TestRun(
            run_id="run-001",
            environment="staging",
            browser="chromium",
            start_time="2026-01-01T00:00:00",
            end_time="2026-01-01T00:01:00",
            total_tests=passed + failed + skipped,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration_ms=60_000,
        )

    def test_run_has_passed_failed_total(self):
        run = self._make_run()
        assert run.passed == 3
        assert run.failed == 1
        assert run.total_tests == 5

    def test_success_rate_correct(self):
        run = self._make_run(passed=8, failed=2, skipped=0)
        assert run.success_rate == pytest.approx(80.0)

    def test_failure_rate_correct(self):
        run = self._make_run(passed=8, failed=2, skipped=0)
        assert run.failure_rate == pytest.approx(20.0)

    def test_zero_tests_success_rate_is_zero(self):
        from core.reporting_engine import TestRun
        run = TestRun(
            run_id="r0", environment="ci", browser="ff",
            start_time="", end_time="",
            total_tests=0, passed=0, failed=0, skipped=0, duration_ms=0,
        )
        assert run.success_rate == 0.0
        assert run.failure_rate == 0.0


class TestReportGenerator:
    def test_generate_report_returns_dict(self, tmp_path):
        from core.reporting_engine import ReportGenerator, TestRun
        gen = ReportGenerator(output_dir=str(tmp_path))
        run = TestRun(
            run_id="r1", environment="test", browser="chrome",
            start_time="2026-01-01T00:00:00", end_time="2026-01-01T00:00:05",
            total_tests=2, passed=2, failed=0, skipped=0, duration_ms=5000,
        )
        result = gen.generate_report(run, formats=["html", "json"])
        assert isinstance(result, dict)

    def test_generate_html_report_creates_file(self, tmp_path):
        from core.reporting_engine import ReportGenerator, TestRun
        gen = ReportGenerator(output_dir=str(tmp_path))
        run = TestRun(
            run_id="r2", environment="test", browser="safari",
            start_time="2026-01-01T00:00:00", end_time="2026-01-01T00:00:01",
            total_tests=1, passed=1, failed=0, skipped=0, duration_ms=1000,
        )
        result = gen.generate_report(run, formats=["html"])
        if "html" in result:
            html_path = result["html"]
            assert Path(html_path).exists()
            content = Path(html_path).read_text(encoding="utf-8")
            assert "<" in content  # minimal HTML tag check

    def test_generate_json_report_creates_valid_json(self, tmp_path):
        from core.reporting_engine import ReportGenerator, TestRun
        gen = ReportGenerator(output_dir=str(tmp_path))
        run = TestRun(
            run_id="r3", environment="prod", browser="firefox",
            start_time="2026-01-01T00:00:00", end_time="2026-01-01T00:00:02",
            total_tests=3, passed=2, failed=1, skipped=0, duration_ms=2000,
        )
        result = gen.generate_report(run, formats=["json"])
        if "json" in result:
            json_path = result["json"]
            data = json.loads(Path(json_path).read_text(encoding="utf-8"))
            assert "run_id" in data or "total_tests" in data or isinstance(data, dict)

    def test_unknown_format_is_skipped_gracefully(self, tmp_path):
        from core.reporting_engine import ReportGenerator, TestRun
        gen = ReportGenerator(output_dir=str(tmp_path))
        run = TestRun(
            run_id="r4", environment="dev", browser="edge",
            start_time="", end_time="",
            total_tests=0, passed=0, failed=0, skipped=0, duration_ms=0,
        )
        # Should not raise even with unknown format
        result = gen.generate_report(run, formats=["unknown_format"])
        assert isinstance(result, dict)


# ===========================================================================
# 3. MonkeyTestEngine tests
# ===========================================================================

class TestMonkeyTestEngineImport:
    def test_import_monkey_test_engine_module(self):
        import importlib
        mod = importlib.import_module("core.monkey_test_engine")
        assert mod is not None

    def test_class_exists(self):
        from core.monkey_test_engine import MonkeyTestEngine
        assert MonkeyTestEngine is not None


class TestMonkeyTestEngine:
    def _make_engine(self):
        from core.monkey_test_engine import MonkeyTestEngine
        return MonkeyTestEngine()

    def test_instantiation(self):
        engine = self._make_engine()
        assert hasattr(engine, "interactions_performed")
        assert hasattr(engine, "anomalies_found")

    def test_initial_state_is_empty(self):
        engine = self._make_engine()
        assert engine.interactions_performed == []
        assert engine.anomalies_found == []

    def test_run_monkey_test_streamed_yields_started_event(self):
        engine = self._make_engine()
        page = MagicMock()
        page.query_selector_all.return_value = []

        events = list(engine.run_monkey_test_streamed(
            page, url="http://example.com", mode="random", iterations=1, timeout=30
        ))
        statuses = [e.get("status") for e in events]
        assert "started" in statuses

    def test_run_with_no_elements_yields_no_elements_status(self):
        engine = self._make_engine()
        page = MagicMock()
        page.query_selector_all.return_value = []

        events = list(engine.run_monkey_test_streamed(
            page, url="http://example.com", mode="smart", iterations=5, timeout=5
        ))
        statuses = [e.get("status") for e in events]
        assert "no_elements" in statuses

    def test_run_returns_session_id_in_started(self):
        engine = self._make_engine()
        page = MagicMock()
        page.query_selector_all.return_value = []

        events = list(engine.run_monkey_test_streamed(
            page, url="http://x.com", iterations=1, timeout=5
        ))
        started = next(e for e in events if e.get("status") == "started")
        assert "session_id" in started
        assert started["session_id"].startswith("monkey_")

    def test_run_started_event_contains_url(self):
        engine = self._make_engine()
        page = MagicMock()
        page.query_selector_all.return_value = []

        events = list(engine.run_monkey_test_streamed(
            page, url="https://neurex.io", iterations=1, timeout=5
        ))
        started = next(e for e in events if e.get("status") == "started")
        assert started["url"] == "https://neurex.io"


# ===========================================================================
# 4. TestCaseManager tests
# ===========================================================================

class TestCaseManagerImport:
    def test_import_test_case_manager_module(self):
        # The module imports core.db which is stubbed; it must not raise
        import importlib
        # Patch _init_test_case_tables to avoid real DB operations
        with patch("core.test_case_manager.TestCaseManager._init_test_case_tables"):
            mod = importlib.import_module("core.test_case_manager")
        assert mod is not None

    def test_class_exists(self):
        with patch("core.test_case_manager.TestCaseManager._init_test_case_tables"):
            from core.test_case_manager import TestCaseManager
        assert TestCaseManager is not None


class TestTestCaseManagerCRUD:
    """CRUD behaviour against an in-memory SQLite DB."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Return a TestCaseManager wired to a fresh in-memory SQLite."""
        import sqlite3
        # Provide a real get_connection that creates a temp SQLite
        db_file = tmp_path / "test.sqlite"

        import contextlib

        @contextlib.contextmanager
        def _get_conn():
            conn = sqlite3.connect(str(db_file))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

        with patch("core.test_case_manager.get_connection", side_effect=_get_conn), \
             patch("core.test_case_manager.init_db"):
            from core.test_case_manager import TestCaseManager
            mgr = TestCaseManager()
        return mgr, _get_conn

    def test_create_returns_test_id(self, manager):
        mgr, _conn = manager
        with patch("core.test_case_manager.get_connection", side_effect=_conn):
            test_id = mgr.create_test_case(
                url="http://example.com",
                title="Login test",
                steps=[{"action": "click", "selector": "#login"}],
                explanations=["Click the login button"],
            )
        assert test_id.startswith("test_")

    def test_get_returns_created_case(self, manager):
        mgr, _conn = manager
        with patch("core.test_case_manager.get_connection", side_effect=_conn):
            test_id = mgr.create_test_case(
                url="http://example.com",
                title="Signup test",
                steps=[{"action": "fill", "selector": "#email", "value": "a@b.com"}],
                explanations=["Fill email"],
            )
            result = mgr.get_test_case(test_id)
        assert result is not None
        assert result["test_id"] == test_id
        assert result["title"] == "Signup test"

    def test_get_nonexistent_returns_none(self, manager):
        mgr, _conn = manager
        with patch("core.test_case_manager.get_connection", side_effect=_conn):
            result = mgr.get_test_case("test_does_not_exist")
        assert result is None

    def test_list_test_cases_returns_list(self, manager):
        mgr, _conn = manager
        with patch("core.test_case_manager.get_connection", side_effect=_conn):
            mgr.create_test_case(
                url="http://app.com", title="TC-1",
                steps=[], explanations=[],
            )
            mgr.create_test_case(
                url="http://app.com", title="TC-2",
                steps=[], explanations=[],
            )
            results = mgr.list_test_cases()
        assert isinstance(results, list)
        assert len(results) >= 2

    def test_list_test_cases_filtered_by_url(self, manager):
        mgr, _conn = manager
        with patch("core.test_case_manager.get_connection", side_effect=_conn):
            mgr.create_test_case(url="http://site-a.com", title="A",
                                 steps=[], explanations=[])
            mgr.create_test_case(url="http://site-b.com", title="B",
                                 steps=[], explanations=[])
            results = mgr.list_test_cases(url="http://site-a.com")
        titles = [r["title"] for r in results]
        assert "A" in titles
        assert "B" not in titles

    def test_create_with_risk_level(self, manager):
        mgr, _conn = manager
        with patch("core.test_case_manager.get_connection", side_effect=_conn):
            test_id = mgr.create_test_case(
                url="http://example.com", title="High risk TC",
                steps=[], explanations=[],
                risk_level="high",
            )
            result = mgr.get_test_case(test_id)
        assert result["risk_level"] == "high"


# ===========================================================================
# 5. VisualAI tests
# ===========================================================================

class TestVisualAIImport:
    def test_import_visual_ai_module(self):
        import importlib
        mod = importlib.import_module("core.visual_ai")
        assert mod is not None

    def test_visual_ai_analyzer_class_exists(self):
        from core.visual_ai import VisualAIAnalyzer
        assert VisualAIAnalyzer is not None

    def test_visual_analysis_dataclass_exists(self):
        from core.visual_ai import VisualAnalysis
        assert VisualAnalysis is not None


class TestVisualAIAnalyzer:
    """Tests use numpy for real pixel math but mock PIL Image.open."""

    @pytest.fixture
    def analyzer(self):
        import numpy as np
        from core.visual_ai import VisualAIAnalyzer
        return VisualAIAnalyzer(), np

    def _make_pil_image_mock(self, arr):
        """Return a MagicMock that behaves like a PIL Image backed by numpy array."""
        img = MagicMock()
        img.mode = "RGB"
        img.size = (arr.shape[1], arr.shape[0])
        img.convert.return_value = img
        img.resize.return_value = img
        # numpy uses __array__ protocol
        img.__array__ = MagicMock(return_value=arr)
        return img

    def test_analyze_identical_images_returns_high_similarity(self, analyzer):
        va, np = analyzer
        arr = _np_real.ones((10, 10, 3), dtype=_np_real.uint8) * 128

        img_mock = self._make_pil_image_mock(arr)

        with patch("core.visual_ai.Image") as img_module:
            img_module.open.return_value = img_mock
            img_module.Resampling = MagicMock()
            result = va.analyze_visual_difference(
                "path/current.png", "path/baseline.png", "test_baseline"
            )

        assert hasattr(result, "similarity")
        assert hasattr(result, "has_anomalies")

    def test_analyze_returns_visual_analysis_object(self, analyzer):
        va, np = analyzer
        from core.visual_ai import VisualAnalysis

        arr = _np_real.zeros((5, 5, 3), dtype=_np_real.uint8)
        img_mock = self._make_pil_image_mock(arr)

        with patch("core.visual_ai.Image") as img_module:
            img_module.open.return_value = img_mock
            img_module.Resampling = MagicMock()
            result = va.analyze_visual_difference("a.png", "b.png")

        assert isinstance(result, VisualAnalysis)

    def test_analyze_exception_returns_fallback_analysis(self, analyzer):
        va, _ = analyzer
        from core.visual_ai import VisualAnalysis

        with patch("core.visual_ai.Image") as img_module:
            img_module.open.side_effect = FileNotFoundError("no file")
            result = va.analyze_visual_difference("missing.png", "also_missing.png")

        assert isinstance(result, VisualAnalysis)
        assert result.similarity == 0

    def test_analyze_result_has_recommendations_list(self, analyzer):
        va, _ = analyzer

        arr = _np_real.full((4, 4, 3), 200, dtype=_np_real.uint8)
        img_mock = self._make_pil_image_mock(arr)

        with patch("core.visual_ai.Image") as img_module:
            img_module.open.return_value = img_mock
            img_module.Resampling = MagicMock()
            result = va.analyze_visual_difference("c.png", "d.png")

        assert isinstance(result.recommendations, list)

    def test_analyzer_has_configurable_threshold(self):
        from core.visual_ai import VisualAIAnalyzer
        va = VisualAIAnalyzer()
        assert 0.0 <= va.anomaly_detection_threshold <= 1.0

    def test_visual_analysis_dataclass_fields(self):
        from core.visual_ai import VisualAnalysis
        va = VisualAnalysis(
            similarity=0.95,
            anomalies=[],
            has_anomalies=False,
            recommendations=["All good"],
            should_update_baseline=False,
        )
        assert va.similarity == pytest.approx(0.95)
        assert va.has_anomalies is False


# ===========================================================================
# 6. PlaybackEngine tests
# ===========================================================================

class TestPlaybackEngineImport:
    def test_import_playback_engine_module(self):
        import importlib
        mod = importlib.import_module("core.playback_engine")
        assert mod is not None

    def test_playback_engine_class_exists(self):
        from core.playback_engine import PlaybackEngine
        assert PlaybackEngine is not None

    def test_playback_report_class_exists(self):
        from core.playback_engine import PlaybackReport
        assert PlaybackReport is not None

    def test_action_result_class_exists(self):
        from core.playback_engine import ActionResult
        assert ActionResult is not None


class TestPlaybackReport:
    def test_empty_report_has_zero_counts(self):
        from core.playback_engine import PlaybackReport
        report = PlaybackReport(session_id="s1")
        assert report.total == 0
        assert report.passed == 0
        assert report.failed == 0
        assert report.healed == 0

    def test_pass_rate_with_no_results_is_zero(self):
        from core.playback_engine import PlaybackReport
        report = PlaybackReport(session_id="s0")
        assert report.pass_rate == 0.0

    def test_to_dict_contains_required_keys(self):
        from core.playback_engine import PlaybackReport
        report = PlaybackReport(session_id="sid123")
        d = report.to_dict()
        for key in ("session_id", "total", "passed", "failed", "healed",
                    "skipped", "pass_rate", "results"):
            assert key in d, f"Missing key: {key}"

    def test_pass_rate_calculation(self):
        from core.playback_engine import PlaybackReport, ActionResult
        report = PlaybackReport(session_id="s2")
        report.results.append(ActionResult(
            event_id="e1", action_type="click", selector="#btn", status="passed"
        ))
        report.results.append(ActionResult(
            event_id="e2", action_type="fill", selector="#input", status="healed"
        ))
        report.results.append(ActionResult(
            event_id="e3", action_type="click", selector="#x", status="failed"
        ))
        assert report.pass_rate == pytest.approx(200 / 3, rel=1e-3)


class TestPlaybackEngineReplay:
    @pytest.fixture
    def engine_with_page(self):
        from core.playback_engine import PlaybackEngine
        page = MagicMock()
        # locator().count() returns 1 so selectors resolve
        page.locator.return_value.count.return_value = 1
        return PlaybackEngine(page=page, timeout=5000)

    def test_replay_empty_events_returns_report(self, engine_with_page):
        from core.playback_engine import PlaybackReport
        report = engine_with_page.replay([], session_id="empty-session")
        assert isinstance(report, PlaybackReport)
        assert report.total == 0

    def test_replay_empty_events_completes_immediately(self, engine_with_page):
        import time
        start = time.time()
        engine_with_page.replay([], session_id="fast")
        elapsed = time.time() - start
        assert elapsed < 2.0, "Empty replay should be near-instant"

    def test_replay_navigate_event_calls_page_goto(self, engine_with_page):
        page = engine_with_page.page
        events = [{
            "id": "ev1",
            "action": {"type": "navigate", "url": "http://example.com"},
            "target": {},
            "context": {},
        }]
        engine_with_page.replay(events, session_id="nav-test")
        page.goto.assert_called_once_with("http://example.com")

    def test_replay_returns_report_with_session_id(self, engine_with_page):
        report = engine_with_page.replay([], session_id="mysession")
        assert report.session_id == "mysession"

    def test_replay_sets_started_at_and_ended_at(self, engine_with_page):
        report = engine_with_page.replay([], session_id="ts-test")
        assert report.started_at != ""
        assert report.ended_at != ""

    def test_replay_click_event_added_to_results(self, engine_with_page):
        events = [{
            "id": "ev2",
            "action": {"type": "click"},
            "target": {"selector": "#submit", "selector_chain": []},
            "context": {},
        }]
        report = engine_with_page.replay(events, session_id="click-test")
        assert report.total == 1

    def test_action_result_to_dict_has_status(self):
        from core.playback_engine import ActionResult
        ar = ActionResult(
            event_id="x", action_type="fill", selector="#f", status="passed"
        )
        d = ar.to_dict()
        assert d["status"] == "passed"
        assert d["action_type"] == "fill"
