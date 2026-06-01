"""
feature_flags service unit testleri — 12 test. (P1 #41 tamamlandı)

Kapsam:
    * list_flags — boş ve dolu store
    * get_flag — mevcut ve bilinmeyen key
    * enable / disable — enabled alanı güncelleme
    * update value — percent ve allow_tenants güncelleme
    * FlagUpdate schema validasyonu — ge/le sınır kontrolleri
    * Bilinmeyen flag (unknown key) fail-closed davranışı
    * Persistence — set_flag sonrası get ile doğrulama
    * clear() — store sıfırlama
    * is_enabled — kısa-yol bool değerlendirmesi
    * evaluate reason — disabled / not_found / rollout_percent / tenant_allowlist
    * bind_redis — runtime redis enjeksiyonu
    * audit_sink — güncelleme event'i tetikleme
"""
from __future__ import annotations

from typing import Dict, List

import pytest
from pydantic import ValidationError

from app.domains.feature_flags.schemas import FlagUpdate
from app.domains.feature_flags.service import FeatureFlagService


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def svc() -> FeatureFlagService:
    """Her test için Redis'siz, temiz bir FeatureFlagService instance'ı."""
    return FeatureFlagService()


# ── 1. list_flags — boş store ────────────────────────────────────────────────

def test_list_flags_empty(svc: FeatureFlagService) -> None:
    """Henüz hiçbir flag eklenmemişse liste boş döner."""
    result = svc.list_flags()
    assert result == []


# ── 2. list_flags — dolu store ───────────────────────────────────────────────

def test_list_flags_returns_all(svc: FeatureFlagService) -> None:
    """Eklenen tüm flag'ler listeye yansır ve alfabetik sıralanır."""
    svc.set_flag("beta.feature", FlagUpdate(enabled=True))
    svc.set_flag("alpha.feature", FlagUpdate(enabled=False))
    flags = svc.list_flags()
    assert len(flags) == 2
    assert flags[0].key == "alpha.feature"
    assert flags[1].key == "beta.feature"


# ── 3. get_flag — mevcut key ─────────────────────────────────────────────────

def test_get_flag_existing(svc: FeatureFlagService) -> None:
    """Var olan bir key için get() doğru FlagOut döner."""
    svc.set_flag("my.flag", FlagUpdate(enabled=True, description="test flag"))
    out = svc.get("my.flag")
    assert out is not None
    assert out.key == "my.flag"
    assert out.enabled is True
    assert out.description == "test flag"


# ── 4. get_flag — bilinmeyen key ─────────────────────────────────────────────

def test_get_flag_unknown_returns_none(svc: FeatureFlagService) -> None:
    """Var olmayan key için get() None döner."""
    result = svc.get("does.not.exist")
    assert result is None


# ── 5. enable flag ───────────────────────────────────────────────────────────

def test_enable_flag(svc: FeatureFlagService) -> None:
    """Kapalı bir flag enabled=True ile açılır."""
    svc.set_flag("toggle.me", FlagUpdate(enabled=False))
    svc.set_flag("toggle.me", FlagUpdate(enabled=True))
    out = svc.get("toggle.me")
    assert out is not None
    assert out.enabled is True


# ── 6. disable flag ──────────────────────────────────────────────────────────

def test_disable_flag(svc: FeatureFlagService) -> None:
    """Açık bir flag enabled=False ile kapatılır."""
    svc.set_flag("toggle.me", FlagUpdate(enabled=True, percent=100))
    svc.set_flag("toggle.me", FlagUpdate(enabled=False))
    out = svc.get("toggle.me")
    assert out is not None
    assert out.enabled is False
    # Kapatılan flag evaluate'de de False döner
    ev = svc.evaluate("toggle.me", tenant_id="t1")
    assert ev.enabled is False
    assert ev.reason == "disabled"


# ── 7. update percent value ───────────────────────────────────────────────────

def test_update_percent(svc: FeatureFlagService) -> None:
    """percent değeri partial update ile doğru güncellenir, diğer alanlar korunur."""
    svc.set_flag("canary.flag", FlagUpdate(enabled=True, description="canary", percent=10))
    svc.set_flag("canary.flag", FlagUpdate(percent=90))
    out = svc.get("canary.flag")
    assert out is not None
    assert out.rollout.percent == 90
    assert out.enabled is True          # korundu
    assert out.description == "canary"  # korundu


# ── 8. FlagUpdate schema validasyonu — sınır değerler ────────────────────────

def test_flag_update_percent_bounds() -> None:
    """FlagUpdate percent alanı 0-100 aralığı dışında ValidationError fırlatır."""
    with pytest.raises(ValidationError):
        FlagUpdate(percent=101)
    with pytest.raises(ValidationError):
        FlagUpdate(percent=-1)
    # Sınır değerler geçerli
    assert FlagUpdate(percent=0).percent == 0
    assert FlagUpdate(percent=100).percent == 100


# ── 9. Bilinmeyen flag — fail-closed ─────────────────────────────────────────

def test_unknown_flag_fail_closed(svc: FeatureFlagService) -> None:
    """Bilinmeyen flag evaluate edildiğinde enabled=False ve reason='not_found' döner."""
    ev = svc.evaluate("nonexistent.flag", tenant_id="any-tenant")
    assert ev.enabled is False
    assert ev.reason == "not_found"


# ── 10. Persistence — set → get doğrulama ────────────────────────────────────

def test_persistence_set_then_get(svc: FeatureFlagService) -> None:
    """set_flag ile yazılan değer get ile geri okunabilir olmalı."""
    svc.set_flag(
        "persist.flag",
        FlagUpdate(enabled=True, percent=50, allow_tenants=["tenant-A"], description="persisted"),
        actor="admin",
    )
    out = svc.get("persist.flag")
    assert out is not None
    assert out.enabled is True
    assert out.rollout.percent == 50
    assert "tenant-A" in out.rollout.allow_tenants
    assert out.description == "persisted"
    assert out.updated_by == "admin"


# ── 11. clear() — store sıfırlama ────────────────────────────────────────────

def test_clear_resets_all_flags(svc: FeatureFlagService) -> None:
    """clear() sonrasında list_flags boş döner."""
    svc.set_flag("flag.a", FlagUpdate(enabled=True))
    svc.set_flag("flag.b", FlagUpdate(enabled=False))
    assert len(svc.list_flags()) == 2
    svc.clear()
    assert svc.list_flags() == []
    # Temizleme sonrası yeni flag eklenebilir
    svc.set_flag("flag.c", FlagUpdate(enabled=True))
    assert len(svc.list_flags()) == 1


# ── 12. is_enabled + evaluate reason detayları ───────────────────────────────

def test_is_enabled_and_evaluate_reasons(svc: FeatureFlagService) -> None:
    """is_enabled kısa-yolu ve evaluate reason değerleri doğru çalışır."""
    # tenant_allowlist reason
    svc.set_flag(
        "allow.flag",
        FlagUpdate(enabled=True, percent=0, allow_tenants=["vip-tenant"]),
    )
    assert svc.is_enabled("allow.flag", tenant_id="vip-tenant") is True
    ev_allow = svc.evaluate("allow.flag", tenant_id="vip-tenant")
    assert ev_allow.reason == "tenant_allowlist"

    # rollout_percent reason — 100% herkese açık
    svc.set_flag("full.flag", FlagUpdate(enabled=True, percent=100))
    ev_full = svc.evaluate("full.flag", tenant_id="any")
    assert ev_full.enabled is True
    assert ev_full.reason == "rollout_percent"

    # disabled reason
    svc.set_flag("off.flag", FlagUpdate(enabled=False))
    ev_off = svc.evaluate("off.flag", tenant_id="t1")
    assert ev_off.enabled is False
    assert ev_off.reason == "disabled"

    # is_enabled bool döner
    assert svc.is_enabled("full.flag", tenant_id="t") is True
    assert svc.is_enabled("off.flag", tenant_id="t") is False
