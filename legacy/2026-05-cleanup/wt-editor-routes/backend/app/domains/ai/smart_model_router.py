"""
Smart Model Router — Gorev tipine ve karmasikliga gore optimal model secimi.

LLM cagrilarinda model, temperature ve max_tokens parametrelerini otomatik belirler.
Gecmis performans verilerini (llm_traces) dikkate alarak akilli yonlendirme yapar.

Routing kurallari:
  - Guvenlik denetimi + kritik risk → en guclu model, dusuk temperature
  - Finansal endpoint + test uretimi → guclu model
  - Dusuk risk + test uretimi → hizli model
  - Kod uretimi → coder model
  - PII iceren endpointler → her zaman guclu model (uyumluluk kritik)

Kullanim:
    from app.domains.ai.smart_model_router import route_model

    rec = route_model(
        task_type="security_audit",
        complexity="high",
        has_financial=True,
        risk_level="critical",
    )
    # rec.model, rec.temperature, rec.max_tokens, rec.reason
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# DATACLASS
# ============================================================================

@dataclass
class ModelRecommendation:
    """Model yonlendirme sonucu."""
    model: str
    temperature: float
    max_tokens: int
    reason: str


# ============================================================================
# MODEL TIERS
# ============================================================================


def _allow_provider_fallback() -> bool:
    return bool(getattr(settings, "allow_provider_fallback", False))


def _resolve_effective_provider() -> str:
    provider = settings.ai_provider
    if provider == "anthropic":
        if settings.anthropic_api_key:
            return "anthropic"
        if _allow_provider_fallback() and settings.openai_api_key:
            logger.warning("Smart router provider fallback: anthropic secili ama ANTHROPIC_API_KEY yok; openai oneriliyor")
            return "openai"
        raise RuntimeError(
            "AI provider 'anthropic' secili ama ANTHROPIC_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )

    if provider == "openai":
        if settings.openai_api_key:
            return "openai"
        if _allow_provider_fallback() and settings.anthropic_api_key:
            logger.warning("Smart router provider fallback: openai secili ama OPENAI_API_KEY yok; anthropic oneriliyor")
            return "anthropic"
        raise RuntimeError(
            "AI provider 'openai' secili ama OPENAI_API_KEY ayarlanmamis. "
            "Fallback icin ALLOW_PROVIDER_FALLBACK=true tanimlayin veya provider/config'i duzeltin."
        )

    if provider == "ollama":
        return "ollama"

    raise RuntimeError(f"Desteklenmeyen AI provider: {provider}")

def _get_strong_model() -> str:
    """En guclu analiz modeli — karmasik gorevler icin."""
    effective_provider = _resolve_effective_provider()
    if effective_provider == "ollama":
        return settings.ollama_model_analyst  # qwen2.5:32b
    if effective_provider == "anthropic":
        return settings.anthropic_model  # claude-sonnet-4-20250514
    return settings.openai_model  # gpt-4o


def _get_fast_model() -> str:
    """Hizli model — basit gorevler icin."""
    effective_provider = _resolve_effective_provider()
    if effective_provider == "ollama":
        return settings.ollama_model_fast  # mistral:latest
    if effective_provider == "anthropic":
        return settings.anthropic_model
    return settings.openai_model  # gpt-4o (OpenAI'da fark yok)


def _get_coder_model() -> str:
    """Kod uretimi modeli."""
    effective_provider = _resolve_effective_provider()
    if effective_provider == "ollama":
        return settings.ollama_model_coder  # qwen2.5-coder:7b
    if effective_provider == "anthropic":
        return settings.anthropic_model
    return settings.openai_model  # gpt-4o


# ============================================================================
# CIRCUIT BREAKER STATE
# ============================================================================

# Basit in-memory circuit breaker — model bazli
# {model: (failure_count, last_failure_ts)}
_circuit_state: Dict[str, Tuple[int, float]] = {}
_CIRCUIT_THRESHOLD = 3       # 3 ardisik basarisizlik → circuit open
_CIRCUIT_RESET_SECS = 300.0  # 5 dakika sonra tekrar dene (half-open)


def _record_circuit_failure(model: str) -> None:
    """Model basarisizligini kaydet."""
    count, _ = _circuit_state.get(model, (0, 0.0))
    _circuit_state[model] = (count + 1, time.time())


def _record_circuit_success(model: str) -> None:
    """Basarili cagri — circuit'i sifirla."""
    if model in _circuit_state:
        _circuit_state[model] = (0, 0.0)


def should_fallback(model: str) -> bool:
    """
    Circuit breaker durumunu kontrol et.

    Returns:
        True → model'e istek gonderilmemeli (circuit open), fallback kullan.
    """
    state = _circuit_state.get(model)
    if state is None:
        return False

    count, last_failure = state
    if count < _CIRCUIT_THRESHOLD:
        return False

    # Threshold asildi — circuit open
    elapsed = time.time() - last_failure
    if elapsed > _CIRCUIT_RESET_SECS:
        # Half-open: bir deneme daha yap
        logger.info("Circuit half-open for %s (%.0fs gecti), bir deneme daha", model, elapsed)
        return False

    logger.warning(
        "Circuit OPEN for %s (%d basarisizlik, %.0fs once). Fallback kullanilacak.",
        model, count, elapsed,
    )
    return True


# ============================================================================
# HISTORICAL PERFORMANCE
# ============================================================================

def get_model_performance_stats(model: str, task_type: str) -> dict:
    """
    llm_traces tablosundan model+task (agent_name) icin performans istatistikleri cek.

    Returns:
        {
            "total_calls": int,
            "success_rate": float (0.0-1.0),
            "avg_latency_ms": int,
            "json_parse_ok_rate": float (0.0-1.0),
        }
        Veri yoksa veya hata olursa bos dict dondurur.
    """
    try:
        from app.domains.ai.llm_trace import get_model_task_performance_stats
        return get_model_task_performance_stats(model, task_type, days=7)
    except Exception as exc:
        logger.debug("Model performance stats alinamadi (%s): %s", model, exc)
        return {}


def _should_upgrade_model(model: str, task_type: str) -> bool:
    """
    Gecmis performansa gore model upgrade onerilmeli mi?
    Dusuk JSON parse orani veya yuksek hata orani → guclu modele gec.
    """
    stats = get_model_performance_stats(model, task_type)
    if not stats or not stats.get("sample_size_sufficient", False):
        # Yeterli veri yok — varsayilani kullan
        return False

    # JSON parse orani %70'in altinda → model yetersiz
    if stats.get("json_parse_ok_rate", 1.0) < 0.70:
        logger.info(
            "Model %s JSON parse orani dusuk (%.1f%%), upgrade oneriliyor",
            model, stats["json_parse_ok_rate"] * 100,
        )
        return True

    # Basari orani %80'in altinda → model guvenilmez
    if stats.get("success_rate", 1.0) < 0.80:
        logger.info(
            "Model %s basari orani dusuk (%.1f%%), upgrade oneriliyor",
            model, stats["success_rate"] * 100,
        )
        return True

    if stats.get("fallback_rate", 0.0) > 0.20:
        logger.info(
            "Model %s fallback orani yuksek (%.1f%%), upgrade oneriliyor",
            model, stats["fallback_rate"] * 100,
        )
        return True

    if stats.get("p95_latency_ms", 0) > 8000:
        logger.info(
            "Model %s p95 latency yuksek (%dms), upgrade oneriliyor",
            model, stats["p95_latency_ms"],
        )
        return True

    return False


# ============================================================================
# CORE ROUTING LOGIC
# ============================================================================

def route_model(
    task_type: str,
    complexity: str = "medium",
    endpoint_count: int = 1,
    has_financial: bool = False,
    has_pii: bool = False,
    risk_level: str = "medium",
) -> ModelRecommendation:
    """
    Gorev tipine ve parametrelere gore optimal model, temperature ve max_tokens sec.

    Args:
        task_type:       "test_generation", "security_audit", "spec_analysis",
                         "chain_builder", "chat", "code_generation"
        complexity:      "low", "medium", "high"
        endpoint_count:  Islenmesi gereken endpoint sayisi
        has_financial:   Finansal islem endpoint'i var mi?
        has_pii:         Kisisel veri (PII) iceren endpoint var mi?
        risk_level:      "low", "medium", "high", "critical"

    Returns:
        ModelRecommendation(model, temperature, max_tokens, reason)
    """
    model = _get_fast_model()
    temperature = 0.25
    max_tokens = 4096
    reason_parts = []  # type: list

    # ── Rule 1: Security audit + critical risk → strongest model ─────────
    if task_type == "security_audit":
        model = _get_strong_model()
        temperature = 0.15
        max_tokens = 8192
        reason_parts.append("Guvenlik denetimi → guclu model + dusuk temperature")

        if risk_level == "critical":
            temperature = 0.10
            max_tokens = 12288
            reason_parts.append("Kritik risk seviyesi → ekstra dikkat")

    # ── Rule 2: Test generation + financial → strong model ───────────────
    elif task_type == "test_generation":
        if has_financial or risk_level in ("high", "critical"):
            model = _get_strong_model()
            temperature = 0.25
            max_tokens = 8192
            reason_parts.append("Finansal/yuksek riskli test uretimi → guclu model")
        elif risk_level == "low" and complexity == "low":
            # Rule 3: Low risk → fast model
            model = _get_fast_model()
            temperature = 0.30
            max_tokens = 4096
            reason_parts.append("Dusuk risk + basit → hizli model")
        else:
            # Medium — still strong for banking domain
            model = _get_strong_model()
            temperature = 0.25
            max_tokens = 8192
            reason_parts.append("Orta risk test uretimi → guclu model (bankacilik)")

    # ── Rule 4: Chain builder → analyst model ────────────────────────────
    elif task_type == "chain_builder":
        model = _get_strong_model()
        temperature = 0.20
        max_tokens = 8192
        reason_parts.append("Chain builder → guclu model (karmasik muhakeme)")

    # ── Rule 5: Spec analysis → fast model ───────────────────────────────
    elif task_type == "spec_analysis":
        model = _get_fast_model()
        temperature = 0.10
        max_tokens = 4096
        reason_parts.append("Spec analizi → hizli model (basit cikartim)")

        # But upgrade if many endpoints or financial
        if endpoint_count > 5 or has_financial:
            model = _get_strong_model()
            max_tokens = 8192
            reason_parts.append("Cok endpoint/finansal → guclu modele yukseltildi")

    # ── Rule 6: Code generation → coder model ───────────────────────────
    elif task_type == "code_generation":
        model = _get_coder_model()
        temperature = 0.15
        max_tokens = 8192
        reason_parts.append("Kod uretimi → coder model")

    # ── Rule: Chat / other → fast model ──────────────────────────────────
    else:
        model = _get_fast_model()
        temperature = 0.30
        max_tokens = 4096
        reason_parts.append("Genel gorev → hizli model")

    # ── Rule 7: Many endpoints → boost max_tokens ───────────────────────
    if endpoint_count > 10:
        max_tokens = max(max_tokens, 16384)
        reason_parts.append(
            "Cok sayida endpoint (%d) → max_tokens arttirildi (%d)"
            % (endpoint_count, max_tokens)
        )

    # ── Rule 8: PII endpoints → always strong model ─────────────────────
    if has_pii:
        strong = _get_strong_model()
        if model != strong:
            model = strong
            reason_parts.append("PII iceren endpoint → guclu modele zorunlu yukseltme (uyumluluk)")

    # ── Complexity override ──────────────────────────────────────────────
    if complexity == "high" and model == _get_fast_model():
        model = _get_strong_model()
        reason_parts.append("Yuksek karmasiklik → guclu modele yukseltildi")

    # ── Circuit breaker check ────────────────────────────────────────────
    if should_fallback(model):
        fallback = _get_fallback_for(model)
        if fallback:
            reason_parts.append(
                "Circuit open (%s) → fallback: %s" % (model, fallback)
            )
            model = fallback

    # ── Historical performance upgrade check ─────────────────────────────
    if model == _get_fast_model() and _should_upgrade_model(model, task_type):
        strong = _get_strong_model()
        if model != strong:
            reason_parts.append(
                "Gecmis performans dusuk (%s) → %s'e yukseltildi" % (model, strong)
            )
            model = strong

    reason = "; ".join(reason_parts) if reason_parts else "Varsayilan yonlendirme"

    rec = ModelRecommendation(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        reason=reason,
    )
    logger.debug(
        "SmartRouter: task=%s complexity=%s risk=%s → model=%s temp=%.2f tokens=%d | %s",
        task_type, complexity, risk_level, rec.model, rec.temperature, rec.max_tokens, rec.reason,
    )
    return rec


# ============================================================================
# HELPERS
# ============================================================================

def _get_fallback_for(model: str) -> Optional[str]:
    """Circuit open olan model icin fallback model dondur."""
    strong = _get_strong_model()
    fast = _get_fast_model()
    coder = _get_coder_model()

    if model == strong:
        return fast   # Strong basarisiz → fast'e duş
    if model == fast:
        return strong  # Fast basarisiz → strong'a cik
    if model == coder:
        return fast    # Coder basarisiz → fast'e duş
    return None


def classify_endpoints(endpoints: list) -> dict:
    """
    Endpoint listesinden routing parametrelerini otomatik cikar.

    Args:
        endpoints: EndpointInfo dict listesi (method, path, ...)

    Returns:
        {
            "endpoint_count": int,
            "has_financial": bool,
            "has_pii": bool,
            "risk_level": str,      # "low" | "medium" | "high" | "critical"
            "complexity": str,      # "low" | "medium" | "high"
        }
    """
    count = len(endpoints)
    has_financial = False
    has_pii = False
    max_risk = "low"

    _FINANCIAL_PATTERNS = ("transfer", "havale", "eft", "payment", "odeme", "kredi", "credit")
    _PII_PATTERNS = ("account", "hesap", "user", "kullanici", "profile", "profil", "kyc")
    _AUTH_PATTERNS = ("auth", "login", "token", "session", "otp")

    risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    for ep in endpoints:
        path = (ep.get("path") or "").lower()
        method = (ep.get("method") or "").upper()

        # Financial check
        if any(p in path for p in _FINANCIAL_PATTERNS):
            has_financial = True
            if risk_order.get(max_risk, 0) < risk_order["critical"]:
                max_risk = "critical"

        # PII check
        if any(p in path for p in _PII_PATTERNS):
            has_pii = True
            if risk_order.get(max_risk, 0) < risk_order["high"]:
                max_risk = "high"

        # Auth is always critical
        if any(p in path for p in _AUTH_PATTERNS):
            if risk_order.get(max_risk, 0) < risk_order["critical"]:
                max_risk = "critical"

        # POST/PUT/DELETE with data mutation → higher risk
        if method in ("POST", "PUT", "DELETE", "PATCH"):
            if risk_order.get(max_risk, 0) < risk_order["medium"]:
                max_risk = "medium"

    # Complexity from count
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


def route_for_endpoints(
    task_type: str,
    endpoints: list,
) -> ModelRecommendation:
    """
    Endpoint listesinden otomatik olarak parametreleri cikarip model sec.
    classify_endpoints + route_model'in birlesimidir.

    Args:
        task_type: Ajan modu
        endpoints: EndpointInfo dict listesi

    Returns:
        ModelRecommendation
    """
    classification = classify_endpoints(endpoints)
    return route_model(
        task_type=task_type,
        complexity=classification["complexity"],
        endpoint_count=classification["endpoint_count"],
        has_financial=classification["has_financial"],
        has_pii=classification["has_pii"],
        risk_level=classification["risk_level"],
    )


def get_routing_stats() -> dict:
    """Model routing konfigurasyonu ve istatistikleri — API icin."""
    return {
        "strong_model": _get_strong_model(),
        "fast_model": _get_fast_model(),
        "coder_model": _get_coder_model(),
        "provider": settings.ai_provider,
        "circuit_state": {
            model: {"failures": count, "last_failure": ts}
            for model, (count, ts) in _circuit_state.items()
        },
    }
