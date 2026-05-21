"""
AI Config Loader — Merkezi AI konfigürasyon yöneticisi.

ai_engine_config.json, ai_bdd_config.yaml ve synthetic_data_config.json
dosyalarını yükler ve ilgili modüllere dağıtır.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def load_ai_engine_config() -> dict[str, Any]:
    """ai_engine_config.json dosyasını yükle ve cache'le."""
    path = _CONFIG_DIR / "ai_engine_config.json"
    if not path.exists():
        logger.warning("ai_engine_config.json not found at %s", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ai_engine", data)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load ai_engine_config.json: %s", e)
        return {}


@lru_cache(maxsize=1)
def load_bdd_config() -> dict[str, Any]:
    """ai_bdd_config.yaml dosyasını yükle ve cache'le."""
    path = _CONFIG_DIR / "ai_bdd_config.yaml"
    if not path.exists():
        return {}
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("bdd_generator", data) if data else {}
    except Exception as e:
        logger.error("Failed to load ai_bdd_config.yaml: %s", e)
        return {}


@lru_cache(maxsize=1)
def load_synthetic_data_config() -> dict[str, Any]:
    """synthetic_data_config.json dosyasını yükle."""
    path = _CONFIG_DIR / "synthetic_data_config.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("synthetic_data", data)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load synthetic_data_config.json: %s", e)
        return {}


def get_self_healing_config() -> dict:
    """Self-healing modülü konfigürasyonu."""
    cfg = load_ai_engine_config()
    return cfg.get("self_healing", {
        "enabled": True,
        "confidence_threshold": 0.85,
        "auto_apply": True,
        "max_retry": 3,
    })


def get_prioritizer_config() -> dict:
    """Test prioritizer konfigürasyonu."""
    cfg = load_ai_engine_config()
    return cfg.get("test_prioritizer", {
        "enabled": True,
        "risk_threshold": 0.30,
        "always_run_tags": ["@smoke", "@critical", "@P0"],
    })


def get_bdd_generator_config() -> dict:
    """BDD generator konfigürasyonu — YAML'dan yükler."""
    cfg = load_bdd_config()
    if cfg:
        return cfg
    engine_cfg = load_ai_engine_config()
    return engine_cfg.get("bdd_generator", {
        "enabled": True,
        "output_dir": "features/generated",
        "max_scenarios_per_feature": 15,
    })


def get_coverage_config() -> dict:
    """Coverage analyzer konfigürasyonu."""
    cfg = load_ai_engine_config()
    return cfg.get("coverage_analyzer", {
        "enabled": True,
        "target_coverage_pct": 85,
    })


def get_feedback_loop_config() -> dict:
    """Feedback loop konfigürasyonu."""
    cfg = load_ai_engine_config()
    return cfg.get("feedback_loop", {
        "enabled": True,
        "history_retention_runs": 200,
        "flaky_threshold": 0.30,
        "auto_quarantine": True,
    })


def get_performance_config() -> dict:
    """Performance analyzer konfigürasyonu."""
    cfg = load_ai_engine_config()
    return cfg.get("performance", {
        "enabled": True,
        "threshold_tolerance_factor": 1.2,
        "regression_threshold_pct": 20,
    })


def get_security_config() -> dict:
    """Security analyzer konfigürasyonu."""
    cfg = load_ai_engine_config()
    return cfg.get("security", {
        "enabled": True,
        "header_analysis": True,
        "form_analysis": True,
    })
