"""Merkezi Prometheus metrik tanımları — LLM katmanı (Dalga 0 · L1).

Tüm LLM metrikleri tek yerde. Yeni metrik eklemek = bu dosyaya ekle +
``test_metrics.py``'te regresyon. Çağıran kod ``record_*`` helper'larını
kullanır; etiket dizilerini doğrudan Counter'a dokunarak değil.

``prometheus_client`` opsiyonel bağımlılıktır; yoksa tüm `record_*`
fonksiyonları no-op döner (logger.debug ile sessiz).

Etiket disiplini (cardinality koruması):
    * tenant: "unknown" veya kısa id (max 64 char) — serbest UUID YOK
    * model: canonical id (registry'den)
    * provider: openai|anthropic|google|ollama|groq|vllm|unknown
    * task_type: enum (sabit küçük set)
    * status: ok|rate_limit|schema_fail|timeout|pii_block|budget_block|
              unknown_error
    * tier: mini|mid|premium|local
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


# ── Prometheus client availability ───────────────────────────────────────
try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore

    _PROM_AVAILABLE = True
except ImportError:
    _PROM_AVAILABLE = False
    Counter = Gauge = Histogram = None  # type: ignore


# ── Registry singleton ──────────────────────────────────────────────────
_lock = threading.Lock()
_initialized = False


class _Metrics:
    """Tüm LLM metriklerinin kapsayıcısı (lazy-init)."""

    requests_total = None
    tokens_total = None
    cost_total = None
    latency_seconds = None
    cache_hits_total = None
    cache_misses_total = None
    schema_violations_total = None
    pii_blocks_total = None
    refine_iterations = None
    retry_count = None
    budget_consumed_ratio = None
    unknown_model_total = None
    shadow_divergence = None
    ttft_seconds = None
    workflow_status_total = None
    workflow_events_total = None
    workflow_dead_letters_total = None
    workflow_approvals_total = None
    workflow_queue_depth = None
    workflow_artifact_integrity_failures_total = None


M = _Metrics()  # public handle — M.requests_total.labels(...).inc()


def ensure_metrics() -> bool:
    """Lazy init. Dönüş: True = prometheus aktif, False = no-op mod."""
    global _initialized
    if _initialized:
        return _PROM_AVAILABLE
    with _lock:
        if _initialized:
            return _PROM_AVAILABLE
        _initialized = True

        if not _PROM_AVAILABLE:
            logger.info("prometheus_client yok; LLM metrikleri no-op")
            return False

        M.requests_total = Counter(
            "llm_requests_total",
            "LLM çağrı sayısı",
            ["tenant", "task_type", "model", "provider", "tier", "status"],
        )
        M.tokens_total = Counter(
            "llm_tokens_total",
            "LLM token tüketimi",
            ["tenant", "model", "provider", "direction"],
        )
        M.cost_total = Counter(
            "llm_cost_usd_total",
            "LLM maliyeti (USD)",
            ["tenant", "model", "provider", "tier"],
        )
        M.latency_seconds = Histogram(
            "llm_latency_seconds",
            "LLM yanıt gecikmesi",
            ["task_type", "model", "tier", "status"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 45.0, 90.0),
        )
        M.ttft_seconds = Histogram(
            "llm_ttft_seconds",
            "Streaming time-to-first-token",
            ["task_type", "model"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
        )
        M.cache_hits_total = Counter(
            "llm_cache_hits_total",
            "Semantic cache isabet sayısı",
            ["task_type", "cache_kind"],  # kind: exact|semantic|embedding
        )
        M.cache_misses_total = Counter(
            "llm_cache_misses_total",
            "Semantic cache miss sayısı",
            ["task_type"],
        )
        M.schema_violations_total = Counter(
            "llm_schema_violations_total",
            "Structured output schema ihlalleri",
            ["task_type", "model"],
        )
        M.pii_blocks_total = Counter(
            "llm_pii_blocks_total",
            "PII tespit edilip bloklanan/redakte edilen çağrı sayısı",
            ["task_type", "rule"],  # rule: tckn|iban|email|phone|card
        )
        M.refine_iterations = Histogram(
            "llm_refine_iterations",
            "Self-refine iterasyon sayısı (başarılı olana kadar)",
            ["task_type"],
            buckets=(0, 1, 2, 3, 4, 5),
        )
        M.retry_count = Histogram(
            "llm_retry_count",
            "Transient error retry sayısı",
            ["task_type", "provider"],
            buckets=(0, 1, 2, 3, 4, 5),
        )
        M.budget_consumed_ratio = Gauge(
            "llm_budget_consumed_ratio",
            "Tenant günlük/aylık bütçesinin yüzde kaçı tüketildi (0.0-1.0+)",
            ["tenant", "window"],  # window: daily|monthly
        )
        M.unknown_model_total = Counter(
            "llm_unknown_model_total",
            "Registry'de bulunamayan model çağrısı (sessiz $0)",
            ["model"],
        )
        M.shadow_divergence = Histogram(
            "llm_shadow_quality_divergence",
            "Shadow trafik vs prod judge skor farkı (shadow − prod)",
            ["task_type", "shadow_tier"],
            buckets=(-1.0, -0.5, -0.2, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, 0.5, 1.0),
        )
        M.workflow_status_total = Counter(
            "agent_v2_workflow_status_total",
            "AI workflow status transition count",
            ["workflow_type", "status"],
        )
        M.workflow_events_total = Counter(
            "agent_v2_workflow_events_total",
            "AI workflow event count",
            ["event_type"],
        )
        M.workflow_dead_letters_total = Counter(
            "agent_v2_workflow_dead_letters_total",
            "AI workflow dead-letter count",
            ["queue_name", "reason"],
        )
        M.workflow_approvals_total = Counter(
            "agent_v2_workflow_approvals_total",
            "AI workflow approval decisions",
            ["decision"],
        )
        M.workflow_queue_depth = Gauge(
            "agent_v2_workflow_queue_depth",
            "AI workflow RQ queue depth",
            ["queue_name"],
        )
        M.workflow_artifact_integrity_failures_total = Counter(
            "agent_v2_workflow_artifact_integrity_failures_total",
            "AI workflow artifact download integrity failures",
            ["kind"],
        )
        logger.info("LLM Prometheus metrikleri aktif (20 seri)")
        return True


# ══════════════════════════════════════════════════════════════════════════
# Public helper API — tüm çağrılar buradan geçsin
# ══════════════════════════════════════════════════════════════════════════


def _safe_label(value: Optional[str], default: str = "unknown", max_len: int = 64) -> str:
    if not value:
        return default
    s = str(value).strip()
    return s[:max_len] if len(s) > max_len else s


def record_request(
    *,
    tenant: Optional[str],
    task_type: Optional[str],
    model: str,
    provider: Optional[str],
    tier: Optional[str],
    status: str,
    latency_ms: Optional[int] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
) -> None:
    """Tek bir LLM çağrısı için hepsi-bir-arada emit."""
    if not ensure_metrics():
        return
    try:
        t = _safe_label(tenant)
        tt = _safe_label(task_type)
        m = _safe_label(model, default="__unknown__")
        p = _safe_label(provider)
        tier_l = _safe_label(tier, default="mid")

        M.requests_total.labels(  # type: ignore[attr-defined]
            tenant=t, task_type=tt, model=m, provider=p, tier=tier_l, status=status,
        ).inc()

        if input_tokens:
            M.tokens_total.labels(  # type: ignore[attr-defined]
                tenant=t, model=m, provider=p, direction="input",
            ).inc(input_tokens)
        if output_tokens:
            M.tokens_total.labels(  # type: ignore[attr-defined]
                tenant=t, model=m, provider=p, direction="output",
            ).inc(output_tokens)

        if cost_usd > 0:
            M.cost_total.labels(  # type: ignore[attr-defined]
                tenant=t, model=m, provider=p, tier=tier_l,
            ).inc(cost_usd)

        if latency_ms is not None and latency_ms >= 0:
            M.latency_seconds.labels(  # type: ignore[attr-defined]
                task_type=tt, model=m, tier=tier_l, status=status,
            ).observe(latency_ms / 1000.0)
    except Exception as exc:  # pragma: no cover - metric emit hata bastırılır
        logger.debug("LLM metrics emit hata: %s", exc)


def record_cache(*, task_type: Optional[str], hit: bool, kind: str = "semantic") -> None:
    if not ensure_metrics():
        return
    try:
        tt = _safe_label(task_type)
        if hit:
            M.cache_hits_total.labels(task_type=tt, cache_kind=kind).inc()  # type: ignore[attr-defined]
        else:
            M.cache_misses_total.labels(task_type=tt).inc()  # type: ignore[attr-defined]
    except Exception as exc:
        logger.debug("cache metric hata: %s", exc)


def record_schema_violation(*, task_type: Optional[str], model: str) -> None:
    if not ensure_metrics():
        return
    try:
        M.schema_violations_total.labels(  # type: ignore[attr-defined]
            task_type=_safe_label(task_type), model=_safe_label(model, "__unknown__"),
        ).inc()
    except Exception as exc:
        logger.debug("schema metric hata: %s", exc)


def record_pii_block(*, task_type: Optional[str], rule: str) -> None:
    if not ensure_metrics():
        return
    try:
        M.pii_blocks_total.labels(  # type: ignore[attr-defined]
            task_type=_safe_label(task_type), rule=_safe_label(rule, "unknown"),
        ).inc()
    except Exception as exc:
        logger.debug("pii metric hata: %s", exc)


def record_refine(*, task_type: Optional[str], iterations: int) -> None:
    if not ensure_metrics():
        return
    try:
        M.refine_iterations.labels(task_type=_safe_label(task_type)).observe(iterations)  # type: ignore[attr-defined]
    except Exception as exc:
        logger.debug("refine metric hata: %s", exc)


def record_workflow_status(*, workflow_type: Optional[str], status: str) -> None:
    if not ensure_metrics():
        return
    try:
        M.workflow_status_total.labels(  # type: ignore[attr-defined]
            workflow_type=_safe_label(workflow_type, "unknown"),
            status=_safe_label(status),
        ).inc()
    except Exception as exc:
        logger.debug("workflow status metric hata: %s", exc)


def record_workflow_event(*, event_type: Optional[str]) -> None:
    if not ensure_metrics():
        return
    try:
        M.workflow_events_total.labels(  # type: ignore[attr-defined]
            event_type=_safe_label(event_type, "message"),
        ).inc()
    except Exception as exc:
        logger.debug("workflow event metric hata: %s", exc)


def record_workflow_dead_letter(*, queue_name: str, reason: str) -> None:
    if not ensure_metrics():
        return
    try:
        M.workflow_dead_letters_total.labels(  # type: ignore[attr-defined]
            queue_name=_safe_label(queue_name),
            reason=_safe_label(reason),
        ).inc()
    except Exception as exc:
        logger.debug("workflow dead-letter metric hata: %s", exc)


def record_workflow_approval(*, decision: str) -> None:
    if not ensure_metrics():
        return
    try:
        M.workflow_approvals_total.labels(  # type: ignore[attr-defined]
            decision=_safe_label(decision),
        ).inc()
    except Exception as exc:
        logger.debug("workflow approval metric hata: %s", exc)


def set_workflow_queue_depth(*, queue_name: str, depth: int) -> None:
    if not ensure_metrics():
        return
    try:
        M.workflow_queue_depth.labels(  # type: ignore[attr-defined]
            queue_name=_safe_label(queue_name),
        ).set(max(depth, 0))
    except Exception as exc:
        logger.debug("workflow queue metric hata: %s", exc)


def record_workflow_artifact_integrity_failure(*, kind: Optional[str]) -> None:
    if not ensure_metrics():
        return
    try:
        M.workflow_artifact_integrity_failures_total.labels(  # type: ignore[attr-defined]
            kind=_safe_label(kind),
        ).inc()
    except Exception as exc:
        logger.debug("workflow artifact integrity metric hata: %s", exc)


def record_retry(*, task_type: Optional[str], provider: Optional[str], count: int) -> None:
    if not ensure_metrics():
        return
    try:
        M.retry_count.labels(  # type: ignore[attr-defined]
            task_type=_safe_label(task_type), provider=_safe_label(provider),
        ).observe(count)
    except Exception as exc:
        logger.debug("retry metric hata: %s", exc)


def set_budget_consumed(*, tenant: str, window: str, ratio: float) -> None:
    """Periyodik snapshot — usage_service gauge'a yazar."""
    if not ensure_metrics():
        return
    try:
        M.budget_consumed_ratio.labels(  # type: ignore[attr-defined]
            tenant=_safe_label(tenant), window=_safe_label(window, "daily"),
        ).set(ratio)
    except Exception as exc:
        logger.debug("budget metric hata: %s", exc)


def record_unknown_model(model: str) -> None:
    if not ensure_metrics():
        return
    try:
        M.unknown_model_total.labels(model=_safe_label(model, "__blank__")).inc()  # type: ignore[attr-defined]
    except Exception as exc:
        logger.debug("unknown model metric hata: %s", exc)


def record_shadow_divergence(
    *, task_type: Optional[str], shadow_tier: str, divergence: float
) -> None:
    """Shadow trafik çıktısı judge ile prod çıktısı arasındaki fark."""
    if not ensure_metrics():
        return
    try:
        M.shadow_divergence.labels(  # type: ignore[attr-defined]
            task_type=_safe_label(task_type), shadow_tier=_safe_label(shadow_tier),
        ).observe(divergence)
    except Exception as exc:
        logger.debug("shadow metric hata: %s", exc)


def record_ttft(*, task_type: Optional[str], model: str, ttft_ms: int) -> None:
    if not ensure_metrics():
        return
    try:
        M.ttft_seconds.labels(  # type: ignore[attr-defined]
            task_type=_safe_label(task_type), model=_safe_label(model, "__unknown__"),
        ).observe(ttft_ms / 1000.0)
    except Exception as exc:
        logger.debug("ttft metric hata: %s", exc)


# ── Test helper ─────────────────────────────────────────────────────────
def _reset_for_tests() -> None:
    """Test fixture'ları için; üretimde kullanılmaz."""
    global _initialized
    _initialized = False
    # Not: prometheus_client collector'ı global state'i korur; gerçekten
    # sıfırlamak için REGISTRY.unregister gerekli. Unit testte ayrı
    # CollectorRegistry kullanmak önerilir.
