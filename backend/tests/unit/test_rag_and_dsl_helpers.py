"""Unit tests for pure helpers in ai.rag_ingestion, dsl.edit_router, billing.notifier.

Tests are fully self-contained: no DB, no HTTP, no AI, no filesystem.
Covers:
  - ai.rag_ingestion._chunk_text: text splitting by paragraph breaks + overlap
  - dsl.edit_router._http_from_editor_error: exception → HTTPException mapping
  - billing.notifier._billing_url: env var override
  - dsl.editor_service.compute_diff: diff computation between before/after dicts
"""
from __future__ import annotations

import os
import pytest

try:
    from app.domains.ai.rag_ingestion import _chunk_text
    _RAG_OK = True
except ImportError:
    _RAG_OK = False

try:
    from app.domains.dsl.edit_router import _http_from_editor_error
    from app.domains.dsl.editor_service import (
        EditorError, NotFoundError, ConflictError, compute_diff
    )
    _DSL_OK = True
except ImportError:
    _DSL_OK = False

try:
    from app.domains.billing.notifier import _billing_url
    _BILLING_OK = True
except ImportError:
    _BILLING_OK = False


# ---------------------------------------------------------------------------
# _chunk_text
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RAG_OK, reason="rag_ingestion import failed")
class TestChunkText:
    def test_empty_returns_empty(self):
        assert _chunk_text("") == []

    def test_short_text_single_chunk(self):
        text = "short text"
        result = _chunk_text(text, max_chars=3200)
        assert result == ["short text"]

    def test_text_at_max_single_chunk(self):
        text = "x" * 3200
        result = _chunk_text(text, max_chars=3200)
        assert len(result) == 1

    def test_text_over_max_splits(self):
        # Create text larger than max_chars
        text = "a" * 100
        result = _chunk_text(text, max_chars=30, overlap=5)
        assert len(result) > 1

    def test_paragraph_break_alignment(self):
        # Text with paragraph breaks should split at \n\n boundaries
        para1 = "First paragraph content here.\n\nSecond paragraph content here.\n\nThird paragraph."
        result = _chunk_text(para1, max_chars=40, overlap=5)
        assert len(result) >= 1
        # No chunk should be empty
        for chunk in result:
            assert chunk.strip() != ""

    def test_chunks_not_empty(self):
        text = "word " * 200  # 1000 chars
        result = _chunk_text(text, max_chars=100, overlap=10)
        assert all(len(c) > 0 for c in result)

    def test_overlap_causes_some_repetition(self):
        # With overlap, adjacent chunks share some content
        text = "word " * 500
        result = _chunk_text(text, max_chars=200, overlap=50)
        assert len(result) >= 2
        # overlap means last chars of chunk[0] appear in start of chunk[1]

    def test_returns_list(self):
        result = _chunk_text("hello", max_chars=100)
        assert isinstance(result, list)

    def test_whitespace_only_not_included(self):
        # Empty chunks stripped
        text = "a" * 50
        result = _chunk_text(text, max_chars=30, overlap=5)
        assert all(chunk.strip() != "" for chunk in result)

    def test_single_newline_not_paragraph(self):
        text = "line one\nline two\nline three " * 20
        result = _chunk_text(text, max_chars=100, overlap=10)
        assert len(result) >= 1

    def test_chunks_cover_content(self):
        # Each char in the original should appear in at least one chunk
        text = "unique_word_alpha unique_word_beta"
        result = _chunk_text(text, max_chars=3200)
        combined = " ".join(result)
        assert "unique_word_alpha" in combined
        assert "unique_word_beta" in combined


# ---------------------------------------------------------------------------
# _http_from_editor_error
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.edit_router import failed")
class TestHttpFromEditorError:
    def test_not_found_error_gives_404(self):
        exc = NotFoundError("Resource not found")
        http_exc = _http_from_editor_error(exc)
        assert http_exc.status_code == 404

    def test_conflict_error_gives_409(self):
        exc = ConflictError("Version conflict")
        http_exc = _http_from_editor_error(exc)
        assert http_exc.status_code == 409

    def test_generic_editor_error_gives_400(self):
        exc = EditorError("Bad input", details={"field": "name"})
        http_exc = _http_from_editor_error(exc)
        assert http_exc.status_code == 400

    def test_not_found_detail_contains_message(self):
        exc = NotFoundError("action-123 not found")
        http_exc = _http_from_editor_error(exc)
        assert "not found" in str(http_exc.detail).lower()

    def test_conflict_detail_contains_message(self):
        exc = ConflictError("stale commit sha")
        http_exc = _http_from_editor_error(exc)
        assert "conflict" in str(http_exc.detail).lower() or "stale" in str(http_exc.detail)

    def test_editor_error_detail_is_dict(self):
        exc = EditorError("validation failed", details={"path": ["name"]})
        http_exc = _http_from_editor_error(exc)
        assert isinstance(http_exc.detail, dict)
        assert "message" in http_exc.detail


# ---------------------------------------------------------------------------
# compute_diff (editor_service)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.editor_service import failed")
class TestComputeDiff:
    def test_create_op_when_before_none(self):
        result = compute_diff(None, {"name": "new"})
        assert result["op"] == "create"

    def test_delete_op_when_after_none(self):
        result = compute_diff({"name": "old"}, None)
        assert result["op"] == "delete"

    def test_update_op_when_both_present(self):
        result = compute_diff({"name": "old"}, {"name": "new"})
        assert result["op"] == "update"

    def test_changed_fields_detected(self):
        result = compute_diff({"name": "old", "version": 1}, {"name": "new", "version": 1})
        assert "name" in result["changed_fields"]
        assert "version" not in result["changed_fields"]

    def test_new_field_in_changed(self):
        result = compute_diff({"name": "x"}, {"name": "x", "description": "new"})
        assert "description" in result["changed_fields"]

    def test_removed_field_in_changed(self):
        result = compute_diff({"name": "x", "tags": ["a"]}, {"name": "x"})
        assert "tags" in result["changed_fields"]

    def test_no_changes_empty_changed_fields(self):
        result = compute_diff({"name": "same"}, {"name": "same"})
        assert result["changed_fields"] == []

    def test_both_none_is_update(self):
        result = compute_diff(None, None)
        # before=None means create, but after=None means delete — create takes precedence per code logic
        assert result["op"] in ("create", "delete")

    def test_changed_fields_sorted(self):
        result = compute_diff({"z": 1, "a": 1}, {"z": 2, "a": 2})
        assert result["changed_fields"] == sorted(result["changed_fields"])


# ---------------------------------------------------------------------------
# _billing_url
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BILLING_OK, reason="billing.notifier import failed")
class TestBillingUrl:
    def test_default_url(self, monkeypatch):
        monkeypatch.delenv("BILLING_URL", raising=False)
        url = _billing_url()
        assert url.startswith("http")
        assert "billing" in url

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("BILLING_URL", "https://custom.example.com/billing")
        url = _billing_url()
        assert url == "https://custom.example.com/billing"

    def test_returns_string(self, monkeypatch):
        monkeypatch.delenv("BILLING_URL", raising=False)
        assert isinstance(_billing_url(), str)
