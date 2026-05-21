"""FeatureFlagService unit testleri.

Kapsam:
    * Memory fallback (Redis yok) davranışı
    * Deterministik canary bucket (aynı tenant her zaman aynı karar)
    * Allow-list + percent kombinasyonu
    * Anonim kullanıcıda canary kapalı (fail-closed)
    * set_flag upsert davranışı
    * Audit sink çağrısı

Redis mock'u: redis client'ın sadece ``hget/hgetall/hset/hdel/delete`` metotları
kullanılıyor — pytest-mock yerine basit bir fake sınıfı yazıyoruz ki testler
hızlı ve bağımlılıksız kalsın.
"""
from __future__ import annotations

from typing import Dict, List

import pytest

from app.domains.feature_flags.schemas import FlagUpdate
from app.domains.feature_flags.service import FeatureFlagService, _hash_bucket


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


@pytest.fixture
def svc() -> FeatureFlagService:
    """Her test için temiz, Redis'siz instance."""
    return FeatureFlagService()


@pytest.fixture
def svc_with_redis() -> tuple[FeatureFlagService, _FakeRedis]:
    redis = _FakeRedis()
    s = FeatureFlagService(redis_client=redis)
    return s, redis


# ── Temel davranış ───────────────────────────────────────────────────────────


def test_unknown_flag_returns_default(svc: FeatureFlagService) -> None:
    out = svc.evaluate("not.exists", tenant_id="t1")
    assert out.enabled is False
    assert out.reason == "not_found"


def test_unknown_flag_with_default_true(svc: FeatureFlagService) -> None:
    out = svc.evaluate("not.exists", tenant_id="t1", default=True)
    assert out.enabled is True
    assert out.reason == "not_found"


def test_set_and_list(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True, description="x flag"), actor="admin")
    flags = svc.list_flags()
    assert len(flags) == 1
    assert flags[0].key == "x"
    assert flags[0].enabled is True
    assert flags[0].description == "x flag"
    assert flags[0].updated_by == "admin"


def test_disabled_flag_always_false(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=False, percent=100))
    out = svc.evaluate("x", tenant_id="t1")
    assert out.enabled is False
    assert out.reason == "disabled"


def test_allowlist_overrides_percent(svc: FeatureFlagService) -> None:
    svc.set_flag(
        "x", FlagUpdate(enabled=True, percent=0, allow_tenants=["tenant-gold"])
    )
    out = svc.evaluate("x", tenant_id="tenant-gold")
    assert out.enabled is True
    assert out.reason == "tenant_allowlist"


def test_hundred_percent_always_true(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True, percent=100))
    out = svc.evaluate("x", tenant_id="any")
    assert out.enabled is True
    assert out.reason == "rollout_percent"


def test_zero_percent_and_no_allowlist_false(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True, percent=0))
    out = svc.evaluate("x", tenant_id="t1")
    assert out.enabled is False


def test_anonymous_tenant_canary_closed(svc: FeatureFlagService) -> None:
    """tenant_id verilmezse percent<100 ise kapalı kalmalı (flicker önleme)."""
    svc.set_flag("x", FlagUpdate(enabled=True, percent=50))
    out = svc.evaluate("x", tenant_id=None)
    assert out.enabled is False


def test_full_rollout_covers_anonymous(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True, percent=100))
    out = svc.evaluate("x", tenant_id=None)
    assert out.enabled is True


# ── Deterministik canary ─────────────────────────────────────────────────────


def test_canary_is_deterministic_per_tenant(svc: FeatureFlagService) -> None:
    svc.set_flag("x", FlagUpdate(enabled=True, percent=50))
    first = svc.is_enabled("x", tenant_id="tenant-42")
    # Cache invalidation + Redis olmadığı için birkaç kez çağır
    for _ in range(10):
        assert svc.is_enabled("x", tenant_id="tenant-42") == first


def test_canary_distribution_is_balanced() -> None:
    """Bucket fonksiyonu 1000 tenant üzerinde ~%50 dağılım vermeli (±10%)."""
    count = sum(1 for i in range(1000) if _hash_bucket(f"tenant-{i}", "flag") < 50)
    assert 400 <= count <= 600, f"beklenen dağılım ~500, gerçekleşen {count}"


# ── Upsert & Partial update ──────────────────────────────────────────────────


def test_partial_update_preserves_other_fields(svc: FeatureFlagService) -> None:
    svc.set_flag(
        "x",
        FlagUpdate(enabled=True, description="orig", percent=30, allow_tenants=["a"]),
    )
    # Sadece percent güncelle
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
    # ikinci silme False
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

    # Yeni bir service instance — redis'ten hydrate etmeli
    svc2 = FeatureFlagService(redis_client=redis)
    got = svc2.get("x")
    assert got is not None
    assert got.enabled is True
    assert got.rollout.percent == 80


def test_redis_failure_falls_back_to_memory() -> None:
    redis = _FakeRedis(fail=True)
    svc = FeatureFlagService(redis_client=redis)
    # hset patlasa da memory'e yazılır, sonraki read memory'den gelir
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
