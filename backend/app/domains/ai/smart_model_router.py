"""
Smart Model Router — OpenAI + Anthropic tier'lı, maliyet-farkında yonlendirme.

Tier mimarisi:
    MINI    → gpt-4o-mini        (ucuz/hizli; chat, basit spec analysis)
    MID     → gpt-4o             (dengeli; test_generation medium, code_generation)
    PREMIUM → claude-sonnet-4    (karmasik muhakeme; security_audit, financial,
                                  chain_builder, quality_judge)
    LOCAL   → qwen2.5:32b        (son care; tüm bulut saglayicilar dustugunde)

Karar matrisi:
    security_audit + critical        → PREMIUM (temp 0.10)
    security_audit + other           → PREMIUM (temp 0.15)
    test_generation + financial/PII  → PREMIUM
    test_generation + medium         → MID
    test_generation + low + simple   → MINI
    chain_builder                    → PREMIUM
    spec_analysis <=5 endpoint       → MINI
    spec_analysis >5 veya financial  → MID
    code_generation                  → MID
    quality_judge                    → PREMIUM
    chat / default                   → MINI

Fallback zinciri (circuit breaker acildiginda):
    PREMIUM → MID → MINI → LOCAL

Global override (settings.ai_routing_mode):
    - "cost_optimized" → PREMIUM -> MID (quality_judge haric)
    - "balanced"       → default karar matrisi
    - "quality_first"  → MINI -> MID, MID -> PREMIUM

Feature flag ``ai.router.v2``:
    Kapaliysa guvenli default (MINI) — acil kapatma için.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple

from app.config import settings
from app.domains.ai.pricing import compute_cost_usd

logger = logging.getLogger(__name__)


# ============================================================================
# TIER ENUM
# ============================================================================


class Tier(str, Enum):
    """Maliyet/yetkinlik ekseninde dort seviye."""

    MINI = "mini"        # gpt-4o-mini — ucuz/hizli
    MID = "mid"          # gpt-4o — dengeli
    PREMIUM = "premium"  # claude-sonnet-4 — karmasik muhakeme
    LOCAL = "local"      # qwen2.5:32b — son care fallback


# ============================================================================
# DATACLASS
# ============================================================================


@dataclass
class ModelRecommendation:
    """Model yonlendirme sonucu."""

    model: str
    tier: Tier
    temperature: float
    max_tokens: int
    reason: str
    estimated_cost_usd: float = 0.0


# ============================================================================
# TIER → MODEL RESOLUTION
# ============================================================================


def _resolve(tier: Tier) -> str:
    """Tier'dan concrete model adina cevir. Config'ten okur."""
    if tier is Tier.MINI:
        return settings.openai_mini_model
    if tier is Tier.MID:
        return settings.openai_mid_model
    if tier is Tier.PREMIUM:
        if settings.anthropic_api_key:
            return settings.anthropic_premium_model
        if getattr(settings, "allow_provider_fallback", True) and getattr(settings, "openai_api_key", ""):
            logger.debug("Anthropic anahtari yok, PREMIUM için %s kullanilacak", settings.openai_model)
            return settings.openai_model
        raise RuntimeError(
            "AI provider 'anthropic' secili ama ANTHROPIC_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )
    # Tier.LOCAL
    return settings.ollama_fallback_model


def _model_tier(model: str) -> Tier:
    """Ters cevirme — concrete model adindan tier bul (metrik/log için)."""
    if model == settings.openai_mini_model:
        return Tier.MINI
    if model == settings.anthropic_premium_model:
        return Tier.PREMIUM
    if model == settings.ollama_fallback_model:
        return Tier.LOCAL
    return Tier.MID


# ============================================================================
# CIRCUIT BREAKER STATE
# ============================================================================


_circuit_state: Dict[str, Tuple[int, float]] = {}
_CIRCUIT_THRESHOLD = 3
_CIRCUIT_RESET_SECS = 300.0


def record_circuit_failure(model: str) -> None:
    count, _ = _circuit_state.get(model, (0, 0.0))
    _circuit_state[model] = (count + 1, time.time())


def record_circuit_success(model: str) -> None:
    if model in _circuit_state:
        _circuit_state[model] = (0, 0.0)


def should_fallback(model: str) -> bool:
    state = _circuit_state.get(model)
    if state is None:
        return False
    count, last_failure = state
    if count < _CIRCUIT_THRESHOLD:
        return False
    elapsed = time.time() - last_failure
    if elapsed > _CIRCUIT_RESET_SECS:
        logger.info("Circuit half-open for %s (%.0fs gecti)", model, elapsed)
        return False
    logger.warning(
        "Circuit OPEN for %s (%d basarisizlik, %.0fs once). Fallback.",
        model, count, elapsed,
    )
    return True


_TIER_FALLBACK: Dict[Tier, Tier] = {
    Tier.PREMIUM: Tier.MID,
    Tier.MID: Tier.MINI,
    Tier.MINI: Tier.LOCAL,
    Tier.LOCAL: Tier.LOCAL,
}


def _next_tier(tier: Tier) -> Tier:
    return _TIER_FALLBACK.get(tier, Tier.LOCAL)


# ============================================================================
# HISTORICAL PERFORMANCE
# ============================================================================


def get_model_performance_stats(model: str, task_type: str) -> dict:
    """llm_traces'ten model için son 7 gunluk istatistikler."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_calls,
                        COUNT(*) FILTER (WHERE success = TRUE) as successful,
                        ROUND(AVG(latency_ms)) as avg_latency,
                        COUNT(*) FILTER (WHERE json_parse_ok = TRUE) as json_ok,
                        COUNT(*) FILTER (WHERE json_parse_ok IS NOT NULL) as json_total
                    FROM llm_traces
                    WHERE model = %s AND created_at > NOW() - INTERVAL '7 days'
                    """,
                    (model,),
                )
                row = cur.fetchone()
                if not row or row[0] == 0:
                    return {}
                total, success, avg_lat, json_ok, json_total = row
                return {
                    "total_calls": total,
                    "success_rate": round(success / total, 3) if total > 0 else 0.0,
                    "avg_latency_ms": int(avg_lat) if avg_lat else 0,
                    "json_parse_ok_rate": round(json_ok / json_total, 3) if json_total > 0 else 1.0,
                }
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("Model performance stats alinamadi (%s): %s", model, exc)
        return {}


def _should_upgrade_model(model: str, task_type: str) -> bool:
    stats = get_model_performance_stats(model, task_type)
    if not stats or stats.get("total_calls", 0) < 5:
        return False
    if stats.get("json_parse_ok_rate", 1.0) < 0.70:
        logger.info("Model %s JSON parse dusuk, upgrade oneriliyor", model)
        return True
    if stats.get("success_rate", 1.0) < 0.80:
        logger.info("Model %s başarı dusuk, upgrade oneriliyor", model)
        return True
    return False


# ============================================================================
# ROUTING RULES
# ============================================================================


@dataclass
class _RoutingResult:
    tier: Tier
    temperature: float
    max_tokens: int
    reason: str


def _base_routing(
    task_type: str,
    complexity: str,
    endpoint_count: int,
    has_financial: bool,
    has_pii: bool,
    risk_level: str,
) -> _RoutingResult:
    """Karar matrisinden temel tier + parametreleri turet."""

    if task_type == "security_audit":
        if risk_level == "critical":
            return _RoutingResult(
                Tier.PREMIUM, 0.10, 12288,
                "security_audit + critical risk -> PREMIUM",
            )
        return _RoutingResult(
            Tier.PREMIUM, 0.15, 8192,
            "security_audit -> PREMIUM",
        )

    if task_type == "test_generation":
        if has_financial or has_pii or risk_level in ("high", "critical"):
            return _RoutingResult(
                Tier.PREMIUM, 0.25, 8192,
                "test_generation + financial/PII/high-risk -> PREMIUM",
            )
        if risk_level == "low" and complexity == "low":
            return _RoutingResult(
                Tier.MINI, 0.30, 4096,
                "test_generation + low + basit -> MINI",
            )
        return _RoutingResult(
            Tier.MID, 0.25, 6144,
            "test_generation + orta -> MID",
        )

    if task_type == "chain_builder":
        return _RoutingResult(
            Tier.PREMIUM, 0.20, 8192,
            "chain_builder -> PREMIUM",
        )

    if task_type == "quality_judge":
        return _RoutingResult(
            Tier.PREMIUM, 0.10, 2048,
            "quality_judge -> PREMIUM (kritik karar)",
        )

    if task_type == "spec_analysis":
        if endpoint_count > 5 or has_financial:
            return _RoutingResult(
                Tier.MID, 0.10, 6144,
                "spec_analysis + cok endpoint/financial -> MID",
            )
        return _RoutingResult(
            Tier.MINI, 0.10, 4096,
            "spec_analysis + basit -> MINI",
        )

    if task_type == "code_generation":
        return _RoutingResult(
            Tier.MID, 0.15, 6144,
            "code_generation -> MID",
        )

    return _RoutingResult(
        Tier.MINI, 0.30, 4096,
        "genel/chat -> MINI",
    )


def _apply_global_mode(result: _RoutingResult, task_type: str) -> _RoutingResult:
    mode = (settings.ai_routing_mode or "balanced").lower()

    if mode == "cost_optimized":
        if result.tier is Tier.PREMIUM and task_type not in ("quality_judge",):
            return _RoutingResult(
                tier=Tier.MID,
                temperature=result.temperature,
                max_tokens=result.max_tokens,
                reason=f"{result.reason}; mode=cost_optimized -> PREMIUM'dan MID'e dusuruldu",
            )

    if mode == "quality_first":
        if result.tier is Tier.MINI:
            return _RoutingResult(
                tier=Tier.MID,
                temperature=result.temperature,
                max_tokens=max(result.max_tokens, 4096),
                reason=f"{result.reason}; mode=quality_first -> MINI'den MID'e yukseltildi",
            )
        if result.tier is Tier.MID:
            return _RoutingResult(
                tier=Tier.PREMIUM,
                temperature=result.temperature,
                max_tokens=max(result.max_tokens, 8192),
                reason=f"{result.reason}; mode=quality_first -> MID'den PREMIUM'a yukseltildi",
            )

    return result


def _estimate_cost(model: str, max_tokens: int) -> float:
    """Max token butcesi baz alinarak tahmini maliyet (USD)."""
    half = max_tokens // 2
    try:
        return compute_cost_usd(model, input_tokens=half, output_tokens=half)
    except Exception as exc:
        logger.debug("_estimate_cost hatasi (%s): %s", model, exc)
        return 0.0


# ============================================================================
# FEATURE FLAG
# ============================================================================


def _v2_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.router.v2 — default True."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.router.v2", tenant_id=tenant_id, default=True)
    except Exception:
        return True


# ============================================================================
# PUBLIC API
# ============================================================================


def route_model(
    task_type: str,
    complexity: str = "medium",
    endpoint_count: int = 1,
    has_financial: bool = False,
    has_pii: bool = False,
    risk_level: str = "medium",
    tenant_id: Optional[str] = None,
) -> ModelRecommendation:
    """Görev tipi + risk + bulutun saglik durumuna gore optimal model sec."""
    # Feature flag kapaliysa guvenli default
    if not _v2_enabled(tenant_id):
        mini = _resolve(Tier.MINI)
        return ModelRecommendation(
            model=mini,
            tier=Tier.MINI,
            temperature=0.25,
            max_tokens=4096,
            reason="feature_flag ai.router.v2 kapalı -> guvenli default MINI",
            estimated_cost_usd=_estimate_cost(mini, 4096),
        )

    base = _base_routing(
        task_type=task_type,
        complexity=complexity,
        endpoint_count=endpoint_count,
        has_financial=has_financial,
        has_pii=has_pii,
        risk_level=risk_level,
    )
    adjusted = _apply_global_mode(base, task_type)

    max_tokens = adjusted.max_tokens
    extra_reason: list[str] = []
    if endpoint_count > 10:
        max_tokens = max(max_tokens, 16384)
        extra_reason.append(f"cok endpoint ({endpoint_count}) -> max_tokens={max_tokens}")

    tier = adjusted.tier
    model = _resolve(tier)

    # Circuit breaker fallback zinciri
    visited: set[Tier] = set()
    while should_fallback(model) and tier not in visited:
        visited.add(tier)
        next_tier = _next_tier(tier)
        if next_tier is tier:
            break
        extra_reason.append(f"circuit open ({tier.value} -> {next_tier.value})")
        tier = next_tier
        model = _resolve(tier)

    # Rate-limit proaktif throttle — kota %10 altinda ise fallback
    try:
        from app.domains.ai.rate_limit_monitor import should_throttle as _rl_throttle
        rl_throttle, rl_reason = _rl_throttle(model)
        if rl_throttle and tier not in visited:
            visited.add(tier)
            next_tier = _next_tier(tier)
            if next_tier is not tier:
                extra_reason.append(f"rate-limit ({rl_reason}) -> {next_tier.value}")
                tier = next_tier
                model = _resolve(tier)
    except Exception:
        pass

    # Geçmiş performans yukseltmesi
    if tier is Tier.MINI and _should_upgrade_model(model, task_type):
        if (settings.ai_routing_mode or "balanced").lower() != "cost_optimized":
            extra_reason.append(f"geçmiş performans dusuk ({model}) -> MID")
            tier = Tier.MID
            model = _resolve(tier)

    # Learned preference override (shadow/active — flag guarded)
    try:
        from app.domains.ai.router_learning import get_learned_preference
        learned = get_learned_preference(task_type)
        if learned and learned != model:
            extra_reason.append(f"learned-routing: {model} -> {learned}")
            model = learned
            tier = _model_tier(model)
    except Exception:
        pass

    estimated_cost = _estimate_cost(model, max_tokens)

    reason = adjusted.reason
    if extra_reason:
        reason = "; ".join([reason, *extra_reason])

    rec = ModelRecommendation(
        model=model,
        tier=tier,
        temperature=adjusted.temperature,
        max_tokens=max_tokens,
        reason=reason,
        estimated_cost_usd=estimated_cost,
    )
    logger.debug(
        "SmartRouter: task=%s risk=%s -> tier=%s model=%s cost~$%.5f | %s",
        task_type, risk_level, rec.tier.value, rec.model, rec.estimated_cost_usd, rec.reason,
    )
    return rec


# ============================================================================
# ENDPOINT CLASSIFICATION
# ============================================================================


_FINANCIAL_PATTERNS = ("transfer", "havale", "eft", "payment", "odeme", "kredi", "credit", "kart", "fatura", "bill")
_PII_PATTERNS = ("account", "hesap", "user", "kullanıcı", "profile", "profil", "kyc", "tckn", "identity")
_AUTH_PATTERNS = ("auth", "login", "token", "session", "otp", "2fa", "password")


def classify_endpoints(endpoints: list) -> dict:
    """Endpoint listesinden routing parametrelerini otomatik cikar."""
    count = len(endpoints)
    has_financial = False
    has_pii = False
    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    max_risk = "low"

    for ep in endpoints:
        path = (ep.get("path") or "").lower()
        method = (ep.get("method") or "").upper()

        if any(p in path for p in _FINANCIAL_PATTERNS):
            has_financial = True
            if risk_order[max_risk] < risk_order["critical"]:
                max_risk = "critical"

        if any(p in path for p in _PII_PATTERNS):
            has_pii = True
            if risk_order[max_risk] < risk_order["high"]:
                max_risk = "high"

        if any(p in path for p in _AUTH_PATTERNS):
            if risk_order[max_risk] < risk_order["critical"]:
                max_risk = "critical"

        if method in ("POST", "PUT", "DELETE", "PATCH"):
            if risk_order[max_risk] < risk_order["medium"]:
                max_risk = "medium"

    if count <= 3:
        complexity = "low"
    elif count <= 10:
        complexity = "medium"
    else:
        complexity = "high"

    return {
        "endpoint_count": count,
        "has_financial": has_financial,
        "has_pii": has_pii,
        "risk_level": max_risk,
        "complexity": complexity,
    }


def route_for_endpoints(task_type: str, endpoints: list) -> ModelRecommendation:
    cl = classify_endpoints(endpoints)
    return route_model(
        task_type=task_type,
        complexity=cl["complexity"],
        endpoint_count=cl["endpoint_count"],
        has_financial=cl["has_financial"],
        has_pii=cl["has_pii"],
        risk_level=cl["risk_level"],
    )


def get_routing_stats() -> dict:
    """Router konfigurasyonu + circuit state — /ai/model-router/stats için."""
    stats = {
        "routing_mode": settings.ai_routing_mode,
        "tiers": {
            "mini": settings.openai_mini_model,
            "mid": settings.openai_mid_model,
            "premium": settings.anthropic_premium_model if settings.anthropic_api_key else settings.openai_mid_model,
            "local": settings.ollama_fallback_model,
        },
        "provider_availability": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
        },
        "circuit_state": {
            model: {"failures": count, "last_failure_ts": ts}
            for model, (count, ts) in _circuit_state.items()
        },
        "fallback_chain": "PREMIUM -> MID -> MINI -> LOCAL",
    }
    # Rate-limit state ve context limits — opsiyonel
    try:
        from app.domains.ai.rate_limit_monitor import get_all_rate_limits
        stats["rate_limits"] = get_all_rate_limits()
    except Exception:
        stats["rate_limits"] = {}
    try:
        from app.domains.ai.token_counter import context_limit
        stats["context_limits"] = {
            tier_key: context_limit(model_name)
            for tier_key, model_name in stats["tiers"].items()
        }
    except Exception:
        pass
    return stats


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================


def _get_strong_model() -> str:
    """Return the PREMIUM model, raising if Anthropic is unavailable and fallback is disabled."""
    if settings.anthropic_api_key:
        return settings.anthropic_premium_model
    allow_fallback = bool(getattr(settings, "allow_provider_fallback", False))
    if allow_fallback and settings.openai_api_key:
        logger.warning("PREMIUM: ANTHROPIC_API_KEY yok; openai fallback kullaniliyor")
        return settings.openai_model
    raise RuntimeError(
        "AI provider 'anthropic' secili ama ANTHROPIC_API_KEY ayarlanmamis. "
        "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
    )


def _get_fast_model() -> str:
    return _resolve(Tier.MINI)


def _get_coder_model() -> str:
    return _resolve(Tier.MID)


_record_circuit_failure = record_circuit_failure
_record_circuit_success = record_circuit_success
