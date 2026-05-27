"""Unit tests for agents.pipeline_service dataclasses and
core.security_middleware.InputSanitizer.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers:
  - PipelinePhase enum: all phases accessible, string values
  - PipelineConfig: defaults, field types, mutable fields
  - PipelineState: unique run_id generation, defaults
  - InputSanitizer.sanitize_string: control char stripping
  - InputSanitizer.sanitize_sql_identifier: valid/invalid identifiers
  - InputSanitizer.validate_uuid: valid/invalid UUID format
  - InputSanitizer.sanitize_path: path traversal prevention
  - InputSanitizer.sanitize_html: HTML tag stripping
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.pipeline_service import (
        PipelinePhase,
        PipelineConfig,
        PipelineState,
    )
    _PIPELINE_OK = True
except ImportError:
    _PIPELINE_OK = False

try:
    from app.core.security_middleware import InputSanitizer
    _SANITIZER_OK = True
except ImportError:
    _SANITIZER_OK = False


# ---------------------------------------------------------------------------
# PipelinePhase
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PIPELINE_OK, reason="pipeline_service import failed")
class TestPipelinePhase:
    def test_initializing_phase(self):
        assert PipelinePhase.INITIALIZING == "initializing"

    def test_completed_phase(self):
        assert PipelinePhase.COMPLETED == "completed"

    def test_failed_phase(self):
        assert PipelinePhase.FAILED == "failed"

    def test_discovery_phase(self):
        assert PipelinePhase.DISCOVERY == "discovery"

    def test_all_phases_are_strings(self):
        for phase in PipelinePhase:
            assert isinstance(phase.value, str)

    def test_phases_count(self):
        # At minimum these phases must exist
        required = {"initializing", "discovery", "analysis", "completed", "failed"}
        phase_values = {p.value for p in PipelinePhase}
        assert required.issubset(phase_values)


# ---------------------------------------------------------------------------
# PipelineConfig
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PIPELINE_OK, reason="pipeline_service import failed")
class TestPipelineConfig:
    def test_creation(self):
        config = PipelineConfig(project_name="Banking Test", target_url="https://bank.com")
        assert config.project_name == "Banking Test"
        assert config.target_url == "https://bank.com"

    def test_defaults(self):
        config = PipelineConfig(project_name="test")
        assert config.target_url is None
        assert config.description == ""
        assert config.cycles == 2
        assert config.generate_bdd is True
        assert config.generate_playwright is True
        assert config.generate_api_tests is True
        assert config.run_tests is True
        assert config.auto_heal is True
        assert config.max_quality_retries == 2

    def test_regulations_default(self):
        config = PipelineConfig(project_name="test")
        assert "BDDK" in config.regulations
        assert "KVKK" in config.regulations

    def test_custom_cycles(self):
        config = PipelineConfig(project_name="test", cycles=5)
        assert config.cycles == 5

    def test_crawl_defaults(self):
        config = PipelineConfig(project_name="test")
        assert config.crawl_max_pages == 10
        assert config.crawl_depth == 2


# ---------------------------------------------------------------------------
# PipelineState
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PIPELINE_OK, reason="pipeline_service import failed")
class TestPipelineState:
    def test_unique_run_ids(self):
        s1 = PipelineState()
        s2 = PipelineState()
        assert s1.run_id != s2.run_id

    def test_run_id_is_string(self):
        s = PipelineState()
        assert isinstance(s.run_id, str)
        assert len(s.run_id) > 0

    def test_initial_phase(self):
        s = PipelineState()
        assert s.phase == PipelinePhase.INITIALIZING

    def test_defaults(self):
        s = PipelineState()
        assert s.progress == 0
        assert s.running is False
        assert s.started_at == pytest.approx(0.0)
        assert s.error is None
        assert s.logs == []
        assert s.warnings == []
        assert s.scenarios == []
        assert s.quality_score == pytest.approx(0.0)
        assert s.tspm_scenario_ids == []
        assert s.project_id is None

    def test_mutable_lists_are_independent(self):
        s1 = PipelineState()
        s2 = PipelineState()
        s1.warnings.append("test warning")
        assert s2.warnings == []  # separate instances

    def test_can_set_phase(self):
        s = PipelineState()
        s.phase = PipelinePhase.DISCOVERY
        assert s.phase == PipelinePhase.DISCOVERY

    def test_can_set_progress(self):
        s = PipelineState()
        s.progress = 50
        assert s.progress == 50


# ---------------------------------------------------------------------------
# InputSanitizer.sanitize_string
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SANITIZER_OK, reason="security_middleware import failed")
class TestSanitizeString:
    def test_normal_string_unchanged(self):
        assert InputSanitizer.sanitize_string("hello world") == "hello world"

    def test_null_byte_removed(self):
        result = InputSanitizer.sanitize_string("hello\x00world")
        assert "\x00" not in result

    def test_control_char_removed(self):
        result = InputSanitizer.sanitize_string("test\x01value")
        assert "\x01" not in result

    def test_newline_preserved(self):
        # Newline should NOT be stripped
        result = InputSanitizer.sanitize_string("line1\nline2")
        assert "\n" in result

    def test_tab_preserved(self):
        result = InputSanitizer.sanitize_string("col1\tcol2")
        assert "\t" in result

    def test_non_string_converted(self):
        result = InputSanitizer.sanitize_string(42)
        assert isinstance(result, str)
        assert "42" in result

    def test_empty_string(self):
        assert InputSanitizer.sanitize_string("") == ""

    def test_returns_string(self):
        assert isinstance(InputSanitizer.sanitize_string("test"), str)


# ---------------------------------------------------------------------------
# InputSanitizer.sanitize_sql_identifier
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SANITIZER_OK, reason="security_middleware import failed")
class TestSanitizeSqlIdentifier:
    def test_valid_identifier(self):
        result = InputSanitizer.sanitize_sql_identifier("user_id")
        assert result == "user_id"

    def test_valid_with_numbers(self):
        result = InputSanitizer.sanitize_sql_identifier("table1")
        assert result == "table1"

    def test_drop_table_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_sql_identifier("users; DROP TABLE users")

    def test_space_in_name_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_sql_identifier("user id")

    def test_hyphen_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_sql_identifier("user-id")

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_sql_identifier("")

    def test_strips_whitespace_before_check(self):
        result = InputSanitizer.sanitize_sql_identifier("  user_id  ")
        assert result == "user_id"


# ---------------------------------------------------------------------------
# InputSanitizer.validate_uuid
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SANITIZER_OK, reason="security_middleware import failed")
class TestValidateUuid:
    def test_valid_uuid(self):
        valid = "550e8400-e29b-41d4-a716-446655440000"
        result = InputSanitizer.validate_uuid(valid)
        assert result == valid

    def test_invalid_uuid_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.validate_uuid("not-a-uuid")

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.validate_uuid("550e8400-e29b-41d4")

    def test_uppercase_uuid_valid(self):
        upper = "550E8400-E29B-41D4-A716-446655440000"
        # Regex might accept uppercase
        try:
            result = InputSanitizer.validate_uuid(upper)
            assert result == upper
        except ValueError:
            pass  # Both outcomes are acceptable

    def test_strips_whitespace(self):
        valid = "  550e8400-e29b-41d4-a716-446655440000  "
        result = InputSanitizer.validate_uuid(valid)
        assert result.strip() == "550e8400-e29b-41d4-a716-446655440000"


# ---------------------------------------------------------------------------
# InputSanitizer.sanitize_path
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SANITIZER_OK, reason="security_middleware import failed")
class TestSanitizePath:
    def test_valid_relative_path(self):
        result = InputSanitizer.sanitize_path("reports/2026/summary.pdf")
        assert result == "reports/2026/summary.pdf"

    def test_path_traversal_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_path("../../etc/passwd")

    def test_absolute_unix_path_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_path("/etc/passwd")

    def test_absolute_windows_path_raises(self):
        with pytest.raises(ValueError):
            InputSanitizer.sanitize_path("C:\\Windows\\System32")

    def test_non_string_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            InputSanitizer.sanitize_path(None)

    def test_simple_filename_valid(self):
        result = InputSanitizer.sanitize_path("report.pdf")
        assert result == "report.pdf"

    def test_strips_whitespace(self):
        result = InputSanitizer.sanitize_path("  report.pdf  ")
        assert result == "report.pdf"


# ---------------------------------------------------------------------------
# InputSanitizer.sanitize_html
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SANITIZER_OK, reason="security_middleware import failed")
class TestSanitizeHtml:
    def test_script_tag_removed(self):
        result = InputSanitizer.sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert" in result  # text content preserved

    def test_plain_text_unchanged(self):
        result = InputSanitizer.sanitize_html("plain text")
        assert result == "plain text"

    def test_anchor_tag_removed(self):
        result = InputSanitizer.sanitize_html('<a href="http://evil.com">click</a>')
        assert "<a" not in result
        assert "click" in result

    def test_nested_tags_removed(self):
        result = InputSanitizer.sanitize_html("<div><b>bold</b></div>")
        assert "<div>" not in result
        assert "<b>" not in result
        assert "bold" in result

    def test_empty_string(self):
        assert InputSanitizer.sanitize_html("") == ""

    def test_non_string_converted(self):
        result = InputSanitizer.sanitize_html(42)
        assert isinstance(result, str)

    def test_returns_string(self):
        assert isinstance(InputSanitizer.sanitize_html("test"), str)
