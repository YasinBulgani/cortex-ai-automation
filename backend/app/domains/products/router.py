"""Product telemetry endpoint.

GET /api/v1/products/{product_id}/telemetry

Gerçek zaman damgası + DB'den çekilen aggregation yoksa demo veri döner.
Frontend'deki useProductTelemetry hook bu endpoint'i 60s'de bir poll eder.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timedelta, timezone as _tz
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db

_logger = logging.getLogger(__name__)


def _format_age(dt: datetime | str | None) -> str:
    """Verilen datetime'ı insanca okunabilir yaş stringine çevirir."""
    if not dt:
        return "?"
    try:
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            delta = datetime.now(_tz.utc) - dt.replace(tzinfo=_tz.utc)
        else:
            delta = datetime.now(_tz.utc) - dt
        total_hours = int(delta.total_seconds() / 3600)
        if total_hours < 1:
            return "az önce"
        if total_hours < 24:
            return f"{total_hours} sa"
        return f"{total_hours // 24} gün"
    except Exception:
        return "?"


def _is_production() -> bool:
    """Read app env at request time so tests can override via monkeypatch."""
    env = (os.getenv("CORTEX_ENV") or os.getenv("APP_ENV") or "").lower()
    return env in {"production", "prod"}


def _block_in_production(endpoint: str) -> JSONResponse | None:
    """In production, return a 200 demo-mode notice instead of raising HTTP 503.

    Returns a JSONResponse when running in production (caller must return it
    immediately), or None when running in any other environment so the normal
    handler can continue.
    """
    if _is_production():
        return JSONResponse(
            status_code=200,
            content={
                "status": "demo",
                "message": (
                    "Product analytics in demo mode. "
                    "Configure PRODUCTS_DEMO_MODE=false for real data."
                ),
                "data": {},
                "_endpoint": endpoint,
            },
            headers={"X-Demo-Disabled": "true", "X-Data-Mode": "demo"},
        )
    return None

# P0 #4: Replace with real aggregation from DB
# TODO: Replace with real DB aggregation (Sprint X).
#   Adımlar:
#   1. _DEMO_MODE = False yap (veya PRODUCTS_DEMO_MODE=false env var ayarla)
#   2. Her endpoint için ilgili tablodan gerçek veriyi çek (bkz. endpoint TODO'ları)
#   3. PRODUCT_STATS ve AI_INSIGHTS sabit sözlüklerini kaldır
_DEMO_MODE = os.getenv("PRODUCTS_DEMO_MODE", "true").lower() == "true"

if _DEMO_MODE:
    _logger.warning(
        "Products domain DEMO MODE aktif — tum metrikler simule edilmektedir. "
        "Gercek implementasyon icin _DEMO_MODE=False yapin ve DB aggregation'lari ekleyin."
    )

router = APIRouter(prefix="/products", tags=["products"])

VALID_PRODUCT_IDS = {
    "one", "studio", "service", "web", "mobile",
    "data", "management", "intelligence", "nexus-code",
}

# ── Stat templates per product ────────────────────────────────────────────────

def _sparkline(base: int, n: int = 7) -> list[int]:
    vals = []
    v = base
    for _ in range(n):
        v = max(0, v + random.randint(-5, 8))
        vals.append(v)
    return vals


PRODUCT_STATS: dict[str, list[dict[str, Any]]] = {
    "one": [
        {"key": "projects",      "label": "Aktif Proje",     "value": 24,  "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "integrations",  "label": "Entegrasyon",     "value": 12,  "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "coverage",      "label": "Kapsam",          "value": 87,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "health",        "label": "Platform Sağlık", "value": 99,  "unit": "%",   "trend": "flat", "severity": "ok"},
        {"key": "sla",           "label": "SLA",             "value": 99.9,"unit": "%",   "trend": "flat", "severity": "ok"},
        {"key": "licenses",      "label": "Lisans Kullanım", "value": 68,  "unit": "%",   "trend": "up",   "severity": "warning"},
    ],
    "studio": [
        {"key": "scenarios",     "label": "Senaryo",         "value": 142, "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "drafts",        "label": "Taslak",          "value": 18,  "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "coverage",      "label": "Kapsam",          "value": 91,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "ai_generated",  "label": "AI Senaryo",      "value": 57,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "pending",       "label": "Onay Bekliyor",   "value": 5,   "unit": None,  "trend": "flat", "severity": "warning"},
        {"key": "pass_rate",     "label": "Geçme Oranı",     "value": 94,  "unit": "%",   "trend": "up",   "severity": "ok"},
    ],
    "service": [
        {"key": "endpoints",     "label": "Endpoint",        "value": 87,  "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "p95",           "label": "P95 Gecikme",     "value": 145, "unit": "ms",  "trend": "down", "severity": "ok"},
        {"key": "error_rate",    "label": "Hata Oranı",      "value": 0.4, "unit": "%",   "trend": "down", "severity": "ok"},
        {"key": "contracts",     "label": "Sözleşme",        "value": 23,  "unit": None,  "trend": "flat", "severity": "ok"},
        {"key": "drift",         "label": "Drift",           "value": 3,   "unit": None,  "trend": "up",   "severity": "warning"},
        {"key": "security",      "label": "Güvenlik Puanı",  "value": 96,  "unit": "%",   "trend": "flat", "severity": "ok"},
    ],
    "web": [
        {"key": "browsers",      "label": "Tarayıcı",        "value": 6,   "unit": None,  "trend": "flat", "severity": "ok"},
        {"key": "visual_delta",  "label": "Görsel Fark",     "value": 2,   "unit": None,  "trend": "down", "severity": "ok"},
        {"key": "a11y_score",    "label": "A11y Puanı",      "value": 88,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "locators",      "value": 94, "label": "Locator Sağlık", "unit": "%", "trend": "flat", "severity": "ok"},
        {"key": "coverage",      "label": "Sayfa Kapsam",    "value": 78,  "unit": "%",   "trend": "up",   "severity": "warning"},
        {"key": "pass_rate",     "label": "Geçme Oranı",     "value": 92,  "unit": "%",   "trend": "up",   "severity": "ok"},
    ],
    "mobile": [
        {"key": "devices",       "label": "Cihaz",           "value": 18,  "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "crash_free",    "label": "Çöküm Yok",       "value": 99.2,"unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "coverage",      "label": "Kapsam",          "value": 83,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "perf_score",    "label": "Performans",      "value": 91,  "unit": "%",   "trend": "flat", "severity": "ok"},
        {"key": "pass_rate",     "label": "Geçme Oranı",     "value": 96,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "sessions",      "label": "Test Oturumu",    "value": 34,  "unit": None,  "trend": "up",   "severity": "ok"},
    ],
    "data": [
        {"key": "tables",        "label": "Tablo",           "value": 47,  "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "quality",       "label": "Kalite Puanı",    "value": 92,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "pii_masked",    "label": "PII Maskeleme",   "value": 98,  "unit": "%",   "trend": "flat", "severity": "ok"},
        {"key": "freshness",     "label": "Tazelik",         "value": 97,  "unit": "%",   "trend": "flat", "severity": "ok"},
        {"key": "volume",        "label": "Üretim (satır)",  "value": 125000, "unit": None, "trend": "up", "severity": "ok"},
        {"key": "recipes",       "label": "Reçete",          "value": 12,  "unit": None,  "trend": "up",   "severity": "ok"},
    ],
    "management": [
        {"key": "cases", "label": "Manuel Test Case", "value": 341, "unit": None, "trend": "up", "severity": "ok"},
        {"key": "active_runs", "label": "Aktif Run", "value": 9, "unit": None, "trend": "flat", "severity": "ok"},
        {"key": "pass_rate", "label": "Pass Rate", "value": 88, "unit": "%", "trend": "up", "severity": "ok"},
        {"key": "blocked", "label": "Blocked", "value": 7, "unit": None, "trend": "down", "severity": "warning"},
        {"key": "coverage", "label": "Req. Coverage", "value": 76, "unit": "%", "trend": "up", "severity": "warning"},
        {"key": "workload", "label": "Tester İş Yükü", "value": 42, "unit": None, "trend": "flat", "severity": "ok"},
    ],
    "intelligence": [
        {"key": "providers",     "label": "Provider",        "value": 3,   "unit": None,  "trend": "flat", "severity": "ok"},
        {"key": "token_m",       "label": "Token (M)",       "value": 2.4, "unit": "M",   "trend": "up",   "severity": "ok"},
        {"key": "cost_usd",      "label": "Maliyet",         "value": 14.2,"unit": "$",   "trend": "up",   "severity": "warning"},
        {"key": "judge_score",   "label": "LLM-Judge",       "value": 87,  "unit": "%",   "trend": "up",   "severity": "ok"},
        {"key": "fallbacks",     "label": "Fallback",        "value": 7,   "unit": None,  "trend": "down", "severity": "ok"},
        {"key": "latency",       "label": "Ort. Gecikme",    "value": 820, "unit": "ms",  "trend": "down", "severity": "ok"},
    ],
    "nexus-code": [
        {"key": "repos",         "label": "Repo",            "value": 8,   "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "analyses",      "label": "Analiz",          "value": 143, "unit": None,  "trend": "up",   "severity": "ok"},
        {"key": "bugs_found",    "label": "Hata Bulundu",    "value": 31,  "unit": None,  "trend": "down", "severity": "ok"},
        {"key": "smells",        "label": "Kod Kokusu",      "value": 18,  "unit": None,  "trend": "down", "severity": "warning"},
        {"key": "pii_findings",  "label": "PII Bulgusu",     "value": 4,   "unit": None,  "trend": "down", "severity": "critical"},
        {"key": "coverage",      "label": "Analiz Kapsam",   "value": 79,  "unit": "%",   "trend": "up",   "severity": "ok"},
    ],
}

AI_INSIGHTS: dict[str, list[dict[str, Any]]] = {
    "one": [
        {"id": "i1", "title": "3 entegrasyonda bağlantı gecikmesi", "description": "Jira, GitHub ve Slack entegrasyonları son 30 dakikada 200ms+ gecikme gösterdi.", "severity": "warning", "category": "integration", "confidence": 0.91},
        {"id": "i2", "title": "Lisans sınırına yaklaşılıyor", "description": "Mevcut kullanım %68 — 30 gün içinde limit aşılabilir.", "severity": "info", "category": "usage", "confidence": 0.78},
    ],
    "studio": [
        {"id": "i1", "title": "5 senaryo onay bekliyor", "description": "AI tarafından oluşturulan senaryolar insan onayı bekliyor.", "severity": "warning", "category": "approval", "confidence": 0.99},
        {"id": "i2", "title": "Login akışı kapsam artışı", "description": "Bu hafta login senaryolarında %12 kapsam artışı gözlemlendi.", "severity": "info", "category": "coverage", "confidence": 0.85},
    ],
    "service": [
        {"id": "i1", "title": "3 API kontrakta sapma var", "description": "Kullanıcı, ödeme ve bildirim servislerinde şema uyumsuzluğu tespit edildi.", "severity": "critical", "category": "contract", "confidence": 0.94},
        {"id": "i2", "title": "P95 gecikme artış trendi", "description": "/api/orders endpoint'i son 2 saatte 145ms → 210ms geçiş yaptı.", "severity": "warning", "category": "performance", "confidence": 0.88},
    ],
    "web": [
        {"id": "i1", "title": "2 görsel regresyon onay bekliyor", "description": "Header ve footer bileşenlerinde pixel farkı tespit edildi.", "severity": "warning", "category": "visual", "confidence": 0.97},
        {"id": "i2", "title": "WCAG kontras oranı sorunu", "description": "3 renk kombinasyonu AA standardının altında kaldı.", "severity": "info", "category": "a11y", "confidence": 0.82},
    ],
    "mobile": [
        {"id": "i1", "title": "iOS 17 uyumluluk sorunu", "description": "iPhone 15 Pro'da scroll performansı düşük tespit edildi.", "severity": "warning", "category": "device", "confidence": 0.89},
        {"id": "i2", "title": "Android deep-link akışı başarılı", "description": "Son 48 saatte deep-link testleri %98 başarı oranıyla tamamlandı.", "severity": "info", "category": "test", "confidence": 0.96},
    ],
    "data": [
        {"id": "i1", "title": "4 PII bulgusu maskelenemedi", "description": "Email alanlarında kısmi maskeleme hatası tespit edildi.", "severity": "critical", "category": "pii", "confidence": 0.99},
        {"id": "i2", "title": "Veri tazeliği düştü", "description": "Orders tablosu son güncelleme 6 saat önce — beklenen süre 1 saat.", "severity": "warning", "category": "freshness", "confidence": 0.85},
    ],
    "management": [
        {"id": "i1", "title": "7 blocked test release riskini artırıyor", "description": "Sprint 12 regression run içinde ödeme ve mobil doğrulama kaynaklı blocked testler var.", "severity": "warning", "category": "run", "confidence": 0.91},
        {"id": "i2", "title": "Coverage matrisi güncellenmeli", "description": "Checkout requirement setinde 11 kısmi coverage kaydı tespit edildi.", "severity": "info", "category": "coverage", "confidence": 0.84},
    ],
    "intelligence": [
        {"id": "i1", "title": "Groq token limiti yaklaşıyor", "description": "Günlük kota %78 kullanıldı — 6 saat içinde Gemini fallback devreye girebilir.", "severity": "warning", "category": "quota", "confidence": 0.91},
        {"id": "i2", "title": "LLM-Judge skoru artışta", "description": "GPT-4 judge kalite skoru bu haftaki referans 87→91.", "severity": "info", "category": "quality", "confidence": 0.88},
    ],
    "nexus-code": [
        {"id": "i1", "title": "4 PII bulgusu tespit edildi", "description": "auth.py ve user_service.py dosyalarında hardcoded PII pattern.", "severity": "critical", "category": "security", "confidence": 0.99},
        {"id": "i2", "title": "18 kod kokusu analiz edildi", "description": "3 dosyada uzun method ve yüksek cyclomatic complexity gözlemlendi.", "severity": "warning", "category": "quality", "confidence": 0.87},
    ],
}


# TODO: SELECT stat_key, agg_value, trend, severity
#        FROM products_metrics
#        WHERE product_id = :product_id
#          AND recorded_at >= NOW() - INTERVAL '7 days'
#        ORDER BY recorded_at DESC;
#       AI insights icin: SELECT * FROM ai_insights WHERE product_id = :product_id AND dismissed = FALSE;
@router.get("/{product_id}/telemetry", summary="Ürün telemetri verisi")
def get_product_telemetry(product_id: str) -> JSONResponse:
    # DEMO MODE: Gercek DB aggregation yerine PRODUCT_STATS sabit verisini kullanir.
    if product_id not in VALID_PRODUCT_IDS:
        raise HTTPException(status_code=404, detail=f"Geçersiz product_id: {product_id}")

    stats_template = PRODUCT_STATS.get(product_id, [])
    insights = AI_INSIGHTS.get(product_id, [])

    now = datetime.now(_tz.utc).isoformat()

    stats = [
        {
            **s,
            "value": s["value"] + random.randint(-2, 3),
            "sparkline": _sparkline(int(s["value"])),
            "delta": random.choice([-1, 0, 1, 2]),
            "deltaLabel": "bu hafta",
        }
        for s in stats_template
    ]

    payload = {
        "productId": product_id,
        "stats": stats,
        "aiInsights": [
            {**ins, "createdAt": now, "dismissed": False}
            for ins in insights
        ],
        "recentActivity": [],
        "onboarding": [],
        "lastUpdated": now,
        "isDemo": _DEMO_MODE,
        "demo_mode": _DEMO_MODE,
    }
    headers = {"X-Data-Mode": "demo"} if _DEMO_MODE else {}
    return JSONResponse(content=payload, headers=headers)


# ── Web product: karar destek endpoint'leri ──────────────────────────────────
#
# Bu uçlar henüz gerçek bir agregasyon backend'ine bağlı değil. Demo veri
# döndürerek frontend kontratını sabit tutar; gerçek implementasyon için
# her birinin TODO'su ilgili handler'ın üstünde belirtilmiştir.


_DEMO_NOTICE = (
    "DEMO_DATA: Bu endpoint henüz gercek aggregation'a baglanmadi -- "
    "donen veriler statik ornektir. "
    "Bkz: backend/app/domains/products/router.py TODO yorumlari."
)
_DEMO_HEADERS = {"X-Data-Mode": "demo", "X-Demo-Data": "true", "X-Demo-Notice": _DEMO_NOTICE}


def _now_iso() -> str:
    return datetime.now(_tz.utc).isoformat()


def _demo(payload: dict[str, Any]) -> JSONResponse:
    """Wrap a demo payload with X-Demo-Data headers so consumers can detect mock data."""
    payload.setdefault("_demo", {"notice": _DEMO_NOTICE, "realDataAvailable": False})
    return JSONResponse(content=payload, headers=_DEMO_HEADERS)


_RELEASE_HEALTH_FALLBACK = {
    "verdict": "caution",
    "release": "web@latest",
    "checks": [
        {"key": "visual", "label": "Visual regression",      "status": "warn", "detail": "1 kritik diff onay bekliyor",  "href": "#visual"},
        {"key": "a11y",   "label": "Accessibility (a11y)",   "status": "fail", "detail": "2 WCAG AA blocker — Checkout", "href": "#a11y"},
        {"key": "pass",   "label": "Pass rate (24s)",         "status": "ok",   "detail": "94.8% · hedef 92%",            "href": "#stats"},
        {"key": "perf",   "label": "Perf (Core Web Vitals)",  "status": "warn", "detail": "LCP 2.9s · hedef <2.5s",       "href": "#perf"},
    ],
}


# TODO: SELECT check_key, status, detail
#        FROM web_release_checks
#        WHERE project_id = :project_id
#          AND release_tag = (SELECT MAX(tag) FROM releases WHERE product = 'web');
#       Verdict, checks tablosundaki en kotu status'a gore hesaplanmali.
@router.get("/web/release-health", summary="Web release sağlığı (verdict + checks)")
def get_web_release_health(
    project_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    guard = _block_in_production("web/release-health")
    if guard is not None:
        return guard

    if not _DEMO_MODE:
        try:
            from app.domains.tspm.models import TspmExecutionMetrics

            cutoff = datetime.now(_tz.utc) - timedelta(hours=24)

            # Aggregate pass/fail over last 24h using TspmExecutionMetrics
            row = db.execute(
                select(
                    func.sum(TspmExecutionMetrics.total).label("total"),
                    func.sum(TspmExecutionMetrics.passed).label("passed"),
                    func.sum(TspmExecutionMetrics.failed).label("failed"),
                    func.avg(TspmExecutionMetrics.pass_rate).label("avg_pass_rate"),
                ).where(TspmExecutionMetrics.executed_at >= cutoff)
            ).one()

            total = row.total or 0
            passed = row.passed or 0
            failed = row.failed or 0
            pass_rate = float(row.avg_pass_rate or 0.0)

            pass_status = "ok" if pass_rate >= 92 else ("warn" if pass_rate >= 80 else "fail")
            pass_detail = f"{pass_rate:.1f}% · hedef 92% ({total} koşum)"

            # visual/a11y/perf: henüz ayrı DB tabloları yok; placeholder döndürülür.
            # TODO: web_visual_checks, web_a11y_checks, web_vitals_samples tablolarından çekilecek.
            _logger.warning(
                "release-health: visual/a11y/perf kontrolleri henüz DB'ye bağlanmadı — "
                "placeholder 'warn' değerleri döndürülüyor. "
                "Gerçek implementasyon için web_visual_checks ve web_a11y_checks tablolarını ekleyin."
            )
            checks = [
                {"key": "visual", "label": "Visual regression",     "status": "warn", "detail": "Placeholder — web_visual_checks tablosu henüz yok", "href": "#visual"},
                {"key": "a11y",   "label": "Accessibility (a11y)",  "status": "warn", "detail": "Placeholder — web_a11y_checks tablosu henüz yok",    "href": "#a11y"},
                {"key": "pass",   "label": "Pass rate (24s)",        "status": pass_status, "detail": pass_detail, "href": "#stats"},
                {"key": "perf",   "label": "Perf (Core Web Vitals)", "status": "warn", "detail": "Placeholder — web_vitals_samples tablosu henüz yok", "href": "#perf"},
            ]

            if any(c["status"] == "fail" for c in checks):
                verdict = "block"
            elif any(c["status"] == "warn" for c in checks):
                verdict = "caution"
            else:
                verdict = "ship"

            return JSONResponse(content={
                "verdict": verdict,
                "release": "web@latest",
                "checks": checks,
                "updatedAt": _now_iso(),
                "_demo": {"notice": "pass_rate from DB; visual/a11y/perf placeholders", "realDataAvailable": True},
            })
        except Exception as exc:
            _logger.warning("Products release-health DB sorgusu basarisiz: %s", exc)
            fallback = dict(_RELEASE_HEALTH_FALLBACK)
            fallback["updatedAt"] = _now_iso()
            return _demo(fallback)

    # DEMO MODE path
    checks = list(_RELEASE_HEALTH_FALLBACK["checks"])
    if any(c["status"] == "fail" for c in checks):
        verdict = "block"
    elif any(c["status"] == "warn" for c in checks):
        verdict = "caution"
    else:
        verdict = "ship"
    return _demo({
        "verdict": verdict,
        "release": "web@2.5.0-rc3",
        "checks": checks,
        "updatedAt": _now_iso(),
    })


_DAY_OVER_DAY_FALLBACK_METRICS = [
    {"key": "pass",     "label": "Pass Rate",   "today": "94.8%", "yesterday": "92.9%", "delta": 1.9,  "deltaUnit": "pp", "goodDirection": "up",   "spark": [88, 90, 89, 91, 92, 92, 94, 95]},
    {"key": "duration", "label": "Ort. Süre",   "today": "3.2dk", "yesterday": "3.6dk", "delta": -11,  "deltaUnit": "%",  "goodDirection": "down", "spark": [42, 40, 39, 38, 37, 36, 34, 32]},
    {"key": "flaky",    "label": "Flaky Test",  "today": "17",    "yesterday": "23",    "delta": -6,                       "goodDirection": "down", "spark": [28, 26, 25, 24, 23, 22, 19, 17]},
    {"key": "newfail",  "label": "Yeni Fail",   "today": "4",     "yesterday": "1",     "delta": 3,                        "goodDirection": "down", "spark": [0, 1, 2, 1, 3, 2, 3, 4]},
    {"key": "visdiff",  "label": "Visual Diff", "today": "4",     "yesterday": "6",     "delta": -2,                       "goodDirection": "down", "spark": [8, 7, 7, 6, 6, 5, 5, 4]},
    {"key": "runs",     "label": "Toplam Koşu", "today": "1.284", "yesterday": "1.156", "delta": 11,   "deltaUnit": "%",  "goodDirection": "up",   "spark": [950, 1000, 1080, 1120, 1150, 1156, 1200, 1284]},
]


# TODO: SELECT metric_key,
#               AVG(value) FILTER (WHERE recorded_at >= NOW() - INTERVAL '24h') AS today,
#               AVG(value) FILTER (WHERE recorded_at BETWEEN NOW() - INTERVAL '48h' AND NOW() - INTERVAL '24h') AS yesterday
#        FROM web_test_metrics
#        WHERE project_id = :project_id
#        GROUP BY metric_key;
@router.get("/web/day-over-day", summary="Bugün vs dün delta metrikleri")
def get_web_day_over_day(
    project_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    guard = _block_in_production("web/day-over-day")
    if guard is not None:
        return guard

    if not _DEMO_MODE:
        try:
            from app.domains.tspm.models import TspmExecutionMetrics

            now = datetime.now(_tz.utc)
            today_cutoff = now - timedelta(hours=24)
            yesterday_cutoff = now - timedelta(hours=48)

            # Today's aggregate (last 24h)
            today_row = db.execute(
                select(
                    func.count(TspmExecutionMetrics.id).label("runs"),
                    func.sum(TspmExecutionMetrics.total).label("total"),
                    func.sum(TspmExecutionMetrics.passed).label("passed"),
                    func.sum(TspmExecutionMetrics.failed).label("failed"),
                    func.avg(TspmExecutionMetrics.pass_rate).label("avg_pass_rate"),
                    func.avg(TspmExecutionMetrics.duration_seconds).label("avg_duration"),
                ).where(TspmExecutionMetrics.executed_at >= today_cutoff)
            ).one()

            # Yesterday's aggregate (24h-48h window)
            yesterday_row = db.execute(
                select(
                    func.count(TspmExecutionMetrics.id).label("runs"),
                    func.sum(TspmExecutionMetrics.total).label("total"),
                    func.sum(TspmExecutionMetrics.passed).label("passed"),
                    func.sum(TspmExecutionMetrics.failed).label("failed"),
                    func.avg(TspmExecutionMetrics.pass_rate).label("avg_pass_rate"),
                    func.avg(TspmExecutionMetrics.duration_seconds).label("avg_duration"),
                ).where(
                    TspmExecutionMetrics.executed_at >= yesterday_cutoff,
                    TspmExecutionMetrics.executed_at < today_cutoff,
                )
            ).one()

            t_pass = float(today_row.avg_pass_rate or 0.0)
            y_pass = float(yesterday_row.avg_pass_rate or 0.0)
            t_runs = int(today_row.runs or 0)
            y_runs = int(yesterday_row.runs or 0)
            t_dur = float(today_row.avg_duration or 0.0)
            y_dur = float(yesterday_row.avg_duration or 0.0)
            t_failed = int(today_row.failed or 0)
            y_failed = int(yesterday_row.failed or 0)

            run_delta_pct = round(((t_runs - y_runs) / y_runs * 100) if y_runs else 0, 1)
            dur_delta_pct = round(((t_dur - y_dur) / y_dur * 100) if y_dur else 0, 1)

            metrics = [
                {
                    "key": "pass", "label": "Pass Rate",
                    "today": f"{t_pass:.1f}%", "yesterday": f"{y_pass:.1f}%",
                    "delta": round(t_pass - y_pass, 1), "deltaUnit": "pp",
                    "goodDirection": "up", "spark": [],
                },
                {
                    "key": "duration", "label": "Ort. Süre",
                    "today": f"{t_dur:.0f}s", "yesterday": f"{y_dur:.0f}s",
                    "delta": dur_delta_pct, "deltaUnit": "%",
                    "goodDirection": "down", "spark": [],
                },
                {
                    "key": "newfail", "label": "Yeni Fail",
                    "today": str(t_failed), "yesterday": str(y_failed),
                    "delta": t_failed - y_failed,
                    "goodDirection": "down", "spark": [],
                },
                {
                    "key": "runs", "label": "Toplam Koşu",
                    "today": str(t_runs), "yesterday": str(y_runs),
                    "delta": run_delta_pct, "deltaUnit": "%",
                    "goodDirection": "up", "spark": [],
                },
            ]

            return JSONResponse(content={
                "windowHours": 24,
                "metrics": metrics,
                "updatedAt": _now_iso(),
                "_demo": {"notice": "real DB aggregation from tspm_execution_metrics", "realDataAvailable": True},
            })
        except Exception as exc:
            _logger.warning("Products day-over-day DB sorgusu basarisiz: %s", exc)
            return _demo({"windowHours": 24, "metrics": list(_DAY_OVER_DAY_FALLBACK_METRICS), "updatedAt": _now_iso()})

    return _demo({"windowHours": 24, "metrics": list(_DAY_OVER_DAY_FALLBACK_METRICS), "updatedAt": _now_iso()})


@router.get("/web/my-inbox", summary="Kullanıcıya atanmış açık işler")
def get_web_my_inbox(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        from app.domains.defects import service as defect_svc

        open_defects = defect_svc.list_defects(
            project_id=project_id,
            status="open",
        )
        awaiting = defect_svc.list_defects(
            project_id=project_id,
            status="awaiting_fix",
        )
        all_defects = open_defects + awaiting
        # dedupe by id (list_defects filtreli sonuç döner, birleşimde tekrar olabilir)
        seen: set[str] = set()
        deduped = []
        for d in all_defects:
            if d.id not in seen:
                seen.add(d.id)
                deduped.append(d)

        # En yeni 20 kayıt
        deduped = sorted(deduped, key=lambda d: d.updated_at, reverse=True)[:20]

        severity_to_priority = {"critical": "high", "major": "high", "minor": "med", "trivial": "low"}
        items = [
            {
                "id": d.id,
                "kind": "defect",
                "priority": severity_to_priority.get(d.severity, "med"),
                "title": d.title or "Açık Defect",
                "context": f"Proje: {d.project_id}" + (f" · Senaryo: {d.scenario_id}" if d.scenario_id else ""),
                "age": _format_age(d.created_at),
            }
            for d in deduped
        ]
        return {"items": items, "total": len(items), "updatedAt": _now_iso()}
    except Exception as e:
        _logger.warning("my-inbox sorgulama hatası: %s", e)
        return {"items": [], "total": 0, "updatedAt": _now_iso(), "_error": str(e)}


# TODO: SELECT page_url, page_label,
#               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY lcp) AS lcp_p75,
#               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY inp) AS inp_p75,
#               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cls) AS cls_p75,
#               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY fcp) AS fcp_p75,
#               PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY tbt) AS tbt_p75,
#               COUNT(*) AS sample_count
#        FROM web_vitals_samples
#        WHERE project_id = :project_id
#          AND sampled_at >= NOW() - INTERVAL '24h'
#        GROUP BY page_url, page_label;
#       Trend icin: son 8 gunluk gunluk p75 pencereler.
@router.get("/web/perf-metrics", summary="Core Web Vitals — sayfa başı + trend")
def get_web_perf_metrics(project_id: str | None = None) -> dict[str, Any]:
    guard = _block_in_production("web/perf-metrics")
    if guard is not None:
        return guard
    pages = [
        {"page": "Homepage",        "url": "/",         "lcp": 2100, "inp": 180, "cls": 0.04, "fcp": 1400, "tbt": 140, "sampleCount": 1284},
        {"page": "Checkout Step 1", "url": "/checkout", "lcp": 2900, "inp": 240, "cls": 0.12, "fcp": 1900, "tbt": 380, "sampleCount": 542},
        {"page": "Product Detail",  "url": "/p/:id",    "lcp": 3200, "inp": 310, "cls": 0.18, "fcp": 2100, "tbt": 520, "sampleCount": 743},
        {"page": "Login",           "url": "/login",    "lcp": 1600, "inp": 90,  "cls": 0.02, "fcp": 1100, "tbt": 80,  "sampleCount": 412},
        {"page": "Profile",         "url": "/profile",  "lcp": 2300, "inp": 210, "cls": 0.08, "fcp": 1500, "tbt": 180, "sampleCount": 287},
        {"page": "Cart",            "url": "/cart",     "lcp": 4100, "inp": 540, "cls": 0.31, "fcp": 2400, "tbt": 720, "sampleCount": 198},
    ]
    trend = {
        "lcp": [2.4, 2.5, 2.6, 2.5, 2.7, 2.8, 2.9, 2.9],
        "inp": [180, 195, 210, 200, 220, 240, 235, 250],
        "cls": [0.08, 0.09, 0.10, 0.11, 0.12, 0.12, 0.13, 0.14],
        "fcp": [1.6, 1.7, 1.7, 1.8, 1.8, 1.9, 1.9, 1.9],
        "tbt": [320, 340, 350, 360, 380, 400, 410, 420],
    }
    return _demo({"pages": pages, "trend": trend, "updatedAt": _now_iso()})


_VALID_INBOX_ACTIONS = {"dismiss", "snooze", "resolve", "assign", "approve", "reject", "reassign"}


@router.post("/web/my-inbox/{item_id}/{action}", summary="Inbox item aksiyonu")
def post_web_inbox_action(
    item_id: str,
    action: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    if action not in _VALID_INBOX_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Geçersiz aksiyon: {action}. Geçerli aksiyonlar: {sorted(_VALID_INBOX_ACTIONS)}")

    user_id = getattr(current_user, "id", "?")
    _logger.info("[inbox] action=%s item=%s user=%s", action, item_id, user_id)

    # resolve → defect'i kapat
    if action == "resolve":
        try:
            from app.domains.defects import service as defect_svc
            defect = defect_svc.get_defect(item_id)
            if defect is not None and defect.status not in ("closed", "verified"):
                defect_svc.verify_and_close(
                    item_id,
                    rerun_id=f"inbox-resolve-{user_id}",
                    rerun_passed=True,
                    actor=str(user_id),
                )
        except Exception as exc:
            _logger.warning("[inbox] resolve defect hatası item=%s: %s", item_id, exc)

    return {
        "ok": True,
        "item_id": item_id,
        "action": action,
        "resolvedAt": _now_iso(),
    }
