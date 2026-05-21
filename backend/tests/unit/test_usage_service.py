"""usage_service.record_usage karma davranışını doğrula.

* Pricing doğru hesaplanıyor ve döndürülüyor
* Prometheus sayaçları doğru label'larla artıyor
* DB hatası pipeline'ı kırmıyor (record_usage hâlâ cost döner)
* cost_usd_override pricing'i bypass eder
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from app.domains.ai import usage_service as us


@pytest.fixture
def captured_emits(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    """Prometheus emit çağrılarını yakalar."""
    captured: List[Dict[str, Any]] = []

    def _fake_emit(**kwargs: Any) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(us, "_emit_metrics", _fake_emit)
    return captured


@pytest.fixture
def capture_persist(monkeypatch: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []

    def _fake_persist(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(us, "_persist_trace", _fake_persist)
    return calls


def test_record_usage_computes_cost(
    captured_emits: List[Dict[str, Any]],
    capture_persist: List[Dict[str, Any]],
) -> None:
    cost = us.record_usage(
        tenant_id="tenant-1",
        agent_name="TestAgent",
        model="gpt-4o-mini",
        latency_ms=123,
        input_tokens=1_000_000,
        output_tokens=500_000,
        provider="openai",
        task_type="scenario_gen",
    )
    # 1M*0.15 + 0.5M*0.60 = 0.15 + 0.30 = 0.45 USD
    assert cost == pytest.approx(0.45)

    # Emit bir kere çağrılmalı, doğru parametrelerle
    assert len(captured_emits) == 1
    emit = captured_emits[0]
    assert emit["tenant_id"] == "tenant-1"
    assert emit["model"] == "gpt-4o-mini"
    assert emit["provider"] == "openai"
    assert emit["input_tokens"] == 1_000_000
    assert emit["output_tokens"] == 500_000
    assert emit["cost_usd"] == pytest.approx(0.45)

    # Persist bir kere çağrılmalı, tenant_id + cost_usd doğru
    assert len(capture_persist) == 1
    persist = capture_persist[0]
    assert persist["tenant_id"] == "tenant-1"
    assert persist["cost_usd"] == pytest.approx(0.45)
    assert persist["total_tokens"] == 1_500_000
    assert persist["task_type"] == "scenario_gen"


def test_cost_override_bypasses_pricing(
    captured_emits: List[Dict[str, Any]],
    capture_persist: List[Dict[str, Any]],
) -> None:
    cost = us.record_usage(
        tenant_id="t",
        agent_name="a",
        model="gpt-4o",
        latency_ms=10,
        input_tokens=1_000_000,  # gpt-4o'da 2.50 olurdu
        output_tokens=0,
        cost_usd_override=0.99,
    )
    assert cost == 0.99
    assert capture_persist[0]["cost_usd"] == 0.99


def test_negative_override_clamped_to_zero(
    captured_emits: List[Dict[str, Any]],
    capture_persist: List[Dict[str, Any]],
) -> None:
    cost = us.record_usage(
        tenant_id="t",
        agent_name="a",
        model="gpt-4o",
        latency_ms=1,
        input_tokens=100,
        cost_usd_override=-5.0,
    )
    assert cost == 0.0


def test_unknown_model_zero_cost(
    captured_emits: List[Dict[str, Any]],
    capture_persist: List[Dict[str, Any]],
) -> None:
    cost = us.record_usage(
        tenant_id="t",
        agent_name="a",
        model="imaginary-model",
        latency_ms=1,
        input_tokens=10_000,
        output_tokens=10_000,
    )
    assert cost == 0.0


def test_persist_failure_does_not_break_caller(
    captured_emits: List[Dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(**_: Any) -> None:
        raise RuntimeError("DB down")

    monkeypatch.setattr(us, "_persist_trace", _boom)
    # Patlamaz, cost hâlâ döner, metric hâlâ atılır
    cost = us.record_usage(
        tenant_id="t",
        agent_name="a",
        model="gpt-4o-mini",
        latency_ms=1,
        input_tokens=1_000_000,
        output_tokens=0,
    )
    assert cost == pytest.approx(0.15)
    assert len(captured_emits) == 1
