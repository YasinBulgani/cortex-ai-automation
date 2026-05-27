"""Unit tests for agents.v2.run_store pure helper functions and dataclasses.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _uuid_or_none: UUID coercion
  - _jsonable: JSON round-trip serialisation
  - _artifact_metadata_with_integrity: file-integrity metadata (tmp_path)
  - _sha256_file: SHA-256 digest for file
  - _record_workflow_* helpers: graceful no-op when metrics absent
  - RunArtifact.to_dict: dataclass → dict serialisation
  - RunRecord.to_status_dict: run record → status summary dict
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    from app.domains.agents.v2.run_store import (
        _uuid_or_none,
        _jsonable,
        _artifact_metadata_with_integrity,
        _sha256_file,
        _record_workflow_status,
        _record_workflow_event,
        _record_workflow_approval,
        _record_workflow_dead_letter,
        RunArtifact,
        RunRecord,
    )
    _RS_OK = True
except ImportError:
    _RS_OK = False


# ---------------------------------------------------------------------------
# _uuid_or_none
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestUuidOrNone:
    def test_valid_uuid_string(self):
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = _uuid_or_none(uid)
        assert result == uid

    def test_valid_uuid_no_hyphens(self):
        # UUID without hyphens should still work via UUID()
        uid_no_hyphens = "550e8400e29b41d4a716446655440000"
        result = _uuid_or_none(uid_no_hyphens)
        assert result is not None
        assert "-" in result  # normalised form has hyphens

    def test_none_returns_none(self):
        assert _uuid_or_none(None) is None

    def test_invalid_string_returns_none(self):
        assert _uuid_or_none("not-a-uuid") is None

    def test_empty_string_returns_none(self):
        assert _uuid_or_none("") is None

    def test_random_string_returns_none(self):
        assert _uuid_or_none("hello world") is None

    def test_numeric_garbage_returns_none(self):
        assert _uuid_or_none(12345) is None

    def test_returns_string_type(self):
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = _uuid_or_none(uid)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _jsonable
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestJsonable:
    def test_none_returns_none(self):
        assert _jsonable(None) is None

    def test_dict_passthrough(self):
        d = {"key": "value", "num": 42}
        result = _jsonable(d)
        assert result == d

    def test_list_passthrough(self):
        lst = [1, 2, 3]
        assert _jsonable(lst) == lst

    def test_string_passthrough(self):
        assert _jsonable("hello") == "hello"

    def test_int_passthrough(self):
        assert _jsonable(42) == 42

    def test_float_passthrough(self):
        assert _jsonable(3.14) == pytest.approx(3.14)

    def test_datetime_becomes_string(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = _jsonable(dt)
        assert isinstance(result, str)
        assert "2024" in result

    def test_nested_dict_with_datetime(self):
        data = {"ts": datetime(2024, 1, 1), "val": 99}
        result = _jsonable(data)
        assert isinstance(result["ts"], str)
        assert result["val"] == 99

    def test_result_is_json_serialisable(self):
        data = {"nested": {"key": [1, 2, datetime(2024, 1, 1)]}}
        result = _jsonable(data)
        # Should not raise
        json.dumps(result)

    def test_returns_new_object(self):
        d = {"k": "v"}
        result = _jsonable(d)
        d["extra"] = "added"
        assert "extra" not in result


# ---------------------------------------------------------------------------
# _sha256_file
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestSha256File:
    def test_known_content(self, tmp_path):
        f = tmp_path / "test.txt"
        content = b"hello world"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert _sha256_file(f) == expected

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert _sha256_file(f) == expected

    def test_binary_content(self, tmp_path):
        f = tmp_path / "binary.bin"
        content = bytes(range(256))
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert _sha256_file(f) == expected

    def test_returns_64_char_hex(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"data")
        result = _sha256_file(f)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_files_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert _sha256_file(f1) != _sha256_file(f2)

    def test_same_content_same_hash(self, tmp_path):
        f1 = tmp_path / "c1.txt"
        f2 = tmp_path / "c2.txt"
        f1.write_bytes(b"same")
        f2.write_bytes(b"same")
        assert _sha256_file(f1) == _sha256_file(f2)


# ---------------------------------------------------------------------------
# _artifact_metadata_with_integrity
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestArtifactMetadataWithIntegrity:
    def test_http_url_returns_metadata_unchanged(self):
        result = _artifact_metadata_with_integrity(
            "http://example.com/file.png", 100, {"key": "val"}
        )
        assert result == {"key": "val"}
        assert "sha256" not in result

    def test_https_url_returns_metadata_unchanged(self):
        result = _artifact_metadata_with_integrity(
            "https://cdn.example.com/asset.js", 0, {}
        )
        assert "sha256" not in result

    def test_nonexistent_file_returns_metadata_unchanged(self):
        result = _artifact_metadata_with_integrity(
            "/nonexistent/path/to/file.txt", 0, {"tag": "x"}
        )
        assert result == {"tag": "x"}

    def test_existing_file_gets_sha256(self, tmp_path):
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"artifact content")
        result = _artifact_metadata_with_integrity(str(f), f.stat().st_size, {})
        assert "sha256" in result
        assert len(result["sha256"]) == 64

    def test_existing_file_gets_hash_algorithm(self, tmp_path):
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"data")
        result = _artifact_metadata_with_integrity(str(f), 0, {})
        assert result.get("hash_algorithm") == "sha256"

    def test_existing_file_gets_size_verified(self, tmp_path):
        f = tmp_path / "artifact.bin"
        content = b"test data"
        f.write_bytes(content)
        result = _artifact_metadata_with_integrity(str(f), len(content), {})
        assert result.get("size_bytes_verified") == len(content)

    def test_size_mismatch_records_discrepancy(self, tmp_path):
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"1234567890")  # 10 bytes
        result = _artifact_metadata_with_integrity(str(f), 99, {})
        assert "size_bytes_mismatch" in result
        mismatch = result["size_bytes_mismatch"]
        assert mismatch["declared"] == 99
        assert mismatch["actual"] == 10

    def test_none_metadata_treated_as_empty(self, tmp_path):
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"x")
        result = _artifact_metadata_with_integrity(str(f), 1, None)
        assert isinstance(result, dict)
        assert "sha256" in result

    def test_existing_metadata_preserved(self, tmp_path):
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"data")
        result = _artifact_metadata_with_integrity(str(f), 4, {"custom": "preserved"})
        assert result["custom"] == "preserved"

    def test_existing_sha256_not_overwritten(self, tmp_path):
        f = tmp_path / "artifact.bin"
        f.write_bytes(b"data")
        result = _artifact_metadata_with_integrity(
            str(f), 4, {"sha256": "pre-existing-hash"}
        )
        # setdefault means pre-existing value is kept
        assert result["sha256"] == "pre-existing-hash"


# ---------------------------------------------------------------------------
# _record_workflow_* (graceful no-op when metrics unavailable)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestRecordWorkflowHelpers:
    """These functions call optional metrics and swallow any exception.
    They must never raise, regardless of whether metrics are installed."""

    def test_record_workflow_status_does_not_raise(self):
        _record_workflow_status("automation", "completed")
        _record_workflow_status(None, "failed")
        _record_workflow_status("", "running")

    def test_record_workflow_event_does_not_raise(self):
        _record_workflow_event("step_start")
        _record_workflow_event(None)
        _record_workflow_event("")

    def test_record_workflow_approval_does_not_raise(self):
        _record_workflow_approval("approved")
        _record_workflow_approval("rejected")
        _record_workflow_approval("")

    def test_record_workflow_dead_letter_does_not_raise(self):
        _record_workflow_dead_letter("main_queue", "timeout")
        _record_workflow_dead_letter("", "unknown")

    def test_record_workflow_status_returns_none(self):
        result = _record_workflow_status("t", "s")
        assert result is None

    def test_record_workflow_event_returns_none(self):
        result = _record_workflow_event("evt")
        assert result is None

    def test_record_workflow_approval_returns_none(self):
        result = _record_workflow_approval("ok")
        assert result is None

    def test_record_workflow_dead_letter_returns_none(self):
        result = _record_workflow_dead_letter("q", "r")
        assert result is None


# ---------------------------------------------------------------------------
# RunArtifact.to_dict
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestRunArtifactToDict:
    def _make_artifact(self, **kwargs):
        defaults = {
            "artifact_id": "art-001",
            "kind": "screenshot",
            "name": "shot.png",
            "storage_path": "/tmp/shot.png",
        }
        defaults.update(kwargs)
        return RunArtifact(**defaults)

    def test_all_keys_present(self):
        d = self._make_artifact().to_dict()
        expected_keys = {
            "artifact_id", "kind", "name", "storage_path",
            "mime_type", "size_bytes", "created_at", "metadata",
        }
        assert set(d.keys()) == expected_keys

    def test_artifact_id_value(self):
        d = self._make_artifact(artifact_id="my-id").to_dict()
        assert d["artifact_id"] == "my-id"

    def test_kind_value(self):
        d = self._make_artifact(kind="report").to_dict()
        assert d["kind"] == "report"

    def test_default_mime_type(self):
        d = self._make_artifact().to_dict()
        assert d["mime_type"] == "application/octet-stream"

    def test_custom_mime_type(self):
        d = self._make_artifact(mime_type="image/png").to_dict()
        assert d["mime_type"] == "image/png"

    def test_default_size_bytes(self):
        d = self._make_artifact().to_dict()
        assert d["size_bytes"] == 0

    def test_custom_size_bytes(self):
        d = self._make_artifact(size_bytes=2048).to_dict()
        assert d["size_bytes"] == 2048

    def test_metadata_default_empty(self):
        d = self._make_artifact().to_dict()
        assert d["metadata"] == {}

    def test_metadata_custom(self):
        meta = {"tag": "production", "version": 3}
        d = self._make_artifact(metadata=meta).to_dict()
        assert d["metadata"] == meta

    def test_created_at_is_datetime(self):
        d = self._make_artifact().to_dict()
        assert isinstance(d["created_at"], datetime)


# ---------------------------------------------------------------------------
# RunRecord.to_status_dict
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _RS_OK, reason="run_store import failed")
class TestRunRecordToStatusDict:
    def _make_record(self, **kwargs):
        defaults = {
            "run_id": "run-001",
            "project_id": "proj-001",
            "tenant_id": "tenant-001",
            "user_id": "user-001",
            "input_source": "api",
        }
        defaults.update(kwargs)
        return RunRecord(**defaults)

    def test_all_keys_present(self):
        d = self._make_record().to_status_dict()
        expected_keys = {
            "run_id", "project_id", "status", "input_source",
            "created_at", "completed_at", "error", "event_count",
            "artifact_count", "approval_count", "cost_usd",
            "tokens_used", "llm_calls_count", "errors",
            "intent_graph", "app_map", "scenarios",
            "generated_code", "run_result", "healing_result",
            "review", "report",
        }
        assert set(d.keys()) == expected_keys

    def test_default_status_queued(self):
        d = self._make_record().to_status_dict()
        assert d["status"] == "queued"

    def test_custom_status(self):
        d = self._make_record(status="running").to_status_dict()
        assert d["status"] == "running"

    def test_run_id(self):
        d = self._make_record(run_id="r-xyz").to_status_dict()
        assert d["run_id"] == "r-xyz"

    def test_project_id(self):
        d = self._make_record(project_id="p-abc").to_status_dict()
        assert d["project_id"] == "p-abc"

    def test_event_count_default_zero(self):
        d = self._make_record().to_status_dict()
        assert d["event_count"] == 0

    def test_artifact_count_default_zero(self):
        d = self._make_record().to_status_dict()
        assert d["artifact_count"] == 0

    def test_approval_count_default_zero(self):
        d = self._make_record().to_status_dict()
        assert d["approval_count"] == 0

    def test_cost_usd_default_zero(self):
        d = self._make_record().to_status_dict()
        assert d["cost_usd"] == pytest.approx(0.0)

    def test_tokens_used_default_zero(self):
        d = self._make_record().to_status_dict()
        assert d["tokens_used"] == 0

    def test_llm_calls_count_default_zero(self):
        d = self._make_record().to_status_dict()
        assert d["llm_calls_count"] == 0

    def test_errors_default_empty_list(self):
        d = self._make_record().to_status_dict()
        assert d["errors"] == []

    def test_scenarios_default_empty_list(self):
        d = self._make_record().to_status_dict()
        assert d["scenarios"] == []

    def test_completed_at_default_none(self):
        d = self._make_record().to_status_dict()
        assert d["completed_at"] is None

    def test_error_default_none(self):
        d = self._make_record().to_status_dict()
        assert d["error"] is None

    def test_intent_graph_default_none(self):
        d = self._make_record().to_status_dict()
        assert d["intent_graph"] is None

    def test_state_cost_reflected(self):
        record = self._make_record()
        record.state = {"cost_usd": 1.23, "tokens_used": 500, "llm_calls_count": 3}
        d = record.to_status_dict()
        assert d["cost_usd"] == pytest.approx(1.23)
        assert d["tokens_used"] == 500
        assert d["llm_calls_count"] == 3

    def test_state_scenarios_reflected(self):
        record = self._make_record()
        record.state = {"scenarios": ["s1", "s2"]}
        d = record.to_status_dict()
        assert d["scenarios"] == ["s1", "s2"]

    def test_event_count_matches_events_list(self):
        record = self._make_record()
        record.events = [{"type": "step"}, {"type": "done"}]
        d = record.to_status_dict()
        assert d["event_count"] == 2

    def test_artifact_count_matches_artifacts_list(self):
        record = self._make_record()
        record.artifacts = [
            RunArtifact(
                artifact_id="a1", kind="s", name="n", storage_path="/tmp/x"
            )
        ]
        d = record.to_status_dict()
        assert d["artifact_count"] == 1
