"""v2 Orchestrator konfigürasyonu — model routing + flags + limits."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import os


@dataclass
class AgentV2Config:
    # Model routing (Ollama / Profil A)
    analyst_model: str = "qwen2.5:14b-instruct-q4_K_M"
    explorer_model_fast: str = "llama3.2:3b-instruct-q4_K_M"
    explorer_model_vision: str = "qwen2-vl:7b"
    locator_model: str = "qwen2.5-coder:14b-instruct-q4_K_M"
    locator_model_vision: str = "qwen2-vl:7b"
    scenario_model: str = "qwen2.5:14b-instruct-q4_K_M"
    coder_model: str = "qwen2.5-coder:14b-instruct-q4_K_M"
    healer_model: str = "qwen2.5-coder:14b-instruct-q4_K_M"
    reviewer_model: str = "qwen2.5:14b-instruct-q4_K_M"
    reporter_model: str = "llama3.2:3b-instruct-q4_K_M"
    embedding_model: str = "bge-m3"

    cloud_fallback_enabled: bool = True
    cloud_fallback_provider: str = "gemini"

    # Hard limits
    max_tokens_per_run: int = 200_000
    max_cost_usd_per_run: float = 2.0
    max_duration_seconds: int = 900
    max_healing_iterations: int = 3
    max_explorer_pages: int = 30

    # Thresholds
    locator_stability_threshold: float = 0.70
    healing_confidence_threshold: float = 0.80
    review_auto_approve_threshold: float = 0.85

    # Observability
    langfuse_enabled: bool = True
    otel_enabled: bool = True

    # Feature flags
    vision_enabled: bool = True
    auto_pr_enabled: bool = False
    auto_merge_enabled: bool = False
    hitl_critical_keywords: list[str] = field(
        default_factory=lambda: [
            "ödeme", "transfer", "havale", "eft", "swift",
            "onay", "silme", "production", "prod",
        ]
    )

    # Sandbox
    sandbox_image: str = "mcr.microsoft.com/playwright:v1.49-jammy"
    sandbox_cpu_limit: str = "4"
    sandbox_memory_limit: str = "4Gi"
    sandbox_network_allowlist: list[str] = field(
        default_factory=lambda: [
            "staging.bank.example.tr",
            "uat.bank.example.tr",
            "*.test.internal",
        ]
    )


@lru_cache(maxsize=1)
def get_config() -> AgentV2Config:
    cfg = AgentV2Config()
    if v := os.getenv("AGENTS_V2_ANALYST_MODEL"):
        cfg.analyst_model = v
    if v := os.getenv("AGENTS_V2_MAX_COST_USD"):
        cfg.max_cost_usd_per_run = float(v)
    if os.getenv("AGENTS_V2_AUTO_PR") == "true":
        cfg.auto_pr_enabled = True
    if os.getenv("AGENTS_V2_AUTO_MERGE") == "true":
        cfg.auto_merge_enabled = True
    if os.getenv("AGENTS_V2_VISION") == "false":
        cfg.vision_enabled = False
    return cfg
