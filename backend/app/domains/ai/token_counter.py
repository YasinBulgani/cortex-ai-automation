"""
Pre-flight token counter — LLM cagrisi once tokenize et, max_tokens'i akilli ayarla.

Ihtiyac:
    * 128K context modellere bile buyuk RAG context + few-shot + system prompt
      sigmayabilir. Erken reddet, wasted cost olmasin.
    * max_tokens = context_limit - input_tokens - safety_buffer
      dogru hesaplanmali, yoksa gateway 400 donerken saniye kaybediyoruz.

Strateji:
    1) tiktoken varsa gerçek sayim (OpenAI modelleri).
    2) Yoksa fallback: len(text) / 4 (kaba TR/EN ortalamasi).
    3) Model context limits tablosu — her model için max toplam token.

Kullanim:
    from app.domains.ai.token_counter import count_tokens, plan_tokens

    plan = plan_tokens(
        model="gpt-4o",
        messages=[{"role": "system", "content": sys}, {"role": "user", "content": usr}],
        requested_max_output=4096,
    )
    # plan.fits, plan.input_tokens, plan.allowed_output_tokens, plan.reason
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Model baglam (context) limitleri — toplam (input+output) token.
# Kaynak: OpenAI/Anthropic dokumantasyon 2026 Q1 donemi.
_MODEL_CONTEXT_LIMITS: dict[str, int] = {
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_000_000,
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    "o1": 200_000,
    "o1-mini": 128_000,
    "o3-mini": 200_000,
    # Anthropic
    "claude-sonnet-4-20250514": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-5-haiku-20241022": 200_000,
    "claude-opus-4-20250514": 200_000,
    # Google
    "gemini-2.5-pro": 2_097_152,
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.0-flash": 1_048_576,
    # On-prem
    "qwen2.5": 32_768,
    "qwen2.5-coder": 32_768,
    "mistral": 32_768,
    "llama3": 8_192,
}

# Guvenlik payi — hesaplamada %5 veya min 500 token boslugu birakir
_SAFETY_BUFFER_PCT = 0.05
_SAFETY_BUFFER_MIN = 500


def _canonicalize_model(model: str) -> str:
    """pricing._canonicalize ile tutarli — tag/prefix temizle."""
    name = (model or "").strip().lower()
    if ":" in name:
        prefix, rest = name.split(":", 1)
        providers = {"openai", "anthropic", "google", "groq", "ollama", "vllm", "azure"}
        if prefix in providers:
            name = rest
        else:
            name = prefix
    return name


def context_limit(model: str) -> int:
    """Modelin toplam context limit'i (token). Bilinmiyorsa 32K default."""
    canon = _canonicalize_model(model)
    if canon in _MODEL_CONTEXT_LIMITS:
        return _MODEL_CONTEXT_LIMITS[canon]
    # Prefix match (tarih suffix'li modelere esnekli)
    for key, limit in _MODEL_CONTEXT_LIMITS.items():
        if canon.startswith(key):
            return limit
    logger.debug("Model %s için context limit bilinmiyor, 32K varsayildi", model)
    return 32_768


@lru_cache(maxsize=8)
def _encoder_for_model(model: str):
    """tiktoken encoder al (cache'li). Basarisizlik None doner."""
    try:
        import tiktoken  # type: ignore
        canon = _canonicalize_model(model)
        try:
            return tiktoken.encoding_for_model(canon)
        except KeyError:
            # Bilinmeyen model -> generic cl100k_base (gpt-4/gpt-3.5)
            return tiktoken.get_encoding("cl100k_base")
    except Exception as exc:
        logger.debug("tiktoken yuklenemedi: %s", exc)
        return None


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Token sayimi. tiktoken varsa kesin, yoksa ~len/4."""
    if not text:
        return 0
    enc = _encoder_for_model(model)
    if enc is not None:
        try:
            return len(enc.encode(text))
        except Exception:
            pass
    # Fallback: kaba tahmin
    return max(1, len(text) // 4)


def count_messages_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    """Chat messages listesinin toplam token'i.

    OpenAI "3 token per message overhead" kuralini kullanir (yaklasik).
    """
    total = 0
    for msg in messages or []:
        role = msg.get("role", "")
        content = msg.get("content", "")
        total += count_tokens(role, model) + count_tokens(content, model) + 3
    total += 3  # reply priming overhead
    return total


# ─────────────────────────────────────────────────────────────────────────
# Pre-flight planning
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class TokenPlan:
    model: str
    context_limit: int
    input_tokens: int
    requested_max_output: int
    allowed_output_tokens: int
    fits: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "context_limit": self.context_limit,
            "input_tokens": self.input_tokens,
            "requested_max_output": self.requested_max_output,
            "allowed_output_tokens": self.allowed_output_tokens,
            "fits": self.fits,
            "reason": self.reason,
        }


def plan_tokens(
    model: str,
    messages: list[dict] | None = None,
    *,
    input_text: str | None = None,
    requested_max_output: int = 4096,
) -> TokenPlan:
    """
    Prompt'u ve istenen max_output'u verilen modele sigdir.

    Args:
        model:                Hedef model (gpt-4o, claude-sonnet-4, ...)
        messages:             Chat messages (dict list)
        input_text:           Alternatif: tek string (gpt-style completion)
        requested_max_output: Istenen max cikti tokeni

    Returns:
        TokenPlan — fits=False ise caller prompt'u kirpmali veya red vermeli.
    """
    limit = context_limit(model)

    if messages:
        input_tokens = count_messages_tokens(messages, model)
    elif input_text:
        input_tokens = count_tokens(input_text, model)
    else:
        input_tokens = 0

    safety = max(_SAFETY_BUFFER_MIN, int(limit * _SAFETY_BUFFER_PCT))
    available = limit - input_tokens - safety

    if available <= 0:
        return TokenPlan(
            model=model,
            context_limit=limit,
            input_tokens=input_tokens,
            requested_max_output=requested_max_output,
            allowed_output_tokens=0,
            fits=False,
            reason=(
                f"input {input_tokens} token + {safety} safety buffer "
                f"model limit {limit}'e sigmiyor"
            ),
        )

    allowed = min(requested_max_output, available)
    fits = allowed >= 256  # Minimum uretken cikti
    reason = (
        "ok"
        if allowed == requested_max_output
        else f"max_tokens {requested_max_output}'den {allowed}'a indirildi (input {input_tokens} token)"
    )
    if not fits:
        reason = f"yeterli cikti tokeni kalmadi ({allowed} < 256)"

    return TokenPlan(
        model=model,
        context_limit=limit,
        input_tokens=input_tokens,
        requested_max_output=requested_max_output,
        allowed_output_tokens=allowed,
        fits=fits,
        reason=reason,
    )
