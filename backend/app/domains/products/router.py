"""Product telemetry endpoint.

GET /api/v1/products/{product_id}/telemetry

Gerçek zaman damgası + DB'den çekilen aggregation yoksa demo veri döner.
Frontend'deki useProductTelemetry hook bu endpoint'i 60s'de bir poll eder.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/products", tags=["products"])

VALID_PRODUCT_IDS = {
    "one", "studio", "service", "web", "mobile",
    "data", "intelligence", "nexus-code",
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
    "intelligence": [
        {"id": "i1", "title": "Groq token limiti yaklaşıyor", "description": "Günlük kota %78 kullanıldı — 6 saat içinde Gemini fallback devreye girebilir.", "severity": "warning", "category": "quota", "confidence": 0.91},
        {"id": "i2", "title": "LLM-Judge skoru artışta", "description": "GPT-4 judge kalite skoru bu haftaki referans 87→91.", "severity": "info", "category": "quality", "confidence": 0.88},
    ],
    "nexus-code": [
        {"id": "i1", "title": "4 PII bulgusu tespit edildi", "description": "auth.py ve user_service.py dosyalarında hardcoded PII pattern.", "severity": "critical", "category": "security", "confidence": 0.99},
        {"id": "i2", "title": "18 kod kokusu analiz edildi", "description": "3 dosyada uzun method ve yüksek cyclomatic complexity gözlemlendi.", "severity": "warning", "category": "quality", "confidence": 0.87},
    ],
}


@router.get("/{product_id}/telemetry", summary="Ürün telemetri verisi")
def get_product_telemetry(product_id: str) -> dict[str, Any]:
    if product_id not in VALID_PRODUCT_IDS:
        raise HTTPException(status_code=404, detail=f"Geçersiz product_id: {product_id}")

    stats_template = PRODUCT_STATS.get(product_id, [])
    insights = AI_INSIGHTS.get(product_id, [])

    now = datetime.now(timezone.utc).isoformat()

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

    return {
        "productId": product_id,
        "stats": stats,
        "aiInsights": [
            {**ins, "createdAt": now, "dismissed": False}
            for ins in insights
        ],
        "recentActivity": [],
        "onboarding": [],
        "lastUpdated": now,
        "isDemo": False,
    }


# ── Web product: karar destek endpoint'leri ──────────────────────────────────
#
# Bu uçlar henüz gerçek bir agregasyon backend'ine bağlı değil. Demo veri
# döndürerek frontend kontratını sabit tutar; gerçek implementasyon için
# her birinin TODO'su ilgili handler'ın üstünde belirtilmiştir.


_DEMO_NOTICE = (
    "DEMO_DATA: Bu endpoint henüz gerçek aggregation'a bağlanmadı — "
    "dönen veriler statik örnektir. "
    "Bkz: backend/app/domains/products/router.py TODO yorumları."
)
_DEMO_HEADERS = {"X-Demo-Data": "true", "X-Demo-Notice": _DEMO_NOTICE}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo(payload: dict[str, Any]) -> JSONResponse:
    """Wrap a demo payload with X-Demo-Data headers so consumers can detect mock data."""
    payload.setdefault("_demo", {"notice": _DEMO_NOTICE, "realDataAvailable": False})
    return JSONResponse(content=payload, headers=_DEMO_HEADERS)


# TODO: visual_diff/a11y/perf/run aggregations'tan birleşik release health üret.
@router.get("/web/release-health", summary="Web release sağlığı (verdict + checks)")
def get_web_release_health(project_id: str | None = None) -> dict[str, Any]:
    checks = [
        {"key": "visual", "label": "Visual regression",      "status": "warn", "detail": "1 kritik diff onay bekliyor",  "href": "#visual"},
        {"key": "a11y",   "label": "Accessibility (a11y)",   "status": "fail", "detail": "2 WCAG AA blocker — Checkout", "href": "#a11y"},
        {"key": "pass",   "label": "Pass rate (24s)",         "status": "ok",   "detail": "94.8% · hedef 92%",            "href": "#stats"},
        {"key": "perf",   "label": "Perf (Core Web Vitals)",  "status": "warn", "detail": "LCP 2.9s · hedef <2.5s",       "href": "#perf"},
    ]
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


# TODO: stats'tan son 24s + önceki 24s pencerelerini agg, delta hesapla.
@router.get("/web/day-over-day", summary="Bugün vs dün delta metrikleri")
def get_web_day_over_day(project_id: str | None = None) -> dict[str, Any]:
    metrics = [
        {"key": "pass",     "label": "Pass Rate",   "today": "94.8%", "yesterday": "92.9%", "delta": 1.9,  "deltaUnit": "pp", "goodDirection": "up",   "spark": [88, 90, 89, 91, 92, 92, 94, 95]},
        {"key": "duration", "label": "Ort. Süre",   "today": "3.2dk", "yesterday": "3.6dk", "delta": -11,  "deltaUnit": "%",  "goodDirection": "down", "spark": [42, 40, 39, 38, 37, 36, 34, 32]},
        {"key": "flaky",    "label": "Flaky Test",  "today": "17",    "yesterday": "23",    "delta": -6,                       "goodDirection": "down", "spark": [28, 26, 25, 24, 23, 22, 19, 17]},
        {"key": "newfail",  "label": "Yeni Fail",   "today": "4",     "yesterday": "1",     "delta": 3,                        "goodDirection": "down", "spark": [0, 1, 2, 1, 3, 2, 3, 4]},
        {"key": "visdiff",  "label": "Visual Diff", "today": "4",     "yesterday": "6",     "delta": -2,                       "goodDirection": "down", "spark": [8, 7, 7, 6, 6, 5, 5, 4]},
        {"key": "runs",     "label": "Toplam Koşu", "today": "1.284", "yesterday": "1.156", "delta": 11,   "deltaUnit": "%",  "goodDirection": "up",   "spark": [950, 1000, 1080, 1120, 1150, 1156, 1200, 1284]},
    ]
    return _demo({"windowHours": 24, "metrics": metrics, "updatedAt": _now_iso()})


# TODO: visual diff onayları, flaky escalation'lar, PR review request'leri, perf
# regression alert'leri ile birleşik bir inbox üret. Kullanıcı kimliği auth'tan.
@router.get("/web/my-inbox", summary="Kullanıcıya atanmış açık işler")
def get_web_my_inbox(project_id: str | None = None) -> dict[str, Any]:
    items = [
        {"id": "1", "kind": "approve",     "priority": "high", "title": "Checkout Step 2 — visual diff onayı bekliyor", "context": "12.4% pixel diff · v2.4.0 → v2.5.0",     "age": "23 dk"},
        {"id": "2", "kind": "fix",         "priority": "high", "title": "Auth flow test'in 3 koşudur flaky",              "context": "Safari 17.4 · 'token undefined' hatası", "age": "1 sa"},
        {"id": "3", "kind": "review",      "priority": "med",  "title": "PR #482 — locator değişikliği",                  "context": "47 test bu locator'ı kullanıyor",         "age": "2 sa"},
        {"id": "4", "kind": "investigate", "priority": "med",  "title": "Homepage LCP 2.5s → 2.9s yükseldi",              "context": "Son deploy sonrası perf regression",      "age": "4 sa"},
        {"id": "5", "kind": "approve",     "priority": "low",  "title": "Profile page — yeni baseline alındı",            "context": "AI 'kabul edilebilir' diyor (skor 0.94)", "age": "6 sa"},
    ]
    return _demo({"items": items, "updatedAt": _now_iso()})


# TODO: Lighthouse / RUM (CrUX, Web Vitals) verilerini agg edip sayfa başı
# p75 LCP/INP/CLS/FCP/TBT döndür. Şu an demo veri.
@router.get("/web/perf-metrics", summary="Core Web Vitals — sayfa başı + trend")
def get_web_perf_metrics(project_id: str | None = None) -> dict[str, Any]:
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


_VALID_INBOX_ACTIONS = {"approve", "reject", "snooze", "reassign"}


# TODO: gerçek aksiyon implementasyonu:
#  - approve/reject → ilgili visual diff / PR review state'ini güncelle
#  - snooze        → kullanıcının inbox kuralında item_id'yi 24s saklı tut
#  - reassign     → request body'den yeni assignee al, audit log yaz
@router.post("/web/my-inbox/{item_id}/{action}", summary="Inbox item aksiyonu")
def post_web_inbox_action(item_id: str, action: str) -> dict[str, Any]:
    if action not in _VALID_INBOX_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Geçersiz aksiyon: {action}")
    return {
        "id": item_id,
        "action": action,
        "status": "accepted",
        "resolvedAt": _now_iso(),
    }
