"""Unit tests for AI embedding cache and artifact retention pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/embedding_cache.py:
    _key
  app/domains/ai/artifact_retention.py:
    _artifact_run_is_eligible, _resolve_retention_path, _compact_error
"""

from __future__ import annotations

import hashlib
import types
from datetime import datetime, timezone, timedelta

import pytest

from app.domains.ai.embedding_cache import _key
from app.domains.ai.artifact_retention import (
    _artifact_run_is_eligible,
    _compact_error,
    _resolve_retention_path,
)


# ── _key (embedding cache) ────────────────────────────────────────────────────


class TestEmbeddingCacheKey:
    def test_returns_string(self) -> None:
        assert isinstance(_key("hello world"), str)

    def test_contains_model_name(self) -> None:
        result = _key("test", model="my-model")
        assert "my-model" in result

    def test_default_model_in_key(self) -> None:
        result = _key("test")
        assert "nomic-embed-text" in result

    def test_deterministic(self) -> None:
        assert _key("same text") == _key("same text")

    def test_different_text_different_key(self) -> None:
        assert _key("text A") != _key("text B")

    def test_different_model_different_key(self) -> None:
        assert _key("same text", "model-a") != _key("same text", "model-b")

    def test_whitespace_normalized(self) -> None:
        # Multiple spaces and tabs should produce same key
        assert _key("hello   world") == _key("hello world")
        assert _key("hello\t\tworld") == _key("hello world")

    def test_case_normalized(self) -> None:
        # Lowercased before hashing
        assert _key("HELLO WORLD") == _key("hello world")

    def test_has_prefix(self) -> None:
        result = _key("test")
        # Should have a colon-separated prefix structure
        assert ":" in result

    def test_empty_string_handled(self) -> None:
        result = _key("")
        assert isinstance(result, str)
        assert len(result) > 0


# ── _artifact_run_is_eligible ─────────────────────────────────────────────────


class TestArtifactRunIsEligible:
    def _past(self, days: int = 10) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=days)

    def _future(self, days: int = 1) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=days)

    def _make_run(self, status: str = "completed", completed_at=None) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            status=status,
            completed_at=completed_at or self._past(30),
        )

    def _make_artifact(self, run=None) -> types.SimpleNamespace:
        return types.SimpleNamespace(run=run)

    def test_eligible_when_completed_before_cutoff(self) -> None:
        run = self._make_run("completed", self._past(30))
        artifact = self._make_artifact(run)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is True

    def test_not_eligible_when_completed_after_cutoff(self) -> None:
        run = self._make_run("completed", self._past(2))
        artifact = self._make_artifact(run)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is False

    def test_not_eligible_wrong_status(self) -> None:
        run = self._make_run("failed", self._past(30))
        artifact = self._make_artifact(run)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is False

    def test_not_eligible_when_no_run(self) -> None:
        artifact = self._make_artifact(run=None)
        cutoff = datetime.now(timezone.utc)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is False

    def test_not_eligible_when_no_completed_at(self) -> None:
        run = types.SimpleNamespace(status="completed", completed_at=None)
        artifact = self._make_artifact(run)
        cutoff = datetime.now(timezone.utc)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is False

    def test_naive_completed_at_treated_as_utc(self) -> None:
        naive = datetime.utcnow() - timedelta(days=30)
        run = types.SimpleNamespace(status="completed", completed_at=naive)
        artifact = self._make_artifact(run)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is True

    def test_multiple_statuses_in_set(self) -> None:
        run = self._make_run("failed", self._past(30))
        artifact = self._make_artifact(run)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed", "failed"}) is True


# ── _resolve_retention_path ───────────────────────────────────────────────────


class TestResolveRetentionPath:
    def test_empty_path_returns_empty_path_status(self) -> None:
        status, path = _resolve_retention_path("")
        assert status == "empty_path"
        assert path is None

    def test_http_url_returns_url_artifact(self) -> None:
        status, path = _resolve_retention_path("http://example.com/file.zip")
        assert status == "url_artifact"
        assert path is None

    def test_https_url_returns_url_artifact(self) -> None:
        status, path = _resolve_retention_path("https://s3.amazonaws.com/bucket/file")
        assert status == "url_artifact"
        assert path is None

    def test_path_outside_artifacts_dir_returns_outside_status(self) -> None:
        status, path = _resolve_retention_path("/etc/passwd")
        assert status == "outside_artifacts_dir"
        assert path is None

    def test_returns_tuple(self) -> None:
        result = _resolve_retention_path("")
        assert isinstance(result, tuple)
        assert len(result) == 2


# ── _compact_error ────────────────────────────────────────────────────────────


class TestCompactError:
    def test_simple_exception(self) -> None:
        exc = ValueError("something went wrong")
        result = _compact_error(exc)
        assert "ValueError" in result
        assert "something went wrong" in result

    def test_only_first_line_used(self) -> None:
        exc = RuntimeError("line one\nline two\nline three")
        result = _compact_error(exc)
        assert "line two" not in result

    def test_empty_message_uses_class_name(self) -> None:
        exc = RuntimeError("")
        result = _compact_error(exc)
        assert "RuntimeError" in result

    def test_returns_string(self) -> None:
        assert isinstance(_compact_error(Exception("test")), str)

    def test_format_is_class_colon_message(self) -> None:
        exc = TypeError("bad type")
        result = _compact_error(exc)
        assert result.startswith("TypeError:")
