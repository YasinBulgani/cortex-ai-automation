"""Unit tests for AI workflows router pure helper functions.

No DB, no HTTP, no Redis — pure Python only.

Covers:
  app/domains/ai/workflows_router.py:
    _guess_mime, _artifact_metadata, _as_utc
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domains.ai.workflows_router import (
    _artifact_metadata,
    _as_utc,
    _guess_mime,
)


# ── _guess_mime ───────────────────────────────────────────────────────────────


class TestGuessMime:
    def test_html_file(self) -> None:
        assert _guess_mime("report.html") == "text/html"

    def test_htm_file(self) -> None:
        assert _guess_mime("index.htm") == "text/html"

    def test_pdf_file(self) -> None:
        assert _guess_mime("report.pdf") == "application/pdf"

    def test_xml_file(self) -> None:
        assert _guess_mime("data.xml") == "application/xml"

    def test_xlsx_file(self) -> None:
        assert _guess_mime("data.xlsx") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_json_file(self) -> None:
        assert _guess_mime("data.json") == "application/json"

    def test_zip_file(self) -> None:
        assert _guess_mime("archive.zip") == "application/zip"

    def test_gz_file(self) -> None:
        assert _guess_mime("file.gz") == "application/zip"

    def test_unknown_extension(self) -> None:
        assert _guess_mime("file.unknownxyz") == "application/octet-stream"

    def test_no_extension(self) -> None:
        assert _guess_mime("makefile") == "application/octet-stream"

    def test_case_insensitive_extension(self) -> None:
        assert _guess_mime("REPORT.HTML") == "text/html"
        assert _guess_mime("DATA.PDF") == "application/pdf"

    def test_returns_string(self) -> None:
        assert isinstance(_guess_mime("file.txt"), str)

    def test_path_with_directory(self) -> None:
        assert _guess_mime("/tmp/reports/output.json") == "application/json"


# ── _artifact_metadata ────────────────────────────────────────────────────────


class TestArtifactMetadata:
    def test_empty_state_returns_dict(self) -> None:
        result = _artifact_metadata({})
        assert isinstance(result, dict)

    def test_workflow_type_included(self) -> None:
        result = _artifact_metadata({"workflow_type": "test_run"})
        assert result.get("workflow_type") == "test_run"

    def test_dry_run_false_by_default(self) -> None:
        result = _artifact_metadata({})
        # dry_run=False is falsy, so it's excluded from result
        assert "dry_run" not in result or result.get("dry_run") is False

    def test_dry_run_true_included(self) -> None:
        result = _artifact_metadata({"dry_run": True})
        assert result.get("dry_run") is True

    def test_none_values_excluded(self) -> None:
        result = _artifact_metadata({"workflow_type": None})
        assert "workflow_type" not in result

    def test_approval_metadata_included(self) -> None:
        state = {
            "workflow_type": "deploy",
            "approvals": [
                {"approval_id": "a1", "decision": "approved", "actor_id": "user1"}
            ]
        }
        result = _artifact_metadata(state)
        assert result.get("approval_id") == "a1"
        assert result.get("approval_decision") == "approved"

    def test_empty_approvals_list(self) -> None:
        result = _artifact_metadata({"approvals": []})
        assert "approval_id" not in result

    def test_returns_dict(self) -> None:
        result = _artifact_metadata({"workflow_type": "test"})
        assert isinstance(result, dict)


# ── _as_utc ───────────────────────────────────────────────────────────────────


class TestAsUtc:
    def test_naive_datetime_gets_utc(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = _as_utc(dt)
        assert result.tzinfo == timezone.utc

    def test_utc_aware_unchanged(self) -> None:
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _as_utc(dt)
        assert result == dt
        assert result.tzinfo == timezone.utc

    def test_other_timezone_converted_to_utc(self) -> None:
        from datetime import timedelta
        tz_plus2 = timezone(timedelta(hours=2))
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=tz_plus2)
        result = _as_utc(dt)
        assert result.tzinfo == timezone.utc
        # 12:00 +02:00 = 10:00 UTC
        assert result.hour == 10

    def test_returns_datetime(self) -> None:
        dt = datetime(2024, 6, 1, 0, 0, 0)
        result = _as_utc(dt)
        assert isinstance(result, datetime)

    def test_date_preserved(self) -> None:
        dt = datetime(2024, 3, 25, 14, 30, 0)
        result = _as_utc(dt)
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 25
