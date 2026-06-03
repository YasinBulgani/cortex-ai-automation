"""Feature flags domain — DB/Redis bağlantısız birim testleri.

Kapsam (görev gereklilikleri):
    1. test_feature_flag_enabled          — aktif flag is_enabled True döner
    2. test_feature_flag_disabled         — pasif flag is_enabled False döner
    3. test_feature_flag_not_found        — olmayan flag 404 / not_found reason döner
    4. test_feature_flag_percentage_rollout — percentage > 0 and < 100
    5. test_feature_flag_tenant_override  — tenant bazlı override

Ek testler:
    * Memory fallback (Redis yok) davranışı
    * Deterministik canary bucket (aynı tenant her zaman aynı karar)
    * Allow-list + percent kombinasyonu
    * Anonim kullanıcıda canary kapalı (fail-closed)
    * set_flag upsert / partial update davranışı
    * Audit sink çağrısı
    * Redis entegrasyonu

Redis mock'u: redis client'ın sadece ``hgetall/hset/hdel/delete`` metotları
kullanılıyor — pytest-mock yerine basit bir fake sınıfı yazıyoruz ki testler
hızlı ve bağımlılıksız kalsın.
"""
from __future__ import annotations

from typing import Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.domains.feature_flags.schemas import FlagUpdate
from app.domains.feature_flags.service import FeatureFlagService, _hash_bucket


# ── Redis fake ───────────────────────────────────────────────────────────────


class _FakeRedis:
    """Minimal redis.Redis stub — sadece kullanılan metotlar."""

    def __init__(self, *, fail: bool = False) -> None:
        self._hash: Dict[str, Dict[str, str]] = {}
        self._fail = fail
        self.calls: List[str] = []

    def hgetall(self, key: str) -> Dict[str, str]:
        self.calls.append(f"hgetall:{key}")
        if self._fail:
            raise RuntimeError("boom")
        return dict(self._hash.get(key, {}))

    def hset(self, key: str, field: str, value: str) -> int:
        self.calls.append(f"hset:{key}:{field}")
        if self._fail:
            raise RuntimeError("boom")
        self._hash.setdefault(key, {})[field] = value
        return 1

    def hdel(self, key: str, field: str) -> int:
        self.calls.append(f"hdel:{key}:{field}")
        if self._fail:
            raise RuntimeError("boom")
        bucket = self._hash.get(key)
        if bucket and field in bucket:
            del bucket[field]
            return 1
        return 0

    def delete(self, key: str) -> int:
        self.calls.append(f"delete:{key}")
        if self._fail:
            raise RuntimeError("boom")
        return 1 if self._hash.pop(key, None) is not None else 0


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def svc() -> FeatureFlagService:
    """Her test için temiz, Redis'siz instance."""
    return FeatureFlagService()


@pytest.fixture
def svc_with_redis() -> tuple[FeatureFlagService, _FakeRedis]:
    redis = _FakeRedis()
    s = FeatureFlagService(redis_client=redis)
    return s, redis


# ── 1. test_feature_flag_enabled ─────────────────────────────────────────────


class TestFeatureFlagEnabled:
    """Aktif flag is_enabled True döner."""

    def test_is_enabled_returns_true(self, svc: FeatureFlagService) -> None:
        svc.set_flag("my.feature", FlagUpdate(enabled=True, percent=100), actor="test")
        assert svc.is_enabled("my.feature") is True

    def test_evaluate_reason_rollout_percent(self, svc: FeatureFlagService) -> None:
        svc.set_flag("my.feature", FlagUpdate(enabled=True, percent=100), actor="test")
        result = svc.evaluate("my.feature")
        assert result.enabled is True
        assert result.reason == "rollout_percent"

    def test_get_returns_enabled_flag(self, svc: FeatureFlagService) -> None:
        svc.set_flag("my.feature", FlagUpdate(enabled=True, description="canary test"))
        out = svc.get("my.feature")
        assert out is not None
        assert out.enabled is True

    def test_hundred_percent_always_true(self, svc: FeatureFlagService) -> None:
        svc.set_flag("x", FlagUpdate(enabled=True, percent=100))
        out = svc.evaluate("x", tenant_id="any")
        assert out.enabled is True
        assert out.reason == "rollout_percent"

    def test_full_rollout_covers_anonymous(self, svc: FeatureFlagService) -> None:
        svc.set_flag("x", FlagUpdate(enabled=True, percent=100))
        out = svc.evaluate("x", tenant_id=None)
        assert out.enabled is True


# ── 2. test_feature_flag_disabled ────────────────────────────────────────────


class TestFeatureFlagDisabled:
    """Pasif flag is_enabled False döner."""

    def test_is_enabled_returns_false(self, svc: FeatureFlagService) -> None:
        svc.set_flag("off.feature", FlagUpdate(enabled=False, percent=100), actor="test")
        assert svc.is_enabled("off.feature") is False

    def test_evaluate_reason_disabled(self, svc: FeatureFlagService) -> None:
        svc.set_flag("off.feature", FlagUpdate(enabled=False, percent=100), actor="test")
        result = svc.evaluate("off.feature")
        assert result.enabled is False
        assert result.reason == "disabled"

    def test_disabled_overrides_tenant_allowlist(self, svc: FeatureFlagService) -> None:
        """enabled=False ise tenant allowlist'te olsa bile kapalı kalır."""
        svc.set_flag(
            "off.feature",
            FlagUpdate(enabled=False, percent=100, allow_tenants=["tenant-1"]),
        )
        result = svc.evaluate("off.feature", tenant_id="tenant-1")
        assert result.enabled is False
        assert result.reason == "disabled"

    def test_disabled_flag_always_false_any_tenant(self, svc: FeatureFlagService) -> None:
        svc.set_flag("x", FlagUpdate(enabled=False, percent=100))
        out = svc.evaluate("x", tenant_id="t1")
        assert out.enabled is False
        assert out.reason == "disabled"


# ── 3. test_feature_flag_not_found ───────────────────────────────────────────


class TestFeatureFlagNotFound:
    """Olmayan flag 404 / not_found reason döner."""

    def test_evaluate_unknown_key_returns_not_found(self, svc: FeatureFlagService) -> None:
        result = svc.evaluate("does.not.exist")
        assert result.enabled is False
        assert result.reason == "not_found"

    def test_evaluate_unknown_key_custom_default(self, svc: FeatureFlagService) -> None:
        result = svc.evaluate("does.not.exist", default=True)
        assert result.reason == "not_found"
        assert result.enabled is True

    def test_is_enabled_unknown_key_fail_closed(self, svc: FeatureFlagService) -> None:
        """Bilinmeyen key → fail-closed → False."""
        assert svc.is_enabled("unknown.key") is False

    def test_get_unknown_key_returns_none(self, svc: FeatureFlagService) -> None:
        assert svc.get("unknown.key") is None

    def test_router_get_raises_404(self) -> None:
        """Router katmanı: get() None döndüğünde HTTPException 404 fırlatılır."""
        from fastapi import HTTPException
        from app.domains.feature_flags.router import get_flag

        mock_user = MagicMock()
        with patch("app.domains.feature_flags.router.feature_flags") as mock_svc:
            mock_svc.get.return_value = None
            with pytest.raises(HTTPException) as exc_info:
                get_flag("non.existent", _=mock_user)
        assert exc_info.value.status_code == 404

    def test_router_delete_raises_404(self) -> None:
        """Router katmanı: delete() False döndüğünde HTTPException 404 fırlatılır."""
        from fastapi import HTTPException
        from app.domains.feature_flags.router import delete_flag

        mock_user = MagicMock()
        with patch("app.domains.feature_flags.router.feature_flags") as mock_svc:
            mock_svc.delete.return_value = False
            with pytest.raises(HTTPException) as exc_info:
                delete_flag("non.existent", _=mock_user)
        assert exc_info.value.status_code == 404

    def test_unknown_flag_returns_default(self, svc: FeatureFlagService) -> None:
        out = svc.evaluate("not.exists", tenant_id="t1")
        assert out.enabled is False
        assert out.reason == "not_found"

    def test_unknown_flag_with_default_true(self, svc: FeatureFlagService) -> None:
        out = svc.evaluate("not.exists", tenant_id="t1", default=True)
        assert out.enabled is True
        assert out.reason == "not_found"


# ── 4. test_feature_flag_percentage_rollout ──────────────────────────────────


class TestFeatureFlagPercentageRollout:
    """Percentage > 0 and < 100 — canary rollout davranışı."""

    def test_zero_percent_always_disabled(self, svc: FeatureFlagService) -> None:
        svc.set_flag("canary.feature", FlagUpdate(enabled=True, percent=0))
        for tenant in ["t1", "t2", "t3", "t4", "t5"]:
            assert svc.is_enabled("canary.feature", tenant_id=tenant) is False

    def test_hundred_percent_always_enabled(self, svc: FeatureFlagService) -> None:
        svc.set_flag("full.rollout", FlagUpdate(enabled=True, percent=100))
        for tenant in ["t1", "t2", "t3", "t4", "t5"]:
            assert svc.is_enabled("full.rollout", tenant_id=tenant) is True

    def test_partial_percent_deterministic(self, svc: FeatureFlagService) -> None:
        """Aynı (tenant, key) çifti her çağrıda aynı sonucu verir."""
        svc.set_flag("partial.feature", FlagUpdate(enabled=True, percent=50))
        tenant = "deterministic-tenant-abc"
        first = svc.is_enabled("partial.feature", tenant_id=tenant)
        for _ in range(5):
            assert svc.is_enabled("partial.feature", tenant_id=tenant) == first

    def test_percent_boundary_clamp_upper(self, svc: FeatureFlagService) -> None:
        """FlagUpdate şeması percent>100 değerini reddeder (ge=0, le=100 validator)."""
        with pytest.raises(Exception):  # pydantic ValidationError
            FlagUpdate(enabled=True, percent=150)

    def test_percent_boundary_clamp_lower(self, svc: FeatureFlagService) -> None:
        """FlagUpdate şeması percent<0 değerini reddeder (ge=0, le=100 validator)."""
        with pytest.raises(Exception):  # pydantic ValidationError
            FlagUpdate(enabled=True, percent=-10)

    def test_partial_rollout_no_tenant_id_is_disabled(self, svc: FeatureFlagService) -> None:
        """tenant_id verilmezse ve percent<100 ise kapalı kalır (anonim canary koruması)."""
        svc.set_flag("canary.partial", FlagUpdate(enabled=True, percent=50))
        result = svc.evaluate("canary.partial", tenant_id=None)
        assert result.enabled is False
        assert result.reason == "rollout_percent"

    def test_partial_rollout_reason_is_rollout_percent(self, svc: FeatureFlagService) -> None:
        svc.set_flag("mid.rollout", FlagUpdate(enabled=True, percent=50))
        result = svc.evaluate("mid.rollout", tenant_id="some-tenant")
        assert result.reason == "rollout_percent"
        assert 0 < result.percent < 100

    def test_canary_is_deterministic_per_tenant(self, svc: FeatureFlagService) -> None:
        svc.set_flag("x", FlagUpdate(enabled=True, percent=50))
        first = svc.is_enabled("x", tenant_id="tenant-42")
        for _ in range(10):
            assert svc.is_enabled("x", tenant_id="tenant-42") == first

    def test_canary_distribution_is_balanced(self) -> None:
        """Bucket fonksiyonu 1000 tenant üzerinde ~%50 dağılım vermeli (±10%)."""
        count = sum(1 for i in range(1000) if _hash_bucket(f"tenant-{i}", "flag") < 50)
        assert 400 <= count <= 600, f"beklenen dağılım ~500, gerçekleşen {count}"

    def test_anonymous_tenant_canary_closed(self, svc: FeatureFlagService) -> None:
        """tenant_id verilmezse percent<100 ise kapalı kalmalı."""
        svc.set_flag("x", FlagUpdate(enabled=True, percent=50))
        out = svc.evaluate("x", tenant_id=None)
        assert out.enabled is False

    def test_zero_percent_and_no_allowlist_false(self, svc: FeatureFlagService) -> None:
        svc.set_flag("x", FlagUpdate(enabled=True, percent=0))
        out = svc.evaluate("x", tenant_id="t1")
        assert out.enabled is False


# ── 5. test_feature_flag_tenant_override ─────────────────────────────────────


class TestFeatureFlagTenantOverride:
    """Tenant bazlı override — allow_tenants beyaz listesi."""

    def test_allowlisted_tenant_gets_flag_enabled(self, svc: FeatureFlagService) -> None:
        """percent=0 olmasına rağmen beyaz listedeki tenant açık görür."""
        svc.set_flag(
            "tenant.flag", FlagUpdate(enabled=True, percent=0, allow_tenants=["vip-tenant"])
        )
        result = svc.evaluate("tenant.flag", tenant_id="vip-tenant")
        assert result.enabled is True
        assert result.reason == "tenant_allowlist"

    def test_non_allowlisted_tenant_obeys_percent(self, svc: FeatureFlagService) -> None:
        """percent=0 → beyaz listede olmayan tenant için kapalı."""
        svc.set_flag(
            "tenant.flag", FlagUpdate(enabled=True, percent=0, allow_tenants=["vip-tenant"])
        )
        result = svc.evaluate("tenant.flag", tenant_id="regular-tenant")
        assert result.enabled is False
        assert result.reason == "rollout_percent"

    def test_multiple_tenants_in_allowlist(self, svc: FeatureFlagService) -> None:
        svc.set_flag(
            "multi.tenant.flag",
            FlagUpdate(enabled=True, percent=0, allow_tenants=["alpha", "beta", "gamma"]),
        )
        for tenant in ["alpha", "beta", "gamma"]:
            result = svc.evaluate("multi.tenant.flag", tenant_id=tenant)
            assert result.enabled is True, f"Tenant {tenant!r} açık olmalı"
            assert result.reason == "tenant_allowlist"

        result_other = svc.evaluate("multi.tenant.flag", tenant_id="delta")
        assert result_other.enabled is False

    def test_allow_tenants_deduplication(self, svc: FeatureFlagService) -> None:
        """FlagUpdate.allow_tenants tekrar eden tenantları temizler."""
        out = svc.set_flag(
            "dedup.flag",
            FlagUpdate(enabled=True, allow_tenants=["t1", "t1", "t2", " t2 "]),
            actor="test",
        )
        assert out.rollout.allow_tenants.count("t1") == 1
        assert out.rollout.allow_tenants.count("t2") == 1

    def test_tenant_override_cleared_on_update(self, svc: FeatureFlagService) -> None:
        """allow_tenants=[] ile override listesi boşaltılabilir."""
        svc.set_flag("clear.flag", FlagUpdate(enabled=True, percent=0, allow_tenants=["vip"]))
        assert svc.evaluate("clear.flag", tenant_id="vip").enabled is True

        svc.set_flag("clear.flag", FlagUpdate(allow_tenants=[]), actor="test")
        result = svc.evaluate("clear.flag", tenant_id="vip")
        assert result.enabled is False
        assert result.reason == "rollout_percent"

    def test_tenant_override_takes_priority_over_rollout_percent(self, svc: FeatureFlagService) -> None:
        """tenant_allowlist reason, rollout_percent reason'dan önce gelir."""
        svc.set_flag("prio.flag", FlagUpdate(enabled=True, percent=50, allow_tenants=["vip"]))
        result = svc.evaluate("prio.flag", tenant_id="vip")
        assert result.reason == "tenant_allowlist"
        assert result.enabled is True

    def test_allowlist_overrides_percent(self, svc: FeatureFlagService) -> None:
        svc.set_flag(
            "x", FlagUpdate(enabled=True, percent=0, allow_tenants=["tenant-gold"])
        )
        out = svc.evaluate("x", tenant_id="tenant-gold")
        assert out.enabled is True
        assert out.reason == "tenant_allowlist"


# ── Upsert & Partial update ──────────────────────────────────────────────────


def test_set_and_list(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True, description="x flag"), actor="admin")
    flags = svc.list_flags()
    assert len(flags) == 1
    assert flags[0].key == "x"
    assert flags[0].enabled is True
    assert flags[0].description == "x flag"
    assert flags[0].updated_by == "admin"


def test_partial_update_preserves_other_fields(svc: FeatureFlagService) -> None:
    svc.set_flag(
        "x",
        FlagUpdate(enabled=True, description="orig", percent=30, allow_tenants=["a"]),
    )
    svc.set_flag("x", FlagUpdate(percent=75))
    out = svc.get("x")
    assert out is not None
    assert out.enabled is True
    assert out.description == "orig"
    assert out.rollout.percent == 75
    assert out.rollout.allow_tenants == ["a"]


def test_delete(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True))
    assert svc.delete("x") is True
    assert svc.get("x") is None
    assert svc.delete("x") is False


def test_empty_key_rejected(svc: FeatureFlagService) -> None:
    with pytest.raises(ValueError):
        svc.set_flag("  ", FlagUpdate(enabled=True))


# ── Redis entegrasyonu ───────────────────────────────────────────────────────


def test_redis_persist_and_hydrate(
    svc_with_redis: tuple[FeatureFlagService, _FakeRedis],
) -> None:
    svc, redis = svc_with_redis
    svc.set_flag("x", FlagUpdate(enabled=True, percent=80))
    assert any(c.startswith("hset:ff:flags:x") for c in redis.calls)

    svc2 = FeatureFlagService(redis_client=redis)
    got = svc2.get("x")
    assert got is not None
    assert got.enabled is True
    assert got.rollout.percent == 80


def test_redis_failure_falls_back_to_memory() -> None:
    redis = _FakeRedis(fail=True)
    svc = FeatureFlagService(redis_client=redis)
    out = svc.set_flag("x", FlagUpdate(enabled=True))
    assert out.enabled is True
    assert svc.is_enabled("x", tenant_id="t1")


# ── Audit sink ───────────────────────────────────────────────────────────────


def test_audit_sink_called() -> None:
    events: List[tuple[str, dict]] = []

    def sink(action: str, payload: dict) -> None:
        events.append((action, payload))

    svc = FeatureFlagService(audit_sink=sink)
    svc.set_flag("x", FlagUpdate(enabled=True, percent=50), actor="admin@x")
    assert len(events) == 1
    action, payload = events[0]
    assert action == "feature_flag.updated"
    assert payload["key"] == "x"
    assert payload["enabled"] is True
    assert payload["percent"] == 50
    assert payload["actor"] == "admin@x"
