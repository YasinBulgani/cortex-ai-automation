"""Extended health service için unit testler — UX-F3-304.

Tüm dış bağımlılıklar (SQLAlchemy engine, redis, httpx) monkeypatch'li.
CI'da DB/Redis/Engine olmadan çalışır.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.domains.health import service as health_service
from app.domains.health.schemas import ComponentStatus, HealthLevel


# ── _compute_overall ──────────────────────────────────────────────────────


def test_overall_ok_when_all_ok() -> None:
    comps = [
        ComponentStatus(name="db", label="DB", level=HealthLevel.ok),
        ComponentStatus(name="engine", label="Engine", level=HealthLevel.ok),
    ]
    assert health_service._compute_overall(comps) == HealthLevel.ok


def test_overall_down_when_required_down() -> None:
    comps = [
        ComponentStatus(name="db", label="DB", level=HealthLevel.down),
        ComponentStatus(name="engine", label="Engine", level=HealthLevel.ok),
    ]
    assert health_service._compute_overall(comps) == HealthLevel.down


def test_overall_degraded_when_required_degraded() -> None:
    comps = [
        ComponentStatus(name="db", label="DB", level=HealthLevel.ok),
        ComponentStatus(name="engine", label="Engine", level=HealthLevel.degraded),
    ]
    assert health_service._compute_overall(comps) == HealthLevel.degraded


def test_overall_ok_when_optional_down() -> None:
    """Opsiyonel bileşen down → overall ok kalır (sadece degraded'a düşer)."""
    comps = [
        ComponentStatus(name="db", label="DB", level=HealthLevel.ok),
        ComponentStatus(name="engine", label="Engine", level=HealthLevel.ok),
        ComponentStatus(
            name="ollama", label="Ollama", level=HealthLevel.down, optional=True
        ),
    ]
    # Zorunlular ok ama opsiyonel down → overall degraded (visual hint)
    assert health_service._compute_overall(comps) == HealthLevel.degraded


def test_overall_down_wins_over_degraded() -> None:
    comps = [
        ComponentStatus(name="db", label="DB", level=HealthLevel.down),
        ComponentStatus(name="engine", label="Engine", level=HealthLevel.degraded),
    ]
    assert health_service._compute_overall(comps) == HealthLevel.down


def test_overall_all_optional_ok() -> None:
    """Tüm zorunlular ok + tüm opsiyoneller ok → overall ok."""
    comps = [
        ComponentStatus(name="db", label="DB", level=HealthLevel.ok),
        ComponentStatus(name="engine", label="Engine", level=HealthLevel.ok),
        ComponentStatus(
            name="ollama", label="Ollama", level=HealthLevel.ok, optional=True
        ),
    ]
    assert health_service._compute_overall(comps) == HealthLevel.ok


# ── _timed ────────────────────────────────────────────────────────────────


def test_timed_fills_latency_when_missing() -> None:
    def _check():
        return ComponentStatus(name="x", label="X", level=HealthLevel.ok)

    result = health_service._timed(_check)
    assert result.latency_ms is not None and result.latency_ms >= 0


def test_timed_catches_exception() -> None:
    def _check():
        raise RuntimeError("boom")

    result = health_service._timed(_check)
    assert result.level == HealthLevel.down
    assert "boom" in (result.detail or "")


# ── get_extended_health (integration, tüm check'ler mock'lu) ──────────────


def test_get_extended_health_all_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tüm check'ler down dönerse overall down."""
    def _fail_db():
        return ComponentStatus(
            name="postgres", label="Veritabanı", level=HealthLevel.down, detail="no db"
        )

    def _fail_redis():
        return ComponentStatus(
            name="redis", label="Redis", level=HealthLevel.down, optional=True
        )

    def _fail_engine():
        return ComponentStatus(
            name="engine", label="Engine", level=HealthLevel.down
        )

    def _fail_gateway():
        return ComponentStatus(
            name="ai_gateway", label="AI GW", level=HealthLevel.down, optional=True
        )

    def _fail_ollama():
        return ComponentStatus(
            name="ollama", label="Ollama", level=HealthLevel.down, optional=True
        )

    monkeypatch.setattr(health_service, "_CHECKS", (
        _fail_db, _fail_redis, _fail_engine, _fail_gateway, _fail_ollama,
    ))

    result = health_service.get_extended_health()
    assert result.overall == HealthLevel.down
    assert len(result.components) == 5
    # Opsiyonel işaretleri korunmuş
    names_optional = {c.name: c.optional for c in result.components}
    assert names_optional["redis"] is True
    assert names_optional["postgres"] is False
    assert names_optional["engine"] is False


def test_get_extended_health_happy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Her şey ok."""
    def _ok(name: str, label: str, opt: bool = False):
        def _fn():
            return ComponentStatus(
                name=name, label=label, level=HealthLevel.ok, optional=opt
            )
        return _fn

    monkeypatch.setattr(health_service, "_CHECKS", (
        _ok("postgres", "DB"),
        _ok("redis", "Redis", opt=True),
        _ok("engine", "Engine"),
        _ok("ai_gateway", "GW", opt=True),
        _ok("ollama", "Ollama", opt=True),
    ))

    result = health_service.get_extended_health()
    assert result.overall == HealthLevel.ok
    assert result.checked_at_unix > 0
    assert result.app_name is not None


def test_get_extended_health_mixed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Zorunlu ok + opsiyonel down → overall degraded (görsel ipucu)."""
    def _ok_db():
        return ComponentStatus(name="postgres", label="DB", level=HealthLevel.ok)

    def _down_ollama():
        return ComponentStatus(
            name="ollama", label="Ollama", level=HealthLevel.down, optional=True
        )

    def _ok_engine():
        return ComponentStatus(name="engine", label="Engine", level=HealthLevel.ok)

    monkeypatch.setattr(health_service, "_CHECKS", (_ok_db, _down_ollama, _ok_engine))

    result = health_service.get_extended_health()
    assert result.overall == HealthLevel.degraded  # opsiyonel down görsel sinyal
