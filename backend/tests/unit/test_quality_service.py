"""Unit tests for app.domains.quality.service.

All filesystem I/O is mocked — no actual files are read.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.quality import service as quality_service
    from app.domains.quality.service import (
        EvalSnapshot,
        EvalSnapshotModel,
        QualityMetrics,
        parse_eval_report,
        get_quality_metrics,
        _read_latest_report,
        _read_history,
        _to_float,
        _to_int,
        _first_match,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="quality service import failed")

from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


# ---------------------------------------------------------------------------
# EvalSnapshot — dataclass defaults
# ---------------------------------------------------------------------------

class TestEvalSnapshotDefaults:
    def test_default_available_is_false(self):
        snap = EvalSnapshot()
        assert snap.available is False

    def test_all_optional_fields_are_none_by_default(self):
        snap = EvalSnapshot()
        for field in (
            "mode", "mapping_accuracy_pct", "value_preservation_pct",
            "unknown_rate_pct", "gherkin_valid_pct", "p95_latency_ms",
            "total_fixtures", "total_steps", "llm_errors", "generated_at",
        ):
            assert getattr(snap, field) is None, f"{field} should default to None"

    def test_available_true_can_be_set(self):
        snap = EvalSnapshot(available=True, mode="grounding-only")
        assert snap.available is True
        assert snap.mode == "grounding-only"


# ---------------------------------------------------------------------------
# Helper converters
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_to_float_parses_percentage(self):
        assert _to_float("86.4%") == pytest.approx(86.4)

    def test_to_float_comma_decimal(self):
        assert _to_float("86,4") == pytest.approx(86.4)

    def test_to_float_none_returns_none(self):
        assert _to_float(None) is None

    def test_to_float_invalid_returns_none(self):
        assert _to_float("not-a-number") is None

    def test_to_int_parses_plain_int(self):
        assert _to_int("22") == 22

    def test_to_int_none_returns_none(self):
        assert _to_int(None) is None

    def test_first_match_found(self):
        text = "Eval Report — 2026-04-19T06:53:31+00:00"
        result = _first_match(text, r"Eval Report\s*[—-]?\s*([\dT:+\-.]+)")
        assert result == "2026-04-19T06:53:31+00:00"

    def test_first_match_not_found_returns_none(self):
        assert _first_match("no match here", r"(NOMATCH)") is None


# ---------------------------------------------------------------------------
# parse_eval_report — markdown parsing
# ---------------------------------------------------------------------------

_SAMPLE_MD = """\
# BGTest Eval Report — 2026-04-19T06:53:31+00:00

**Mod:** `grounding-only`

| Metrik | Değer |
|---|---|
| Fixture sayısı | 5 |
| Toplam adım | 22 |
| **Mapping accuracy** | 86.4% |
| Unknown rate | 13.6% |
| Value preservation | 100.0% |
| p95 latency | 44 ms |
| LLM hatası | 0 |
"""


class TestParseEvalReport:
    def test_available_true_after_parse(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.available is True

    def test_mode_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.mode == "grounding-only"

    def test_mapping_accuracy_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.mapping_accuracy_pct == pytest.approx(86.4)

    def test_unknown_rate_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.unknown_rate_pct == pytest.approx(13.6)

    def test_value_preservation_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.value_preservation_pct == pytest.approx(100.0)

    def test_p95_latency_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.p95_latency_ms == 44

    def test_total_fixtures_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.total_fixtures == 5

    def test_total_steps_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.total_steps == 22

    def test_llm_errors_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.llm_errors == 0

    def test_timestamp_parsed(self):
        snap = parse_eval_report(_SAMPLE_MD)
        assert snap.generated_at is not None
        assert "2026" in snap.generated_at

    def test_empty_text_returns_available_true_with_none_fields(self):
        """Even with no matching content, parse returns available=True (graceful)."""
        snap = parse_eval_report("no metrics here")
        assert snap.available is True
        assert snap.mapping_accuracy_pct is None


# ---------------------------------------------------------------------------
# _read_latest_report — filesystem interactions
# ---------------------------------------------------------------------------

class TestReadLatestReport:
    def test_no_file_returns_unavailable(self):
        """When latest.md does not exist, returns EvalSnapshot(available=False)."""
        mock_dir = MagicMock(spec=Path)
        mock_latest = MagicMock(spec=Path)
        mock_latest.is_file.return_value = False
        mock_dir.__truediv__ = lambda self, other: mock_latest

        result = _read_latest_report(mock_dir)
        assert result.available is False

    def test_valid_file_returns_available(self):
        """When latest.md exists and is readable, returns available=True snapshot."""
        mock_dir = MagicMock(spec=Path)
        mock_latest = MagicMock(spec=Path)
        mock_latest.is_file.return_value = True
        mock_latest.read_text.return_value = _SAMPLE_MD
        mock_dir.__truediv__ = lambda self, other: mock_latest

        result = _read_latest_report(mock_dir)
        assert result.available is True
        assert result.mapping_accuracy_pct == pytest.approx(86.4)

    def test_os_error_returns_unavailable(self):
        """OSError during read_text returns EvalSnapshot(available=False)."""
        mock_dir = MagicMock(spec=Path)
        mock_latest = MagicMock(spec=Path)
        mock_latest.is_file.return_value = True
        mock_latest.read_text.side_effect = OSError("permission denied")
        mock_dir.__truediv__ = lambda self, other: mock_latest

        result = _read_latest_report(mock_dir)
        assert result.available is False


# ---------------------------------------------------------------------------
# _read_history
# ---------------------------------------------------------------------------

class TestReadHistory:
    def test_no_history_dir_returns_empty_list(self):
        mock_dir = MagicMock(spec=Path)
        mock_history = MagicMock(spec=Path)
        mock_history.is_dir.return_value = False
        mock_dir.__truediv__ = lambda self, other: mock_history

        result = _read_history(mock_dir)
        assert result == []

    def test_multiple_files_returns_multiple_snapshots(self):
        mock_dir = MagicMock(spec=Path)
        mock_history = MagicMock(spec=Path)
        mock_history.is_dir.return_value = True

        # Create two fake file mocks
        def make_file(mtime: float):
            f = MagicMock(spec=Path)
            f.is_file.return_value = True
            f.read_text.return_value = _SAMPLE_MD
            f.stat.return_value = MagicMock(st_mtime=mtime)
            f.suffix = ".md"
            return f

        file1 = make_file(1000.0)
        file2 = make_file(2000.0)
        mock_history.glob.return_value = [file1, file2]
        mock_dir.__truediv__ = lambda self, other: mock_history

        result = _read_history(mock_dir, limit=10)
        assert len(result) == 2
        assert all(isinstance(s, EvalSnapshot) for s in result)


# ---------------------------------------------------------------------------
# EvalSnapshotModel — Pydantic model
# ---------------------------------------------------------------------------

class TestEvalSnapshotModel:
    def test_valid_model_construction(self):
        model = EvalSnapshotModel(
            available=True,
            mode="full-v2",
            mapping_accuracy_pct=91.5,
        )
        assert model.available is True
        assert model.mode == "full-v2"
        assert model.mapping_accuracy_pct == pytest.approx(91.5)

    def test_defaults_are_false_and_none(self):
        model = EvalSnapshotModel()
        assert model.available is False
        assert model.mode is None
        assert model.mapping_accuracy_pct is None

    def test_extra_fields_ignored(self):
        """extra='ignore' — unknown fields should not raise."""
        model = EvalSnapshotModel(available=True, unknown_field="x")
        assert model.available is True


# ---------------------------------------------------------------------------
# get_quality_metrics — integration (all IO mocked)
# ---------------------------------------------------------------------------

class TestGetQualityMetrics:
    def test_returns_quality_metrics_object(self, tmp_path):
        """With a real temp directory and no files, returns unavailable latest."""
        result = get_quality_metrics(reports_dir=tmp_path)
        assert isinstance(result, QualityMetrics)
        assert result.latest_eval.available is False
        assert result.history == []

    def test_with_latest_file_returns_available(self, tmp_path):
        """With a latest.md present, latest_eval.available is True."""
        (tmp_path / "latest.md").write_text(_SAMPLE_MD, encoding="utf-8")
        result = get_quality_metrics(reports_dir=tmp_path)
        assert result.latest_eval.available is True
        assert result.latest_eval.mode == "grounding-only"
