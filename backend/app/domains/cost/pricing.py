"""LLM provider fiyat tablosu — tek doğru referans (2026-04 itibarıyla).

Fiyatlar USD / 1M token (input/output). Kaynaklar:
    - OpenAI: https://openai.com/api/pricing (2026-04)
    - Anthropic: https://www.anthropic.com/pricing
    - Google: https://ai.google.dev/pricing
    - DeepSeek: https://api-docs.deepseek.com/quick_start/pricing
    - Ollama / lokal: ücretsiz (elektrik dahil değil)

Fiyat güncellemeleri bu dosyadan tek noktadan yapılır. Kod fiyatı
doğrudan okumaz; ``get_pricing(model)`` ile önbellek dostu erişim
sağlanır ve bilinmeyen model için varsayılan döner.

Not: Perakende USD fiyatı kullanılır. TRY dönüşümü runtime'da
``DEFAULT_USD_TO_TRY`` ile veya env ``USD_TO_TRY`` ile yapılır.
Gerçek zamanlı forex bir sonraki sprint'te opsiyonel olarak eklenebilir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# USD / 1 milyon token
@dataclass(frozen=True)
class PricingEntry:
    model: str
    provider: str                   # "openai" | "anthropic" | "google" | "deepseek" | "ollama" | ...
    input_per_mtoken_usd: float
    output_per_mtoken_usd: float
    is_local: bool = False          # True → maliyet 0
    is_free_tier_available: bool = False
    notes: str = ""


PRICING_CATALOG: dict[str, PricingEntry] = {
    # ─── OpenAI (2026-04) ───────────────────────────────────────────────
    "gpt-5":       PricingEntry("gpt-5",       "openai", 1.25, 10.00),
    "gpt-5.2":     PricingEntry("gpt-5.2",     "openai", 1.75, 14.00),
    "gpt-5-nano":  PricingEntry("gpt-5-nano",  "openai", 0.05, 0.40),
    "gpt-4o":      PricingEntry("gpt-4o",      "openai", 2.50, 10.00,
                                notes="Legacy, yeni projelerde gpt-5 önerilir"),
    # ─── Anthropic ──────────────────────────────────────────────────────
    "claude-sonnet-4.5": PricingEntry("claude-sonnet-4.5", "anthropic", 3.00, 15.00),
    "claude-sonnet-4.6": PricingEntry("claude-sonnet-4.6", "anthropic", 3.00, 15.00),
    "claude-opus-4.6":   PricingEntry("claude-opus-4.6",   "anthropic", 5.00, 25.00),
    # ─── Google ─────────────────────────────────────────────────────────
    "gemini-2.5-pro":   PricingEntry("gemini-2.5-pro",   "google", 1.25, 10.00),
    "gemini-2.5-flash": PricingEntry("gemini-2.5-flash", "google", 0.15, 0.60,
                                     is_free_tier_available=True),
    "gemini-3.1-pro":   PricingEntry("gemini-3.1-pro",   "google", 2.00, 12.00),
    # ─── DeepSeek ───────────────────────────────────────────────────────
    "deepseek-v3.1-reasoning":     PricingEntry(
        "deepseek-v3.1-reasoning", "deepseek", 0.55, 2.19),
    "deepseek-v3.1-non-reasoning": PricingEntry(
        "deepseek-v3.1-non-reasoning", "deepseek", 0.27, 1.10),
    # ─── Ollama lokal (ücretsiz) ─────────────────────────────────────────
    "qwen2.5-coder:7b":      PricingEntry(
        "qwen2.5-coder:7b", "ollama", 0.0, 0.0, is_local=True),
    "qwen2.5-coder:14b":     PricingEntry(
        "qwen2.5-coder:14b", "ollama", 0.0, 0.0, is_local=True),
    "qwen2.5-coder:32b":     PricingEntry(
        "qwen2.5-coder:32b", "ollama", 0.0, 0.0, is_local=True),
    "qwen2.5:14b":           PricingEntry(
        "qwen2.5:14b", "ollama", 0.0, 0.0, is_local=True),
    "qwen2.5:32b":           PricingEntry(
        "qwen2.5:32b", "ollama", 0.0, 0.0, is_local=True),
    "qwen3-coder-next":      PricingEntry(
        "qwen3-coder-next", "ollama", 0.0, 0.0, is_local=True,
        notes="MoE, 80B total / 3B aktif, Feb 2026"),
    "bge-m3":                PricingEntry(
        "bge-m3", "ollama", 0.0, 0.0, is_local=True,
        notes="Embedding modeli — lokal"),
    "mistral:latest":        PricingEntry(
        "mistral:latest", "ollama", 0.0, 0.0, is_local=True),
    "llama3.2:3b":           PricingEntry(
        "llama3.2:3b", "ollama", 0.0, 0.0, is_local=True),
}


# Bilinmeyen model için savunmacı default — orta tier bulut modeli gibi davran
# (aşırı düşük tahmin vermemek için pesimistik tutuldu).
DEFAULT_PRICING = PricingEntry(
    model="unknown",
    provider="unknown",
    input_per_mtoken_usd=1.00,
    output_per_mtoken_usd=5.00,
    notes="Bilinmeyen model — pesimistik fallback",
)


def get_pricing(model: str) -> PricingEntry:
    """Model adına göre fiyat kaydı. Bulunamazsa pesimistik default."""
    if not model:
        return DEFAULT_PRICING
    # Tam eşleşme öncelikli
    entry = PRICING_CATALOG.get(model)
    if entry is not None:
        return entry
    # Olmadı → normalize edilmiş (case-insensitive, ollama quant suffix'lerini at)
    key = model.lower().strip()
    # "qwen2.5-coder:14b-instruct-q4_K_M" → "qwen2.5-coder:14b"
    if ":" in key:
        base, _, rest = key.partition(":")
        first_tok = rest.split("-")[0]
        normalized = f"{base}:{first_tok}"
        if normalized in PRICING_CATALOG:
            return PRICING_CATALOG[normalized]
    return DEFAULT_PRICING


def estimate_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Tek bir çağrının yaklaşık USD maliyeti."""
    p = get_pricing(model)
    if p.is_local:
        return 0.0
    in_usd = (input_tokens / 1_000_000) * p.input_per_mtoken_usd
    out_usd = (output_tokens / 1_000_000) * p.output_per_mtoken_usd
    return round(in_usd + out_usd, 6)
