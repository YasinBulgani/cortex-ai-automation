"""LLM Prometheus metrikleri — Dalga 0 L1.

prometheus_client global REGISTRY kullandığı için her test için taze bir
CollectorRegistry oluşturmak yerine sayaç deltasını ölçüyoruz.
"""
from __future__ import annotations

import pytest

from app.domains.ai import metrics as m


@pytest.fixture(autouse=True)
def _ensure_prom():
    active = m.ensure_metrics()
    if not active:
        pytest.skip("prometheus_client yüklü değil")
    yield


def _counter_value(counter, **labels) -> float:
    """Label setiyle sayaç değerini okur; yoksa 0 dönmüş sayılır."""
    try:
        return counter.labels(**labels)._value.get()
    except Exception:
        return 0.0


def _histogram_count(hist, **labels) -> float:
    try:
        return hist.labels(**labels)._sum.get()
    except Exception:
        return 0.0


class TestRequestMetrics:
    def test_request_counter_increments(self):
        tenant = "test-tenant-req-inc"
        before = _counter_value(
            m.M.requests_total,
            tenant=tenant, task_type="chat", model="gpt-4o", provider="openai",
            tier="mid", status="ok",
        )
        m.record_request(
            tenant=tenant, task_type="chat", model="gpt-4o",
            provider="openai", tier="mid", status="ok",
            input_tokens=100, output_tokens=50, cost_usd=0.001, latency_ms=500,
        )
        after = _counter_value(
            m.M.requests_total,
            tenant=tenant, task_type="chat", model="gpt-4o", provider="openai",
            tier="mid", status="ok",
        )
        assert after - before == 1.0

    def test_token_counter_splits_in_out(self):
        tenant = "test-tenant-tokens"
        m.record_request(
            tenant=tenant, task_type="chat", model="gpt-4o",
            provider="openai", tier="mid", status="ok",
            input_tokens=1000, output_tokens=500, cost_usd=0.01,
        )
        inp = _counter_value(
            m.M.tokens_total,
            tenant=tenant, model="gpt-4o", provider="openai", direction="input",
        )
        out = _counter_value(
            m.M.tokens_total,
            tenant=tenant, model="gpt-4o", provider="openai", direction="output",
        )
        assert inp == 1000
        assert out == 500

    def test_cost_counter(self):
        tenant = "test-tenant-cost"
        m.record_request(
            tenant=tenant, task_type="chat", model="gpt-4o-mini",
            provider="openai", tier="mini", status="ok",
            cost_usd=0.00045,
        )
        val = _counter_value(
            m.M.cost_total,
            tenant=tenant, model="gpt-4o-mini", provider="openai", tier="mini",
        )
        assert val == pytest.approx(0.00045)


class TestCacheMetrics:
    def test_hit_and_miss(self):
        before_hit = _counter_value(
            m.M.cache_hits_total, task_type="chat", cache_kind="semantic"
        )
        m.record_cache(task_type="chat", hit=True)
        m.record_cache(task_type="chat", hit=False)
        after_hit = _counter_value(
            m.M.cache_hits_total, task_type="chat", cache_kind="semantic"
        )
        miss = _counter_value(m.M.cache_misses_total, task_type="chat")
        assert after_hit - before_hit == 1
        assert miss >= 1


class TestSafetyMetrics:
    def test_schema_violation(self):
        m.record_schema_violation(task_type="generate_test_cases", model="gpt-4o")
        val = _counter_value(
            m.M.schema_violations_total, task_type="generate_test_cases", model="gpt-4o"
        )
        assert val >= 1

    def test_pii_block_rule_label(self):
        m.record_pii_block(task_type="chat", rule="tckn")
        val = _counter_value(m.M.pii_blocks_total, task_type="chat", rule="tckn")
        assert val >= 1


class TestRefineAndRetry:
    def test_refine_histogram(self):
        m.record_refine(task_type="test_gen", iterations=3)
        # Histogram observe etti — sum artmış olmalı
        s = _histogram_count(m.M.refine_iterations, task_type="test_gen")
        assert s >= 3

    def test_retry_histogram(self):
        m.record_retry(task_type="chat", provider="openai", count=2)
        s = _histogram_count(m.M.retry_count, task_type="chat", provider="openai")
        assert s >= 2


class TestBudget:
    def test_gauge_set(self):
        m.set_budget_consumed(tenant="acme", window="daily", ratio=0.85)
        val = m.M.budget_consumed_ratio.labels(tenant="acme", window="daily")._value.get()
        assert val == pytest.approx(0.85)


class TestLabelSafety:
    def test_unknown_labels_default(self):
        m.record_request(
            tenant=None, task_type=None, model="", provider=None, tier=None, status="ok",
        )
        val = _counter_value(
            m.M.requests_total,
            tenant="unknown", task_type="unknown", model="__unknown__",
            provider="unknown", tier="mid", status="ok",
        )
        assert val >= 1

    def test_long_label_truncation(self):
        long_tenant = "x" * 200
        m.record_request(
            tenant=long_tenant, task_type="chat", model="gpt-4o",
            provider="openai", tier="mid", status="ok",
        )
        # Truncate sonrası uzunluk kontrolü (64 max)
        for sample in m.M.requests_total.collect()[0].samples:
            if sample.labels.get("task_type") == "chat":
                assert len(sample.labels["tenant"]) <= 64


class TestUnknownModelMetric:
    def test_unknown_model_counter(self):
        before = _counter_value(m.M.unknown_model_total, model="brand-new-x1")
        m.record_unknown_model("brand-new-x1")
        after = _counter_value(m.M.unknown_model_total, model="brand-new-x1")
        assert after - before == 1


class TestShadow:
    def test_shadow_divergence_observed(self):
        m.record_shadow_divergence(
            task_type="chat", shadow_tier="premium", divergence=0.1
        )
        s = _histogram_count(
            m.M.shadow_divergence, task_type="chat", shadow_tier="premium"
        )
        assert s >= 0.1
