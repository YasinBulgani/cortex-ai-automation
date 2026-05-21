"""Pricing tablosu unit testleri — regresyon koruması.

Model fiyatları değişirse bu snapshot testleri kırılır → bilinçli güncelleme
PR'ı yapılır. Belirsiz fiyat değişikliklerini engeller.
"""
from __future__ import annotations

import pytest

from app.domains.ai.pricing import (
    ModelPrice,
    compute_cost_usd,
    known_models,
    lookup_price,
)


class TestLookup:
    def test_openai_direct(self) -> None:
        p = lookup_price("gpt-4o-mini")
        assert p.input_per_mtok == 0.15
        assert p.output_per_mtok == 0.60

    def test_openai_with_prefix(self) -> None:
        p = lookup_price("openai:gpt-4o")
        assert p.input_per_mtok == 2.50

    def test_ollama_tag_strip(self) -> None:
        # "qwen2.5:32b" → "qwen2.5"
        p = lookup_price("qwen2.5:32b")
        assert p.input_per_mtok == 0.0
        assert p.output_per_mtok == 0.0

    def test_anthropic(self) -> None:
        p = lookup_price("claude-3-5-sonnet-20241022")
        assert p.input_per_mtok == 3.0
        assert p.output_per_mtok == 15.0

    def test_unknown_model_returns_zero(self) -> None:
        p = lookup_price("nonexistent-model-xyz")
        assert p.input_per_mtok == 0.0
        assert p.output_per_mtok == 0.0

    def test_date_suffix_variant_matches_prefix(self) -> None:
        # "gpt-4.1-mini-2025-02-01" benzeri → "gpt-4.1-mini"
        p = lookup_price("gpt-4.1-mini-2025-02-01")
        assert p.input_per_mtok == 0.40


class TestCompute:
    def test_basic(self) -> None:
        # gpt-4o-mini: 0.15 in / 0.60 out per 1M
        # 1M input + 500K output = 0.15 + 0.30 = 0.45 USD
        cost = compute_cost_usd(
            "gpt-4o-mini", input_tokens=1_000_000, output_tokens=500_000
        )
        assert cost == pytest.approx(0.45)

    def test_zero_tokens(self) -> None:
        assert compute_cost_usd("gpt-4o", input_tokens=0, output_tokens=0) == 0.0

    def test_unknown_model_free(self) -> None:
        # Bilinmeyen model → 0 (fail-open)
        cost = compute_cost_usd(
            "imaginary", input_tokens=10_000_000, output_tokens=10_000_000
        )
        assert cost == 0.0

    def test_cached_input_discount(self) -> None:
        # gpt-4o: 2.50 in / 10.00 out, cached 1.25
        # 100K input, 50K cached, 20K output:
        #   cached_portion = 50K * 1.25 / 1M = 0.0625
        #   remaining input = 50K * 2.50 / 1M = 0.125
        #   output = 20K * 10.00 / 1M = 0.200
        cost = compute_cost_usd(
            "gpt-4o",
            input_tokens=100_000,
            cached_input_tokens=50_000,
            output_tokens=20_000,
        )
        assert cost == pytest.approx(0.0625 + 0.125 + 0.200)

    def test_cached_without_cached_price(self) -> None:
        # Anthropic cached_input_per_mtok None → cache verilse bile standart fiyat
        # 100K input (50K cached flag'li ama indirim yok) + 0 out
        cost = compute_cost_usd(
            "claude-3-5-haiku-20241022",
            input_tokens=100_000,
            cached_input_tokens=50_000,
            output_tokens=0,
        )
        # Fallback: tüm input standart fiyat (0.80 / 1M)
        # 100K * 0.80 / 1M = 0.080
        assert cost == pytest.approx(0.080)

    def test_negative_inputs_coerced_to_zero(self) -> None:
        cost = compute_cost_usd("gpt-4o", input_tokens=-100, output_tokens=-50)
        assert cost == 0.0

    def test_ollama_always_free(self) -> None:
        cost = compute_cost_usd(
            "qwen2.5:32b", input_tokens=10_000_000, output_tokens=10_000_000
        )
        assert cost == 0.0


class TestSnapshot:
    """Kritik fiyatların regresyonu — pricing güncellenince bu test kasten kırılır."""

    def test_gpt_4o_snapshot(self) -> None:
        p = lookup_price("gpt-4o")
        assert p == ModelPrice(2.50, 10.00, cached_input_per_mtok=1.25)

    def test_claude_sonnet_4_snapshot(self) -> None:
        p = lookup_price("claude-sonnet-4-20250514")
        assert p == ModelPrice(3.00, 15.00)

    def test_gemini_2_5_flash_snapshot(self) -> None:
        p = lookup_price("gemini-2.5-flash")
        assert p == ModelPrice(0.30, 2.50)

    def test_known_models_includes_essentials(self) -> None:
        models = set(known_models())
        must_have = {
            "gpt-4o",
            "gpt-4o-mini",
            "claude-sonnet-4-20250514",
            "gemini-2.5-flash",
            "qwen2.5",
            "mistral",
        }
        missing = must_have - models
        assert not missing, f"pricing tablosunda eksik: {missing}"
