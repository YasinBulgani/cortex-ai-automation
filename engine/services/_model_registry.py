"""Engine-taraf model registry okuyucu — ``infra/registry/model_registry.yaml``.

Bu dosya ``backend/app/domains/ai/model_registry.py`` ile aynı YAML'ı okur.
Kasıtlı olarak küçük bir duplikasyondur: engine bağımsız deploy edilebilir;
backend paketine runtime dependency yaratmayalım. Veri kaynağı TEK (YAML).

Eğer engine ve backend aynı process'te çalışıyorsa ``backend`` tarafının
tam sürümü ``get_model_info`` / ``compute_cost_usd`` zaten import edilebilir.
Engine direct-mode çağrılarında bu hafif sürüm yeterli.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


def _find_yaml() -> Optional[Path]:
    override = os.environ.get("TWAI_MODEL_REGISTRY_PATH")
    if override:
        p = Path(override)
        if p.is_file():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "infra" / "registry" / "model_registry.yaml"
        if cand.is_file():
            return cand
    return None


@dataclass(frozen=True)
class EngineModelInfo:
    id: str
    provider: str
    tier: str
    input_per_mtok: float
    output_per_mtok: float
    offline_safe: bool = False
    supports_json: bool = True

    @property
    def cost(self) -> Dict[str, float]:
        """Eski engine MODEL_COSTS formatı — per-token, not per-million."""
        return {
            "input": self.input_per_mtok / 1_000_000.0,
            "output": self.output_per_mtok / 1_000_000.0,
        }


_UNKNOWN = EngineModelInfo(
    id="__unknown__", provider="unknown", tier="mini",
    input_per_mtok=0.0, output_per_mtok=0.0,
)


@dataclass
class _Cache:
    models: Dict[str, EngineModelInfo] = field(default_factory=dict)
    alias_to_id: Dict[str, str] = field(default_factory=dict)
    families: List[Tuple[str, EngineModelInfo]] = field(default_factory=list)
    loaded: bool = False


_cache = _Cache()


def _parse_entry(entry: Dict[str, Any], defaults: Dict[str, Any]) -> EngineModelInfo:
    cost = entry.get("cost") or {}
    return EngineModelInfo(
        id=str(entry["id"]),
        provider=str(entry.get("provider", defaults.get("provider", "unknown"))),
        tier=str(entry.get("tier", defaults.get("tier", "mid"))),
        input_per_mtok=float(cost.get("input", 0.0) or 0.0),
        output_per_mtok=float(cost.get("output", 0.0) or 0.0),
        offline_safe=bool(entry.get("offline_safe", defaults.get("offline_safe", False))),
        supports_json=bool(entry.get("supports_json", defaults.get("supports_json", True))),
    )


def _load() -> None:
    path = _find_yaml()
    if not path:
        logger.warning("Engine: model_registry.yaml bulunamadı; boş cache ile devam")
        _cache.loaded = True
        return
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:
        logger.warning("Engine: model registry okunamadı (%s): %s", path, exc)
        _cache.loaded = True
        return

    defaults = data.get("defaults") or {}
    for entry in data.get("models") or []:
        info = _parse_entry(entry, defaults)
        canon = info.id.lower()
        _cache.models[canon] = info
        _cache.alias_to_id[canon] = canon
        for alias in entry.get("aliases") or []:
            _cache.alias_to_id[str(alias).lower()] = canon

    for fam in data.get("families") or []:
        prefix = str(fam["prefix"]).lower()
        cost = fam.get("cost") or {}
        info = EngineModelInfo(
            id=prefix,
            provider="family",
            tier=str(fam.get("tier", "mid")),
            input_per_mtok=float(cost.get("input", 0.0) or 0.0),
            output_per_mtok=float(cost.get("output", 0.0) or 0.0),
            offline_safe=bool(fam.get("offline_safe", False)),
        )
        _cache.families.append((prefix, info))

    _cache.families.sort(key=lambda x: len(x[0]), reverse=True)
    _cache.loaded = True


def _ensure_loaded() -> None:
    if not _cache.loaded:
        _load()


_PROVIDER_PREFIXES = frozenset({
    "openai", "anthropic", "google", "groq",
    "ollama", "vllm", "azure", "gemini",
})


def _canon(model: str) -> str:
    name = (model or "").strip().lower()
    if ":" in name:
        prefix, rest = name.split(":", 1)
        if prefix in _PROVIDER_PREFIXES:
            return rest
    return name


def get_model_info(model: str) -> EngineModelInfo:
    _ensure_loaded()
    if not model:
        return _UNKNOWN
    canon = _canon(model)
    target = _cache.alias_to_id.get(canon)
    if target:
        return _cache.models[target]

    best_len = 0
    best: Optional[EngineModelInfo] = None
    for mid, info in _cache.models.items():
        if canon.startswith(mid) and len(mid) > best_len:
            best_len = len(mid)
            best = info
    for prefix, info in _cache.families:
        if canon.startswith(prefix) and len(prefix) > best_len:
            best_len = len(prefix)
            best = info
    return best or _UNKNOWN


def compute_cost_usd(model: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
    info = get_model_info(model)
    return (
        input_tokens * info.input_per_mtok / 1_000_000.0
        + output_tokens * info.output_per_mtok / 1_000_000.0
    )


def build_legacy_model_costs() -> Dict[str, Dict[str, float]]:
    """Eski engine API'si: ``MODEL_COSTS[model]["input"|"output"]`` (per-token)."""
    _ensure_loaded()
    out: Dict[str, Dict[str, float]] = {}
    for canon, info in _cache.models.items():
        out[canon] = info.cost
    # alias'ları da koy (geriye dönük lookup)
    for alias, canonical in _cache.alias_to_id.items():
        if alias != canonical and canonical in _cache.models:
            out[alias] = _cache.models[canonical].cost
    return out
