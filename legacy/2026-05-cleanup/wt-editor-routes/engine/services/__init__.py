"""
TestwrightAI AI Test Engine — Servis Katmanı

Tüm AI destekli test otomasyon servisleri bu pakette yer alır.
Her servis bağımsız çalışır ve LLM Gateway üzerinden merkezi LLM erişimi kullanır.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from .llm_gateway import LLMGateway

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@lru_cache(maxsize=1)
def get_ai_config() -> dict[str, Any]:
    """ai_config.yaml'dan merkezi AI konfigürasyonunu yükler."""
    cfg_file = _CONFIG_DIR / "ai_config.yaml"
    if cfg_file.exists():
        try:
            data = yaml.safe_load(cfg_file.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def is_feature_enabled(feature_name: str) -> bool:
    """ai_config.yaml'daki feature flag'i kontrol eder."""
    cfg = get_ai_config()
    if not cfg.get("ai", {}).get("enabled", True):
        return False
    features = cfg.get("ai", {}).get("features", {})
    return bool(features.get(feature_name, False))


@lru_cache(maxsize=1)
def get_llm_gateway() -> LLMGateway:
    """Singleton LLM Gateway instance döndürür."""
    from .llm_gateway import LLMGateway

    return LLMGateway(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        enable_cache=os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true",
        enable_pii_sanitization=os.getenv("LLM_PII_SANITIZATION", "true").lower() == "true",
        budget_limit_usd=float(os.getenv("LLM_BUDGET_LIMIT_USD", "100")),
        rate_limit_per_hour=int(os.getenv("LLM_RATE_LIMIT_PER_HOUR", "100")),
        cache_ttl_seconds=int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600")),
    )
