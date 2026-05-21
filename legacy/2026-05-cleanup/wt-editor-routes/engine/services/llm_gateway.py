"""
Merkezi LLM erişim katmanı.

Tüm AI servisleri bu gateway üzerinden LLM çağrısı yapar.
PII sanitization, prompt cache, model routing ve maliyet takibi sağlar.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ── PII desenleri (varsayılan — config/pii_patterns.yaml ile override edilir) ──
_DEFAULT_PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b\d{11}\b", "[TC_KIMLIK]"),
    (r"\b[Tt][Rr]\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b", "[IBAN]"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL]"),
    (r"\b05\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b", "[TELEFON]"),
]

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# ── Token başına yaklaşık maliyet (USD) ──
MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "claude-3-5-sonnet-latest": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-3-5-haiku-latest": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
}


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int
    cached: bool
    cost_usd: float
    latency_ms: int


@dataclass
class UsageStats:
    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    cache_hits: int = 0
    calls_by_model: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "cache_hits": self.cache_hits,
            "calls_by_model": self.calls_by_model,
        }


class LLMGateway:
    """Merkezi LLM erişim noktası — cache, PII sanitize, rate limit, maliyet kontrolü."""

    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        enable_cache: bool = True,
        enable_pii_sanitization: bool = True,
        budget_limit_usd: float = 100.0,
        rate_limit_per_hour: int = 100,
        cache_ttl_seconds: int = 3600,
    ):
        self._openai_key = openai_api_key
        self._anthropic_key = anthropic_api_key
        self._openai = None
        self._anthropic = None
        self.enable_cache = enable_cache
        self.enable_pii_sanitization = enable_pii_sanitization
        self.budget_limit = budget_limit_usd
        self.rate_limit_per_hour = rate_limit_per_hour
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[LLMResponse, float]] = {}
        self._call_timestamps: list[float] = []
        self.stats = UsageStats()
        self._pii_patterns = self._load_pii_patterns()
        self._apply_yaml_config()
        # Explicit constructor args override yaml values
        if budget_limit_usd != 100.0:
            self.budget_limit = budget_limit_usd
        if rate_limit_per_hour != 100:
            self.rate_limit_per_hour = rate_limit_per_hour
        if cache_ttl_seconds != 3600:
            self.cache_ttl_seconds = cache_ttl_seconds

    # ── public ──────────────────────────────────────────────────────────────

    def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Senkron LLM çağrısı — rate limit, budget, cache, PII koruması ile."""
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o")

        if self.stats.total_cost_usd >= self.budget_limit:
            raise RuntimeError(
                f"LLM bütçe limiti aşıldı: ${self.stats.total_cost_usd:.2f} >= ${self.budget_limit:.2f}"
            )

        self._enforce_rate_limit()

        if self.enable_pii_sanitization:
            messages = self._sanitize_messages(messages)

        cache_key = self._cache_key(messages, model, temperature)
        if self.enable_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                self.stats.cache_hits += 1
                return LLMResponse(
                    content=cached.content,
                    model=cached.model,
                    tokens_used=0,
                    cached=True,
                    cost_usd=0.0,
                    latency_ms=0,
                )

        start = time.monotonic()

        if model.startswith("claude"):
            response = self._call_anthropic(messages, model, temperature, max_tokens)
        else:
            response = self._call_openai(messages, model, temperature, max_tokens)

        response.latency_ms = int((time.monotonic() - start) * 1000)
        self._update_stats(response)

        if self.enable_cache:
            self._cache[cache_key] = (response, time.monotonic())

        return response

    @property
    def has_openai(self) -> bool:
        return bool(self._openai_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self._anthropic_key)

    @property
    def available(self) -> bool:
        return self.has_openai or self.has_anthropic

    # ── OpenAI ──────────────────────────────────────────────────────────────

    def _get_openai(self):
        if self._openai is None:
            from openai import OpenAI
            self._openai = OpenAI(
                api_key=self._openai_key,
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            )
        return self._openai

    def _call_openai(self, messages, model, temperature, max_tokens) -> LLMResponse:
        if not self._openai_key:
            raise RuntimeError("OpenAI API anahtarı yapılandırılmamış")
        client = self._get_openai()
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = resp.usage
        tokens = usage.total_tokens if usage else 0
        cost = self._calculate_cost(model, usage.prompt_tokens, usage.completion_tokens) if usage else 0.0
        content = ""
        if resp.choices:
            content = resp.choices[0].message.content or ""
        return LLMResponse(
            content=content,
            model=model,
            tokens_used=tokens,
            cached=False,
            cost_usd=cost,
            latency_ms=0,
        )

    # ── Anthropic ───────────────────────────────────────────────────────────

    def _get_anthropic(self):
        if self._anthropic is None:
            from anthropic import Anthropic
            self._anthropic = Anthropic(api_key=self._anthropic_key)
        return self._anthropic

    def _call_anthropic(self, messages, model, temperature, max_tokens) -> LLMResponse:
        if not self._anthropic_key:
            raise RuntimeError("Anthropic API anahtarı yapılandırılmamış")
        client = self._get_anthropic()
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = client.messages.create(
            model=model,
            system=system_msg,
            messages=user_msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        input_t = resp.usage.input_tokens
        output_t = resp.usage.output_tokens
        cost = self._calculate_cost(model, input_t, output_t)
        return LLMResponse(
            content=resp.content[0].text,
            model=model,
            tokens_used=input_t + output_t,
            cached=False,
            cost_usd=cost,
            latency_ms=0,
        )

    # ── PII ─────────────────────────────────────────────────────────────────

    def _sanitize_messages(self, messages: list[dict]) -> list[dict]:
        sanitized = []
        for msg in messages:
            content = msg.get("content", "")
            for pattern, replacement in self._pii_patterns:
                content = re.sub(pattern, replacement, content)
            sanitized.append({**msg, "content": content})
        return sanitized

    def _load_pii_patterns(self) -> list[tuple[str, str]]:
        pii_file = _CONFIG_DIR / "pii_patterns.yaml"
        if pii_file.exists():
            try:
                data = yaml.safe_load(pii_file.read_text())
                if isinstance(data, dict):
                    patterns = [(p["regex"], p["replacement"]) for p in data.get("patterns", [])]
                    if patterns:
                        return patterns
            except Exception as exc:
                logger.debug("pii_patterns.yaml okunamadı, varsayılan desenler: %s", exc)
        return _DEFAULT_PII_PATTERNS

    # ── rate limiting ────────────────────────────────────────────────────────

    def _enforce_rate_limit(self):
        """Saatlik çağrı sayısını kontrol eder, aşılırsa RuntimeError fırlatır."""
        now = time.monotonic()
        one_hour_ago = now - 3600
        self._call_timestamps = [t for t in self._call_timestamps if t > one_hour_ago]
        if len(self._call_timestamps) >= self.rate_limit_per_hour:
            raise RuntimeError(
                f"Rate limit aşıldı: {len(self._call_timestamps)}/{self.rate_limit_per_hour} çağrı/saat"
            )
        self._call_timestamps.append(now)

    def _get_from_cache(self, key: str) -> LLMResponse | None:
        """TTL-aware cache lookup."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        response, timestamp = entry
        if time.monotonic() - timestamp > self.cache_ttl_seconds:
            del self._cache[key]
            return None
        return response

    # ── yaml config ─────────────────────────────────────────────────────────

    def _apply_yaml_config(self):
        """ai_config.yaml ve llm_models.yaml'dan çalışma zamanı ayarlarını yükler."""
        ai_cfg_file = _CONFIG_DIR / "ai_config.yaml"
        if ai_cfg_file.exists():
            try:
                cfg = yaml.safe_load(ai_cfg_file.read_text())
                if isinstance(cfg, dict):
                    llm_cfg = cfg.get("llm", {})
                    if "budget_limit_usd" in llm_cfg:
                        self.budget_limit = float(llm_cfg["budget_limit_usd"])
                    if "cache_enabled" in llm_cfg:
                        self.enable_cache = bool(llm_cfg["cache_enabled"])
                    if "pii_sanitization" in llm_cfg:
                        self.enable_pii_sanitization = bool(llm_cfg["pii_sanitization"])
                    if "rate_limit_per_hour" in llm_cfg:
                        self.rate_limit_per_hour = int(llm_cfg["rate_limit_per_hour"])
                    if "cache_ttl_seconds" in llm_cfg:
                        self.cache_ttl_seconds = int(llm_cfg["cache_ttl_seconds"])
            except Exception as exc:
                logger.debug("ai_config.yaml okunamadı: %s", exc)

        models_file = _CONFIG_DIR / "llm_models.yaml"
        if models_file.exists():
            try:
                data = yaml.safe_load(models_file.read_text())
                if isinstance(data, dict):
                    for model_name, info in data.get("models", {}).items():
                        if not isinstance(info, dict):
                            continue
                        c_in = info.get("cost_per_million_input")
                        c_out = info.get("cost_per_million_output")
                        if c_in is not None and c_out is not None:
                            MODEL_COSTS[model_name] = {
                                "input": float(c_in) / 1_000_000,
                                "output": float(c_out) / 1_000_000,
                            }
            except Exception as exc:
                logger.debug("llm_models.yaml okunamadı: %s", exc)

    # ── cache / cost ────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(messages, model, temperature) -> str:
        raw = json.dumps({"m": messages, "model": model, "t": temperature}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        costs = MODEL_COSTS.get(model, MODEL_COSTS.get("gpt-4o", {"input": 0, "output": 0}))
        return input_tokens * costs["input"] + output_tokens * costs["output"]

    def _update_stats(self, response: LLMResponse):
        self.stats.total_calls += 1
        self.stats.total_tokens += response.tokens_used
        self.stats.total_cost_usd += response.cost_usd
        bucket = self.stats.calls_by_model.setdefault(
            response.model, {"calls": 0, "tokens": 0, "cost": 0.0}
        )
        bucket["calls"] += 1
        bucket["tokens"] += response.tokens_used
        bucket["cost"] = round(bucket["cost"] + response.cost_usd, 6)
