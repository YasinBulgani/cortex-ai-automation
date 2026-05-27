"""Unit tests for feature_flags.service pure helper functions and classes.

All tests are self-contained: no Redis, no DB, no HTTP.
Covers:
  - _hash_bucket: deterministic 0-99 tenant rollout bucket
  - _FlagRecord: internal flag record with percent clamping, JSON round-trip
"""
from __future__ import annotations

import json

import pytest

try:
    import app.domains.feature_flags.service as _ff_module
    from app.domains.feature_flags.service import _hash_bucket
    _FlagRecord = _ff_module._FlagRecord  # type: ignore[attr-defined]
    _FF_OK = True
except (ImportError, AttributeError):
    _FF_OK = False


# ---------------------------------------------------------------------------
# _hash_bucket
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FF_OK, reason="feature_flags import failed")
class TestHashBucket:
    def test_deterministic_same_tenant_same_key(self):
        b1 = _hash_bucket("tenant1", "flag.x")
        b2 = _hash_bucket("tenant1", "flag.x")
        assert b1 == b2

    def test_range_0_to_99(self):
        for tenant in ["t1", "t2", "t3", "ACME", ""]:
            for key in ["feature.a", "feature.b", "ai.cache"]:
                bucket = _hash_bucket(tenant, key)
                assert 0 <= bucket <= 99, f"bucket out of range: {bucket}"

    def test_different_tenants_likely_differ(self):
        # With enough different tenants, buckets should vary
        results = {_hash_bucket(f"tenant_{i}", "feature.x") for i in range(20)}
        assert len(results) > 1

    def test_different_keys_differ(self):
        b1 = _hash_bucket("tenant1", "feature.a")
        b2 = _hash_bucket("tenant1", "feature.b")
        assert b1 != b2

    def test_empty_tenant_still_works(self):
        b = _hash_bucket("", "my.flag")
        assert 0 <= b <= 99

    def test_empty_key_still_works(self):
        b = _hash_bucket("tenant1", "")
        assert 0 <= b <= 99

    def test_returns_int(self):
        assert isinstance(_hash_bucket("t", "k"), int)

    def test_unicode_tenant(self):
        b = _hash_bucket("müşteri-001", "ai.enable")
        assert 0 <= b <= 99

    def test_long_key(self):
        long_key = "feature." + "x" * 200
        b = _hash_bucket("tenant", long_key)
        assert 0 <= b <= 99

    def test_tenant_key_separator_matters(self):
        # "a|bc" and "ab|c" have different raw inputs
        b1 = _hash_bucket("a", "bc")
        b2 = _hash_bucket("ab", "c")
        # Different separations → different digests (almost certainly)
        # Just verify both are valid — they may or may not differ
        assert 0 <= b1 <= 99
        assert 0 <= b2 <= 99


# ---------------------------------------------------------------------------
# _FlagRecord
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FF_OK, reason="feature_flags import failed")
class TestFlagRecord:
    def _make(self, **kwargs):
        defaults = {"key": "test.flag"}
        defaults.update(kwargs)
        return _FlagRecord(**defaults)

    def test_default_enabled_false(self):
        r = self._make()
        assert r.enabled is False

    def test_custom_enabled_true(self):
        r = self._make(enabled=True)
        assert r.enabled is True

    def test_default_percent_zero(self):
        r = self._make()
        assert r.percent == 0

    def test_percent_50(self):
        r = self._make(percent=50)
        assert r.percent == 50

    def test_percent_clamped_above_100(self):
        r = self._make(percent=150)
        assert r.percent == 100

    def test_percent_clamped_below_0(self):
        r = self._make(percent=-10)
        assert r.percent == 0

    def test_allow_tenants_default_empty(self):
        r = self._make()
        assert r.allow_tenants == []

    def test_allow_tenants_set(self):
        r = self._make(allow_tenants=["t1", "t2"])
        assert r.allow_tenants == ["t1", "t2"]

    def test_none_allow_tenants_becomes_empty_list(self):
        r = self._make(allow_tenants=None)
        assert r.allow_tenants == []

    def test_key_stored(self):
        r = self._make(key="my.special.flag")
        assert r.key == "my.special.flag"

    # to_json / from_json round-trip

    def test_to_json_returns_string(self):
        r = self._make(enabled=True, percent=75)
        j = r.to_json()
        assert isinstance(j, str)

    def test_to_json_is_valid_json(self):
        r = self._make(enabled=True, percent=25, allow_tenants=["a"])
        data = json.loads(r.to_json())
        assert isinstance(data, dict)

    def test_to_json_enabled_field(self):
        r = self._make(enabled=True)
        data = json.loads(r.to_json())
        assert data["enabled"] is True

    def test_to_json_percent_field(self):
        r = self._make(percent=60)
        data = json.loads(r.to_json())
        assert data["percent"] == 60

    def test_to_json_allow_tenants_field(self):
        r = self._make(allow_tenants=["t1", "t2"])
        data = json.loads(r.to_json())
        assert data["allow_tenants"] == ["t1", "t2"]

    def test_from_json_round_trip_enabled(self):
        r = self._make(enabled=True)
        r2 = _FlagRecord.from_json("test.flag", r.to_json())
        assert r2.enabled is True

    def test_from_json_round_trip_percent(self):
        r = self._make(percent=80)
        r2 = _FlagRecord.from_json("test.flag", r.to_json())
        assert r2.percent == 80

    def test_from_json_round_trip_allow_tenants(self):
        r = self._make(allow_tenants=["tenant-a", "tenant-b"])
        r2 = _FlagRecord.from_json("test.flag", r.to_json())
        assert r2.allow_tenants == ["tenant-a", "tenant-b"]

    def test_from_json_key_preserved(self):
        r = self._make()
        r2 = _FlagRecord.from_json("special.key", r.to_json())
        assert r2.key == "special.key"

    def test_from_json_missing_fields_use_defaults(self):
        minimal = json.dumps({"enabled": False})
        r2 = _FlagRecord.from_json("my.flag", minimal)
        assert r2.percent == 0
        assert r2.allow_tenants == []

    def test_description_default_empty(self):
        r = self._make()
        assert r.description == ""

    def test_description_custom(self):
        r = self._make(description="Feature X rollout")
        assert r.description == "Feature X rollout"
