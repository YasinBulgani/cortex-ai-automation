"""Unit tests for miscellaneous ai domain pure helper functions.

All tests are self-contained: no DB, no Redis, no HTTP.
Covers:
  - quality_metrics._empty_metrics: default metrics dict structure
  - embedding_cache._key: cache key generation (SHA256 + prefix)
  - artifact_retention._artifact_run_is_eligible: run eligibility check
  - artifact_retention._compact_error: exception → short string
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

try:
    from app.domains.ai.quality_metrics import _empty_metrics
    _QM_OK = True
except ImportError:
    _QM_OK = False

try:
    from app.domains.ai.embedding_cache import _key as _embed_key
    _EC_OK = True
except ImportError:
    _EC_OK = False

try:
    from app.domains.ai.artifact_retention import (
        _artifact_run_is_eligible,
        _compact_error,
    )
    _AR_OK = True
except ImportError:
    _AR_OK = False


# ---------------------------------------------------------------------------
# quality_metrics._empty_metrics
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QM_OK, reason="quality_metrics import failed")
class TestEmptyMetrics:
    def test_returns_dict(self):
        assert isinstance(_empty_metrics(7), dict)

    def test_period_days_matches_input(self):
        result = _empty_metrics(30)
        assert result["period"]["days"] == 30

    def test_overview_total_calls_zero(self):
        result = _empty_metrics(7)
        assert result["overview"]["total_calls"] == 0

    def test_overview_success_rate_zero(self):
        result = _empty_metrics(7)
        assert result["overview"]["success_rate"] == 0

    def test_by_agent_is_list(self):
        assert isinstance(_empty_metrics(7)["by_agent"], list)

    def test_by_model_is_list(self):
        assert isinstance(_empty_metrics(7)["by_model"], list)

    def test_recommendations_is_list(self):
        assert isinstance(_empty_metrics(7)["recommendations"], list)

    def test_period_start_before_end(self):
        result = _empty_metrics(7)
        start = result["period"]["start"]
        end = result["period"]["end"]
        assert start < end

    def test_different_days_different_period(self):
        r7 = _empty_metrics(7)
        r30 = _empty_metrics(30)
        assert r7["period"]["days"] != r30["period"]["days"]

    def test_daily_trend_is_list(self):
        assert isinstance(_empty_metrics(7)["daily_trend"], list)


# ---------------------------------------------------------------------------
# embedding_cache._key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EC_OK, reason="embedding_cache import failed")
class TestEmbedCacheKey:
    def test_returns_string(self):
        assert isinstance(_embed_key("hello"), str)

    def test_deterministic(self):
        assert _embed_key("hello world") == _embed_key("hello world")

    def test_different_text_different_key(self):
        assert _embed_key("text A") != _embed_key("text B")

    def test_model_in_key(self):
        result = _embed_key("test", model="nomic-embed-text")
        assert "nomic-embed-text" in result

    def test_different_model_different_key(self):
        k1 = _embed_key("text", model="model-A")
        k2 = _embed_key("text", model="model-B")
        assert k1 != k2

    def test_whitespace_normalized(self):
        # "hello  world" and "hello world" → same after normalization
        k1 = _embed_key("hello  world")
        k2 = _embed_key("hello world")
        assert k1 == k2

    def test_case_lowercased(self):
        k1 = _embed_key("Hello World")
        k2 = _embed_key("hello world")
        assert k1 == k2

    def test_empty_string(self):
        result = _embed_key("")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# artifact_retention._artifact_run_is_eligible
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AR_OK, reason="artifact_retention import failed")
class TestArtifactRunIsEligible:
    class _Run:
        def __init__(self, status: str, completed_at):
            self.status = status
            self.completed_at = completed_at

    class _Artifact:
        def __init__(self, run):
            self.run = run

    def _make_artifact(self, status: str, days_ago: int = 5, aware: bool = True):
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        if not aware:
            dt = dt.replace(tzinfo=None)
        run = self._Run(status, dt)
        return self._Artifact(run)

    def test_eligible_with_correct_status_and_old_enough(self):
        artifact = self._make_artifact("completed", days_ago=10)
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        result = _artifact_run_is_eligible(artifact, cutoff, {"completed"})
        assert result is True

    def test_not_eligible_if_too_recent(self):
        artifact = self._make_artifact("completed", days_ago=1)
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        result = _artifact_run_is_eligible(artifact, cutoff, {"completed"})
        assert result is False

    def test_not_eligible_wrong_status(self):
        artifact = self._make_artifact("running", days_ago=10)
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        result = _artifact_run_is_eligible(artifact, cutoff, {"completed"})
        assert result is False

    def test_no_run_returns_false(self):
        class NoRun:
            run = None
        result = _artifact_run_is_eligible(NoRun(), datetime.now(timezone.utc), {"completed"})
        assert result is False

    def test_naive_completed_at_gets_utc(self):
        artifact = self._make_artifact("completed", days_ago=10, aware=False)
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        result = _artifact_run_is_eligible(artifact, cutoff, {"completed"})
        assert result is True

    def test_no_completed_at_returns_false(self):
        class RunNoDate:
            status = "completed"
            completed_at = None
        artifact = self._Artifact(RunNoDate())
        result = _artifact_run_is_eligible(artifact, datetime.now(timezone.utc), {"completed"})
        assert result is False

    def test_returns_bool(self):
        artifact = self._make_artifact("completed")
        result = _artifact_run_is_eligible(artifact, datetime.now(timezone.utc), {"completed"})
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# artifact_retention._compact_error
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AR_OK, reason="artifact_retention import failed")
class TestCompactError:
    def test_returns_string(self):
        assert isinstance(_compact_error(ValueError("test")), str)

    def test_includes_exception_class(self):
        result = _compact_error(ValueError("test error"))
        assert "ValueError" in result

    def test_includes_error_message(self):
        result = _compact_error(RuntimeError("connection failed"))
        assert "connection" in result

    def test_empty_message_uses_class_name(self):
        result = _compact_error(ValueError(""))
        assert "ValueError" in result

    def test_multiline_message_truncated_to_first_line(self):
        result = _compact_error(RuntimeError("line one\nline two\nline three"))
        assert "line two" not in result

    def test_only_first_line_of_message(self):
        result = _compact_error(RuntimeError("first line\nsecond line"))
        assert "second line" not in result
