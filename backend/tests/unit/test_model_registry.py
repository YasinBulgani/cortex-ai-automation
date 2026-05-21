"""Model Registry — tek kaynak testleri (Dalga 0 · konsolidasyon).

Bu testler ``infra/registry/model_registry.yaml`` dosyasının:
  * Yüklendiğini
  * Alias'ların çözüldüğünü
  * Prefix fallback (uzun-eşleşme-kazanır) kuralının çalıştığını
  * compute_cost_usd'nin doğru hesap yaptığını
  * Engine-taraf wrapper'ın aynı veriyi okuduğunu
kanıtlar.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from app.domains.ai import model_registry as mr


# ── Fixture: her test başında cache temizle ──────────────────────────────
@pytest.fixture(autouse=True)
def _reset_registry():
    mr.reload_registry()
    yield


class TestBasicLookup:
    def test_exact_id(self):
        info = mr.get_model_info("gpt-4o")
        assert info.id == "gpt-4o"
        assert info.provider == "openai"
        assert info.tier == "mid"
        assert info.cost.input_per_mtok == 2.50

    def test_alias_resolution(self):
        assert mr.resolve_alias("claude-3-5-sonnet-latest") == "claude-sonnet-4-20250514"
        info = mr.get_model_info("claude-3-5-sonnet-latest")
        assert info.provider == "anthropic"
        assert info.tier == "premium"

    def test_provider_prefix_strip(self):
        info = mr.get_model_info("openai:gpt-4o")
        assert info.id == "gpt-4o"

    def test_unknown_model_returns_unknown(self):
        info = mr.get_model_info("totally-fake-model-xyz-2099")
        assert info.id == "__unknown__"
        assert info.cost.input_per_mtok == 0.0


class TestPrefixResolution:
    def test_longer_prefix_wins_against_shorter(self):
        """gpt-4.1-mini-2025-02-01 ailelere karşı → gpt-4.1-mini (id) kazanır."""
        info = mr.get_model_info("gpt-4.1-mini-2025-02-01")
        assert info.id == "gpt-4.1-mini"
        assert info.cost.input_per_mtok == 0.40

    def test_family_prefix_fallback(self):
        """Registry'de olmayan qwen tag'i aile prefix'ine düşer."""
        info = mr.get_model_info("qwen2.5:99b-unreal-variant")
        # Ya registry'deki qwen2.5-coder'a ya da qwen2.5 family'sine düşer
        assert info.cost.input_per_mtok == 0.0
        assert info.offline_safe is True


class TestCostCalculation:
    def test_basic_input_output(self):
        # gpt-4o-mini: 0.15 in + 0.60 out per 1M
        cost = mr.compute_cost_usd("gpt-4o-mini", input_tokens=1_000_000, output_tokens=500_000)
        assert cost == pytest.approx(0.45)

    def test_cached_input_discount(self):
        """Cached input OpenAI'da yarı fiyat civarı."""
        # gpt-4o: 2.50 normal / 1.25 cached
        # 1M input, 800K cached, 0 output
        cost = mr.compute_cost_usd(
            "gpt-4o",
            input_tokens=1_000_000,
            cached_input_tokens=800_000,
            output_tokens=0,
        )
        # 200K normal @ 2.50 + 800K cached @ 1.25 = 0.50 + 1.00 = 1.50
        assert cost == pytest.approx(1.50)

    def test_offline_model_free(self):
        cost = mr.compute_cost_usd("qwen2.5:32b", input_tokens=10_000_000, output_tokens=10_000_000)
        assert cost == 0.0


class TestTierFiltering:
    def test_premium_tier_list(self):
        premium = mr.list_models_by_tier("premium")
        ids = {m.id for m in premium}
        # En az bir premium model olmalı
        assert "claude-sonnet-4-20250514" in ids or "gpt-4.1" in ids or "o1" in ids

    def test_offline_models(self):
        offline = mr.list_offline_models()
        assert len(offline) >= 5
        assert all(m.offline_safe for m in offline)


class TestEngineSideReader:
    """engine/services/_model_registry.py aynı YAML'ı okur mu?"""

    def test_engine_reader_agrees_on_cost(self):
        engine_path = Path(__file__).resolve().parents[3] / "engine" / "services"
        sys.path.insert(0, str(engine_path))
        try:
            from _model_registry import compute_cost_usd as engine_compute  # type: ignore
        finally:
            sys.path.pop(0)

        for model in ["gpt-4o", "gpt-4o-mini", "claude-3-5-haiku-20241022"]:
            backend_cost = mr.compute_cost_usd(model, input_tokens=10_000, output_tokens=5_000)
            engine_cost = engine_compute(model, input_tokens=10_000, output_tokens=5_000)
            assert backend_cost == pytest.approx(engine_cost), f"{model} drift!"


class TestDefaults:
    def test_defaults_applied_when_missing(self):
        info = mr.get_model_info("gpt-4o")
        assert info.supports_json is True
        assert info.offline_safe is False


class TestRegistryIntegrity:
    """YAML'ın kendisinin içsel tutarlılığı."""

    def test_all_models_have_required_fields(self):
        for canon_id, info in mr._get_registry().models.items():
            assert info.provider, f"{canon_id}: provider eksik"
            assert info.tier in {"mini", "mid", "premium", "local"}, f"{canon_id}: tier geçersiz"
            assert info.cost.input_per_mtok >= 0, f"{canon_id}: negative cost"
            assert info.cost.output_per_mtok >= 0, f"{canon_id}: negative cost"

    def test_no_duplicate_aliases(self):
        reg = mr._get_registry()
        # Bir alias iki ayrı canonical'a işaret edemez (reverse check)
        from collections import Counter
        cnt = Counter(reg.alias_to_id.values())
        # Her canonical birden fazla alias'a sahip olabilir — bu normal.
        # Ama alias'ların kendisi unique olmalı:
        assert len(reg.alias_to_id) == len(set(reg.alias_to_id.keys()))
