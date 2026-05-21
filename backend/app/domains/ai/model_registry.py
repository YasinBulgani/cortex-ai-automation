"""Model Registry — TEK kaynak.

`infra/registry/model_registry.yaml` dosyasını okur; backend, engine ve agents/v2
bu modül aracılığıyla model bilgilerine erişir. Dördüncü bir `_COST_TABLE` veya
`MODEL_COSTS` oluşturmak yasak — arch-guard CI kuralıyla kontrol edilir.

Kullanım:
    from app.domains.ai.model_registry import (
        get_model_info, compute_cost_usd, resolve_alias, list_models_by_tier,
    )

    info = get_model_info("claude-3-5-sonnet-latest")
    # -> ModelInfo(id="claude-sonnet-4-20250514", tier="premium", ...)

    cost = compute_cost_usd("gpt-4o-mini", input_tokens=1000, output_tokens=200)

Tasarım:
    * YAML dosyası tek kez yüklenir + hash'lenir; hot-reload için
      ``reload_registry()`` (test fixture'ları kullansın).
    * Alias -> canonical id eşlemesi çözülür; ``lookup_price("gpt-4o")``
      da ``lookup_price("openai:gpt-4o")`` da çalışır.
    * Bilinmeyen model → families prefix eşlemesi; yine yoksa 0.0 (fail-open)
      + debug log; metrik: ``llm_unknown_model_total`` incr.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

logger = logging.getLogger(__name__)


# ── Registry dosyasının konumu ────────────────────────────────────────
# Repo kökünden itibaren: infra/registry/model_registry.yaml
# Hem backend (çalıştırma yolu) hem test ortamı için path discovery.
def _find_registry_path() -> Path:
    override = os.environ.get("TWAI_MODEL_REGISTRY_PATH")
    if override:
        p = Path(override)
        if p.is_file():
            return p
        logger.warning("TWAI_MODEL_REGISTRY_PATH (%s) bulunamadı; fallback aramasına geçiliyor", override)

    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        cand = parent / "infra" / "registry" / "model_registry.yaml"
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        "model_registry.yaml bulunamadı. Repo kökünü kontrol edin veya "
        "TWAI_MODEL_REGISTRY_PATH env'i ayarlayın."
    )


@dataclass(frozen=True)
class ModelCost:
    input_per_mtok: float = 0.0
    output_per_mtok: float = 0.0
    cached_input_per_mtok: Optional[float] = None


@dataclass(frozen=True)
class ModelInfo:
    id: str
    provider: str
    tier: str  # mini | mid | premium | local
    context_window: int = 0
    max_output: int = 0
    cost: ModelCost = field(default_factory=ModelCost)
    supports_json: bool = True
    supports_tools: bool = True
    offline_safe: bool = False
    status: str = "prod"
    kind: str = "chat"  # chat | embedding | vision
    p95_ms: int = 0
    aliases: Tuple[str, ...] = ()


@dataclass
class _Registry:
    models: Dict[str, ModelInfo]      # canonical_id -> info
    alias_to_id: Dict[str, str]       # lowercased alias -> canonical_id
    families: List[Tuple[str, ModelInfo]]  # (prefix, info_proxy) sorted desc
    source_path: Path
    schema_version: int


_UNKNOWN = ModelInfo(id="__unknown__", provider="unknown", tier="mini")


def _parse_cost(raw: Optional[Dict[str, Any]]) -> ModelCost:
    if not raw:
        return ModelCost()
    return ModelCost(
        input_per_mtok=float(raw.get("input", 0.0) or 0.0),
        output_per_mtok=float(raw.get("output", 0.0) or 0.0),
        cached_input_per_mtok=(
            float(raw["cached_input"]) if raw.get("cached_input") is not None else None
        ),
    )


def _parse_model(entry: Dict[str, Any], defaults: Dict[str, Any]) -> ModelInfo:
    sla = entry.get("sla") or {}
    return ModelInfo(
        id=str(entry["id"]),
        provider=str(entry.get("provider", defaults.get("provider", "unknown"))),
        tier=str(entry.get("tier", defaults.get("tier", "mid"))),
        context_window=int(entry.get("context_window", 0) or 0),
        max_output=int(entry.get("max_output", 0) or 0),
        cost=_parse_cost(entry.get("cost")),
        supports_json=bool(entry.get("supports_json", defaults.get("supports_json", True))),
        supports_tools=bool(entry.get("supports_tools", defaults.get("supports_tools", True))),
        offline_safe=bool(entry.get("offline_safe", defaults.get("offline_safe", False))),
        status=str(entry.get("status", defaults.get("status", "prod"))),
        kind=str(entry.get("kind", "chat")),
        p95_ms=int(sla.get("p95_ms", 0) or 0),
        aliases=tuple(str(a).lower() for a in (entry.get("aliases") or [])),
    )


def _parse_family(raw: Dict[str, Any]) -> Tuple[str, ModelInfo]:
    prefix = str(raw["prefix"]).lower()
    # Aile kaydı minimal; ModelInfo proxy olarak tutulur
    info = ModelInfo(
        id=prefix,
        provider="family",
        tier=str(raw.get("tier", "mid")),
        cost=_parse_cost(raw.get("cost")),
        offline_safe=bool(raw.get("offline_safe", False)),
        kind="chat",
    )
    return prefix, info


def _load(path: Path) -> _Registry:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    defaults = data.get("defaults") or {}
    models_raw = data.get("models") or []
    families_raw = data.get("families") or []

    models: Dict[str, ModelInfo] = {}
    alias_to_id: Dict[str, str] = {}

    for entry in models_raw:
        info = _parse_model(entry, defaults)
        canon = info.id.lower()
        models[canon] = info
        alias_to_id[canon] = canon
        for alias in info.aliases:
            alias_to_id[alias] = canon

    families = [_parse_family(f) for f in families_raw]
    # Prefix match'te "en uzun eşleşme kazanır" için desc sırala
    families.sort(key=lambda x: len(x[0]), reverse=True)

    return _Registry(
        models=models,
        alias_to_id=alias_to_id,
        families=families,
        source_path=path,
        schema_version=int(data.get("schema_version", 1)),
    )


# Singleton — her zaman _get_registry() üzerinden erişilecek
_registry_singleton: Optional[_Registry] = None


def _get_registry() -> _Registry:
    global _registry_singleton
    if _registry_singleton is None:
        path = _find_registry_path()
        _registry_singleton = _load(path)
        logger.info("Model registry yüklendi: %d model, %d aile (%s)",
                    len(_registry_singleton.models),
                    len(_registry_singleton.families),
                    path)
    return _registry_singleton


def reload_registry() -> None:
    """Test fixture'ları veya hot-reload için. Üretimde kullanmayın."""
    global _registry_singleton
    _registry_singleton = None
    _get_registry()


# ── Provider prefix ayıklama ────────────────────────────────────────────
_PROVIDER_PREFIXES = frozenset({
    "openai", "anthropic", "google", "groq",
    "ollama", "vllm", "azure", "gemini",
})


def _canonicalize(model: str) -> str:
    """"openai:gpt-4o" → "gpt-4o"; "qwen2.5-coder:7b-instruct-q4_K_M" korunur."""
    name = (model or "").strip().lower()
    if ":" in name:
        prefix, rest = name.split(":", 1)
        if prefix in _PROVIDER_PREFIXES:
            return rest
    return name


# ── Public API ─────────────────────────────────────────────────────────
def resolve_alias(model: str) -> Optional[str]:
    """Alias → canonical id. Bulunmazsa None."""
    if not model:
        return None
    canon = _canonicalize(model)
    return _get_registry().alias_to_id.get(canon)


def get_model_info(model: str) -> ModelInfo:
    """Model için tam bilgi.

    Çözüm sırası:
      1. Tam id / alias match
      2. En uzun prefix match — hem registry id'leri hem aile prefix'leri
         birlikte değerlendirilir; ``gpt-4.1-mini-2025-02-01`` ``gpt-4.1``
         yerine ``gpt-4.1-mini`` ile eşleşir. Eşitlikte id önceliklidir.
      3. Bulunamazsa ``_UNKNOWN`` (cost=0, tier=mini) + debug log.
    """
    if not model:
        return _UNKNOWN

    reg = _get_registry()
    canon = _canonicalize(model)

    # 1. Tam id veya alias
    target = reg.alias_to_id.get(canon)
    if target:
        return reg.models[target]

    # 2. En uzun prefix match — registry id'leri + aile prefix'leri birlikte.
    #    Eşitlikte registry id (model-özel) aile'ye göre önceliklidir.
    best: Tuple[int, int, Optional[ModelInfo]] = (0, 0, None)  # (length, priority, info)

    for mid, info in reg.models.items():
        if canon.startswith(mid) and len(mid) > best[0]:
            best = (len(mid), 1, info)  # priority=1 (id > family)

    for prefix, family_info in reg.families:
        if canon.startswith(prefix):
            # Eşit uzunlukta id > family; daha uzunsa family kazanır
            if len(prefix) > best[0]:
                best = (len(prefix), 0, family_info)

    if best[2] is not None:
        return best[2]

    logger.debug("Registry: bilinmeyen model '%s' (canon='%s')", model, canon)
    return _UNKNOWN


def lookup_cost(model: str) -> ModelCost:
    return get_model_info(model).cost


def compute_cost_usd(
    model: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_input_tokens: int = 0,
) -> float:
    """Token → USD.

    ``cached_input_tokens`` modelde cached price varsa indirimli uygulanır;
    geri kalan input standart fiyat üzerinden.
    """
    cost = lookup_cost(model)
    total = 0.0

    if cached_input_tokens > 0 and cost.cached_input_per_mtok is not None:
        total += (cached_input_tokens / 1_000_000.0) * cost.cached_input_per_mtok
        remaining = max(0, input_tokens - cached_input_tokens)
    else:
        remaining = max(0, input_tokens)

    if remaining:
        total += (remaining / 1_000_000.0) * cost.input_per_mtok
    if output_tokens:
        total += (max(0, output_tokens) / 1_000_000.0) * cost.output_per_mtok

    return round(total, 8)


def list_models_by_tier(tier: str, *, offline_only: bool = False) -> List[ModelInfo]:
    reg = _get_registry()
    out = [
        m for m in reg.models.values()
        if m.tier == tier and (not offline_only or m.offline_safe)
    ]
    return sorted(out, key=lambda m: (m.provider, m.id))


def list_offline_models() -> List[ModelInfo]:
    return [m for m in _get_registry().models.values() if m.offline_safe]


def known_models() -> Tuple[str, ...]:
    """Tüm canonical id + alias'ları döndürür (test/inspection için)."""
    reg = _get_registry()
    return tuple(sorted(reg.alias_to_id))


# ── Geriye dönük uyumluluk: pricing.py arayüzü ─────────────────────────
# pricing.py'deki ModelPrice'a eşlenen tip (compute_cost_usd aynı isimde).
@dataclass(frozen=True)
class ModelPrice:
    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: Optional[float] = None


def lookup_price(model: str) -> ModelPrice:
    c = lookup_cost(model)
    return ModelPrice(
        input_per_mtok=c.input_per_mtok,
        output_per_mtok=c.output_per_mtok,
        cached_input_per_mtok=c.cached_input_per_mtok,
    )
