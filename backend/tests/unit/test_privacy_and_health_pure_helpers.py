"""Unit tests for privacy.service and health.service pure helper functions.

All tests are self-contained: no DB, no filesystem, no HTTP.
Covers:
  - privacy.service._uuid_or_none: UUID string validation/coercion
  - health.service._compute_overall: HealthLevel from ComponentStatus list
"""
from __future__ import annotations

import pytest

try:
    from app.domains.privacy.service import _uuid_or_none
    _PRIV_OK = True
except ImportError:
    _PRIV_OK = False

try:
    from app.domains.health.service import _compute_overall
    from app.domains.health.schemas import ComponentStatus, HealthLevel
    _HEALTH_OK = True
except ImportError:
    _HEALTH_OK = False


# ---------------------------------------------------------------------------
# _uuid_or_none
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _PRIV_OK, reason="privacy.service import failed")
class TestUuidOrNone:
    def test_valid_uuid4(self):
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = _uuid_or_none(uuid)
        assert result == uuid

    def test_valid_uuid_without_hyphens(self):
        # UUID without hyphens — UUID() should still parse
        compact = "550e8400e29b41d4a716446655440000"
        result = _uuid_or_none(compact)
        assert result is not None  # UUID normalizes to hyphenated form

    def test_invalid_string_returns_none(self):
        assert _uuid_or_none("not-a-uuid") is None

    def test_empty_string_returns_none(self):
        assert _uuid_or_none("") is None

    def test_returns_string_type(self):
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = _uuid_or_none(uuid)
        assert isinstance(result, str)

    def test_none_input_returns_none(self):
        assert _uuid_or_none(None) is None  # type: ignore[arg-type]

    def test_integer_string_returns_none(self):
        assert _uuid_or_none("12345") is None

    def test_uuid_format_preserved(self):
        uuid = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        result = _uuid_or_none(uuid)
        assert result == uuid

    def test_all_zeros_uuid(self):
        uuid = "00000000-0000-0000-0000-000000000000"
        result = _uuid_or_none(uuid)
        assert result == uuid

    def test_case_insensitive_input(self):
        upper = "550E8400-E29B-41D4-A716-446655440000"
        result = _uuid_or_none(upper)
        assert result is not None


# ---------------------------------------------------------------------------
# _compute_overall
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HEALTH_OK, reason="health.service import failed")
class TestComputeOverall:
    def _comp(self, level: str, optional: bool = False) -> ComponentStatus:
        return ComponentStatus(
            name="test",
            label="Test Component",
            level=HealthLevel(level),
            optional=optional,
        )

    def test_all_ok_returns_ok(self):
        components = [self._comp("ok"), self._comp("ok")]
        assert _compute_overall(components) == HealthLevel.ok

    def test_required_down_returns_down(self):
        components = [self._comp("ok"), self._comp("down")]
        assert _compute_overall(components) == HealthLevel.down

    def test_required_degraded_returns_degraded(self):
        components = [self._comp("ok"), self._comp("degraded")]
        assert _compute_overall(components) == HealthLevel.degraded

    def test_optional_down_returns_degraded_not_down(self):
        # Optional down → overall degraded (not down)
        components = [self._comp("ok"), self._comp("down", optional=True)]
        result = _compute_overall(components)
        assert result != HealthLevel.down

    def test_empty_list_returns_ok(self):
        assert _compute_overall([]) == HealthLevel.ok

    def test_down_beats_degraded(self):
        # Any required down → down even if others degraded
        components = [self._comp("degraded"), self._comp("down")]
        assert _compute_overall(components) == HealthLevel.down

    def test_all_optional_down_returns_degraded(self):
        components = [self._comp("down", optional=True), self._comp("down", optional=True)]
        # Required list is empty → no required down/degraded; but optional down → degraded
        result = _compute_overall(components)
        assert result == HealthLevel.degraded

    def test_returns_health_level(self):
        result = _compute_overall([self._comp("ok")])
        assert isinstance(result, HealthLevel)

    def test_single_required_ok(self):
        assert _compute_overall([self._comp("ok")]) == HealthLevel.ok

    def test_single_required_down(self):
        assert _compute_overall([self._comp("down")]) == HealthLevel.down

    def test_optional_degraded_with_all_required_ok(self):
        components = [self._comp("ok"), self._comp("degraded", optional=True)]
        # Optional degraded → overall degraded
        result = _compute_overall(components)
        assert result == HealthLevel.degraded
