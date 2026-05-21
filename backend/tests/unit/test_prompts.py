"""Canary karar fonksiyonu + resolve semantiği unit testleri.

DB'ye gitmeden:
    * canary pure fn (test_canary_*)
    * resolve dal mantığı: monkey-patch'lenmiş get_rollout / get_version /
      list_versions ile davranış kontrol edilir (test_resolve_*)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import pytest

from app.domains.prompts.canary import canary_bucket, should_canary
from app.domains.prompts import service as svc
from app.domains.prompts.schemas import (
    PromptVersionOut,
    RolloutIn,
    RolloutOut,
)


# ── Canary pure fn ────────────────────────────────────────────────────────


def test_canary_zero_pct_never_true() -> None:
    for t in ["a", "b", "zzz"]:
        assert should_canary(t, "p", 0) is False


def test_canary_hundred_pct_always_true() -> None:
    for t in ["a", "b", None]:
        assert should_canary(t, "p", 100) is True


def test_canary_anonymous_below_hundred_false() -> None:
    # Anonim (tenant=None) %100 altı canary'ye alınmaz (flicker önleme)
    assert should_canary(None, "p", 50) is False
    assert should_canary("", "p", 99) is False


def test_canary_deterministic_per_tenant() -> None:
    for pct in [10, 25, 50, 75, 99]:
        first = should_canary("tenant-42", "prompt.x", pct)
        for _ in range(10):
            assert should_canary("tenant-42", "prompt.x", pct) == first


def test_canary_bucket_distribution() -> None:
    # 1000 tenant üstünde ~%50 canary oranı ~500±%10 içinde olmalı
    hits = sum(
        1 for i in range(1000) if should_canary(f"tenant-{i}", "p", 50)
    )
    assert 400 <= hits <= 600, f"dağılım 500±100 beklendi, elde: {hits}"


def test_canary_bucket_different_prompt_independent() -> None:
    # Aynı tenant farklı prompt → farklı kararlar mümkün (aynı hash değil)
    same = 0
    for pct in [50]:
        for i in range(500):
            a = should_canary(f"t-{i}", "prompt.a", pct)
            b = should_canary(f"t-{i}", "prompt.b", pct)
            if a == b:
                same += 1
    # Tamamen bağımsız olsaydı ~%50 aynı olurdu; identical hash olamaz
    # bağımsız randomness + deterministik — yaklaşık %50
    assert 200 <= same <= 300


# ── resolve() dal mantığı ────────────────────────────────────────────────


def _mk_version(prompt_id: str, version: int, system: str = "S", user_t: str = "U") -> PromptVersionOut:
    return PromptVersionOut(
        id=version,
        prompt_id=prompt_id,
        version=version,
        system_prompt=system,
        user_template=user_t,
        model_hint=None,
        temperature=None,
        max_tokens=None,
        notes=None,
        created_at=datetime.now(timezone.utc),
        created_by=None,
    )


def _mk_rollout(
    prompt_id: str,
    active: int = 1,
    canary: Optional[int] = None,
    pct: int = 0,
) -> RolloutOut:
    return RolloutOut(
        prompt_id=prompt_id,
        env="prod",
        active_version=active,
        canary_version=canary,
        canary_pct=pct,
        updated_at=datetime.now(timezone.utc),
        updated_by=None,
    )


@pytest.fixture
def stub_store(monkeypatch: pytest.MonkeyPatch):
    """Her testte kontrolü kolay in-memory stub."""
    rollouts: dict = {}
    versions: dict = {}

    def _get_rollout(pid, env="prod"):
        return rollouts.get((pid, env))

    def _get_version(pid, v):
        return versions.get((pid, v))

    def _list_versions(pid, limit=100):
        xs = [v for (p, _), v in versions.items() if p == pid]
        return sorted(xs, key=lambda x: -x.version)[:limit]

    monkeypatch.setattr(svc, "get_rollout", _get_rollout)
    monkeypatch.setattr(svc, "get_version", _get_version)
    monkeypatch.setattr(svc, "list_versions", _list_versions)

    class Store:
        def add_version(self, pid, v, **kwargs):
            versions[(pid, v)] = _mk_version(pid, v, **kwargs)

        def set_rollout(self, pid, **kwargs):
            rollouts[(pid, "prod")] = _mk_rollout(pid, **kwargs)

    return Store()


def test_resolve_no_prompt_returns_none(stub_store) -> None:
    assert svc.resolve("ghost") is None


def test_resolve_no_rollout_uses_latest_version(stub_store) -> None:
    stub_store.add_version("p", 1)
    stub_store.add_version("p", 2)
    stub_store.add_version("p", 3)
    out = svc.resolve("p", tenant_id="t1")
    assert out is not None
    assert out.version == 3
    assert out.decision_reason == "active"
    assert out.active_version == 3
    assert out.canary_version is None


def test_resolve_active_only(stub_store) -> None:
    stub_store.add_version("p", 1)
    stub_store.add_version("p", 2)
    stub_store.set_rollout("p", active=2, canary=None, pct=0)
    out = svc.resolve("p", tenant_id="t1")
    assert out is not None
    assert out.version == 2
    assert out.decision_reason == "active"


def test_resolve_canary_hits(stub_store) -> None:
    # %100 canary → herkes canary
    stub_store.add_version("p", 1)
    stub_store.add_version("p", 2)
    stub_store.set_rollout("p", active=1, canary=2, pct=100)
    out = svc.resolve("p", tenant_id="t1")
    assert out is not None
    assert out.version == 2
    assert out.decision_reason == "canary_percent"
    assert out.canary_pct == 100


def test_resolve_canary_zero_pct(stub_store) -> None:
    # pct=0 → hiç canary, active gider
    stub_store.add_version("p", 1)
    stub_store.add_version("p", 2)
    stub_store.set_rollout("p", active=1, canary=2, pct=0)
    out = svc.resolve("p", tenant_id="t1")
    assert out is not None
    assert out.version == 1
    assert out.decision_reason == "active"


def test_resolve_canary_broken_falls_back_to_active(stub_store) -> None:
    # canary_version=2 ama 2 yok → active=1'e fallback
    stub_store.add_version("p", 1)
    stub_store.set_rollout("p", active=1, canary=2, pct=100)
    out = svc.resolve("p", tenant_id="t1")
    assert out is not None
    assert out.version == 1
    assert out.decision_reason == "fallback_active"


def test_resolve_no_versions_returns_none(stub_store) -> None:
    # rollout var ama versiyon hiç yok (korumalı durum)
    stub_store.set_rollout("p", active=1, canary=None, pct=0)
    out = svc.resolve("p", tenant_id="t1")
    assert out is None


def test_resolve_anonymous_with_partial_canary_gets_active(stub_store) -> None:
    # tenant_id None, canary %50 → anonim canary'e düşmez, active
    stub_store.add_version("p", 1)
    stub_store.add_version("p", 2)
    stub_store.set_rollout("p", active=1, canary=2, pct=50)
    out = svc.resolve("p", tenant_id=None)
    assert out is not None
    assert out.version == 1
    assert out.decision_reason == "active"


# ── RolloutIn validasyonu ────────────────────────────────────────────────


def test_rollout_in_canary_pct_requires_version() -> None:
    with pytest.raises(ValueError, match="canary_version zorunlu"):
        RolloutIn(active_version=1, canary_version=None, canary_pct=10)


def test_rollout_in_canary_zero_pct_no_version_ok() -> None:
    ro = RolloutIn(active_version=1, canary_version=None, canary_pct=0)
    assert ro.canary_pct == 0
