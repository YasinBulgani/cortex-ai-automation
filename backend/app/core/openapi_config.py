"""OpenAPI / Swagger UI configuration for Neurex Platform."""
from __future__ import annotations

# ── API Metadata ────────────────────────────────────────────────────────

API_TITLE = "Neurex Platform API"
API_VERSION = "2.1.0"
API_DESCRIPTION = """
**Neurex Platform API** — AI destekli test otomasyon platformu.

## Ana Modüller
- **Auth**: JWT kimlik doğrulama, TOTP MFA, SSO (Google/Azure)
- **TSPM**: Test plan, test case, test run, defect yönetimi
- **AI**: LLM entegrasyonu, test üretimi, kalite analizi
- **Engine**: Test otomasyon motoru (Playwright, Appium)
- **API Testing**: OpenAPI spec parse, güvenlik taraması

## Ek Özellikler
- **CoverUp**: Kod kapsam analizi ve AI test üretimi
- **Synthetic Data**: KVKK uyumlu sentetik veri üretimi
- **CI/CD**: GitHub, GitLab, Jenkins webhook entegrasyonları
- **Audit Trail**: KVKK ve BDDK odaklı denetim izi kayıtları

## Kimlik Doğrulama
Bearer token (JWT) veya Cookie-based session kullanılır.
Token almak için `POST /api/v1/auth/login` endpoint'ini kullanın.

## Rate Limiting
Varsayılan: 60 istek/dakika (kullanıcı bazında). AI endpoint'leri: 20/dakika.
"""

API_CONTACT = {
    "name": "Neurex Platform Team",
    "email": "platform@testwright-ai.dev",
}

API_LICENSE = {
    "name": "Proprietary",
}

# ── OpenAPI Tags ────────────────────────────────────────────────────────

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "**Kimlik Dogrulama & Yetkilendirme**\n\n"
            "Kullanici girisi, kayit, JWT token yonetimi ve rol tabanli erisim kontrolu (RBAC).\n\n"
            "### Temel Akislar\n"
            "- `POST /api/v1/auth/login` ile access ve refresh token alin\n"
            "- `POST /api/v1/auth/refresh` ile oturumu yenileyin\n"
            "- `GET /api/v1/auth/me` ile aktif kullaniciyi sorgulayin"
        ),
    },
    {
        "name": "tspm",
        "description": (
            "**Test Suite & Process Management**\n\n"
            "Proje, senaryo, gereksinim, kosu, akis, zamanlama ve izlenebilirlik yonetimini kapsar.\n\n"
            "### Baslica Gruplar\n"
            "- `GET/POST /api/v1/tspm/projects` — Proje yonetimi\n"
            "- `GET/POST /api/v1/tspm/projects/{id}/scenarios` — Senaryo CRUD\n"
            "- `GET/POST /api/v1/tspm/projects/{id}/executions` — Kosu ve sonuc yonetimi"
        ),
    },
    {
        "name": "catalog",
        "description": (
            "**Veri Seti Katalogu**\n\n"
            "Test verisi setleri, surumleri ve sema snapshot'lari bu grupta yonetilir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/datasets` — Veri setlerini listeler\n"
            "- `POST /api/v1/datasets` — Yeni veri seti olusturur\n"
            "- `GET /api/v1/datasets/{id}/versions/{version_id}/schema` — Sema bilgisini getirir"
        ),
    },
    {
        "name": "rules",
        "description": (
            "**Is Kurallari Motoru**\n\n"
            "Veri setlerine bagli is kurali setlerini ve dogrulama mantiklarini yonetir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/datasets/{id}/rule-sets` — Kural setlerini listeler\n"
            "- `POST /api/v1/datasets/{id}/rule-sets` — Yeni kural seti olusturur\n"
            "- `GET /api/v1/datasets/{id}/rule-sets/{rule_set_id}` — Kural seti detayini getirir"
        ),
    },
    {
        "name": "jobs",
        "description": (
            "**Arka Plan Isleri**\n\n"
            "Veri uretim isleri, kuyruklanan gorevler ve bunlara ait olay/artifact kayitlari burada yer alir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/jobs` — Kuyruktaki ve tamamlanan isleri listeler\n"
            "- `POST /api/v1/jobs` — Yeni generation job olusturur\n"
            "- `GET /api/v1/jobs/{id}/events` — Is olaylarini getirir"
        ),
    },
    {
        "name": "artifacts",
        "description": (
            "**Artifact Yonetimi**\n\n"
            "Kosu ve generation sureclerinde uretilen dosyalari depolar ve indirilebilir hale getirir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/artifacts/{artifact_id}/download` — Artifact dosyasini indirir\n"
            "- Log, rapor ve cikti dosyalari bu alan uzerinden dagitilir"
        ),
    },
    {
        "name": "notifications",
        "description": (
            "**Bildirim Sistemi**\n\n"
            "Kullanici bazli bildirim tercihleri ve gercek zamanli websocket bildirimlerini yonetir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/notifications/prefs` — Tercihleri getirir\n"
            "- `PUT /api/v1/notifications/prefs` — Tercihleri gunceller\n"
            "- `WS /api/v1/ws/notifications` — Anlik bildirim akisini acar"
        ),
    },
    {
        "name": "automation",
        "description": (
            "**Otomasyon Motoru Proxy Katmani**\n\n"
            "Harici automation engine servisine health kontrolu ve transparan proxy erisimi saglar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/automation/health` — Engine sagligini kontrol eder\n"
            "- `/api/v1/automation/proxy/{path}` — Engine API'sine istek yonlendirir"
        ),
    },
    {
        "name": "audit",
        "description": (
            "**Denetim Izi**\n\n"
            "KVKK ve BDDK odakli audit trail kayitlarini, filtreleme ve sayfalama ile sunar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/audit/events` — Audit kayitlarini listeler\n"
            "- `action` ve `resource_type` query parametreleri ile filtreleme yapilabilir"
        ),
    },
    {
        "name": "ai",
        "description": (
            "**AI Zeka Katmani**\n\n"
            "LLM destekli chat, senaryo onerileri, test analizi ve streaming tabanli AI yardimcilari icerir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `POST /api/v1/ai/chat/sessions/{id}/messages` — AI sohbet mesaji gonderir\n"
            "- `POST /api/v1/ai/stream/scenarios` — SSE ile senaryo uretir\n"
            "- `POST /api/v1/ai/projects/{project_id}/analyze` benzeri akislarla proje bazli analiz saglanir"
        ),
    },
    {
        "name": "agents",
        "description": (
            "**AI Agent Sistemi**\n\n"
            "Bankacilik QA ajanlari, heal pipeline ve locator intelligence akislari bu grup altindadir.\n\n"
            "### Alt Sistemler\n"
            "- Banking team ajanlari ile otomatik analiz ve uretim\n"
            "- Heal pipeline ile kirilan selector onarimi\n"
            "- Agent tabanli orkestra ve saglik endpoint'leri"
        ),
    },
    {
        "name": "api-testing",
        "description": (
            "**API Testing**\n\n"
            "OpenAPI spec import, endpoint kesfi, test case uretimi, assertion ve execution analizini kapsar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `POST /api/v1/api-testing/projects/{id}/specs/import` — Spec ice aktarir\n"
            "- `POST /api/v1/api-testing/projects/{id}/execute/test-cases` — Test case kosusu baslatir\n"
            "- `GET /api/v1/api-testing/projects/{id}/coverage-analysis` — Kapsam analizini getirir"
        ),
    },
    {
        "name": "synthetic",
        "description": (
            "**Sentetik Veri Uretimi**\n\n"
            "KVKK uyumlu sentetik veri, bankacilik veri setleri ve differential privacy yardimcilari saglar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `POST /api/v1/synthetic/generate` — Ornek veriden sentetik kayit uretir\n"
            "- `POST /api/v1/synthetic/banking-dataset` — Bankacilik veri paketi uretir\n"
            "- `POST /api/v1/synthetic/privacy/*` — Mahremiyet analiz ve koruma islemleri"
        ),
    },
    {
        "name": "playwright-mcp",
        "description": (
            "**Playwright MCP**\n\n"
            "Canli browser oturumlari, DOM analizi, selector dogrulama ve ekran goruntusu alma islemlerini yonetir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- Session CRUD islemleri\n"
            "- Navigasyon, screenshot ve DOM snapshot akislari\n"
            "- Selector validation ve self-healing yardimcilari"
        ),
    },
    {
        "name": "n8n",
        "description": (
            "**n8n Entegrasyonu**\n\n"
            "n8n workflow callback'lerini kabul eder ve mevcut workflow listesini proxy eder.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `POST /api/v1/n8n/webhook/{workflow_id}` — Callback sonucunu alir\n"
            "- `GET /api/v1/n8n/available-workflows` — n8n workflow listesini getirir"
        ),
    },
    {
        "name": "coverup",
        "description": (
            "**CoverUp — Kod Kapsami**\n\n"
            "Coverage raporu yukleme, bosluk analizi ve AI destekli test uretim akislari sunar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `POST /api/v1/coverup/upload` — Coverage raporu yukler\n"
            "- `POST /api/v1/coverup/analyze` — Kapsam bosluklarini cikarir\n"
            "- `POST /api/v1/coverup/generate` — Eksik testleri uretir"
        ),
    },
    {
        "name": "cicd",
        "description": (
            "**CI/CD Entegrasyonlari**\n\n"
            "GitHub, GitLab ve Jenkins webhook'larini alir; quality gate ve impact analysis akislarini yonetir.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `POST /api/v1/cicd/webhook/github` — GitHub webhook kabul eder\n"
            "- `GET /api/v1/cicd/events` — Son CI/CD olaylarini listeler\n"
            "- `POST /api/v1/cicd/quality-gate/evaluate` — Kosu ozetini kalite kapisindan gecirir"
        ),
    },
    {
        "name": "products",
        "description": (
            "**Urun Metrikleri ve Dashboard**\n\n"
            "Urun bazli kalite metrikleri, KPI dashboard verileri ve trend analizlerini sunar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/products/{id}/metrics` — Urun kalite metriklerini getirir\n"
            "- `GET /api/v1/products/{id}/dashboard` — Dashboard ozet verisini getirir\n"
            "- `GET /api/v1/products/{id}/trends` — Zaman serisi trend analizini getirir"
        ),
    },
    {
        "name": "billing",
        "description": (
            "**Abonelik ve Faturalama**\n\n"
            "Stripe tabanli abonelik yonetimi, fatura gecmisi ve kullanim kotasi takibini kapsar.\n\n"
            "### Ornek Endpoint'ler\n"
            "- `GET /api/v1/billing/subscription` — Aktif aboneligi getirir\n"
            "- `POST /api/v1/billing/subscription/upgrade` — Plani yukseltir\n"
            "- `GET /api/v1/billing/invoices` — Fatura gecmisini listeler"
        ),
    },
]

# ── Custom OpenAPI Schema Hook ──────────────────────────────────────────


def custom_openapi_schema(app):
    """Generate custom OpenAPI schema with enhanced documentation."""
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=OPENAPI_TAGS,
        contact=API_CONTACT,
        license_info=API_LICENSE,
    )

    # Add security scheme
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from POST /api/v1/auth/login",
        }
    }

    # Apply security globally (except public endpoints)
    schema["security"] = [{"BearerAuth": []}]

    # Add server URLs
    schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://api.testwright-ai.dev", "description": "Production"},
    ]

    # Tag groups for richer ReDoc navigation
    schema["x-tagGroups"] = [
        {"name": "Kimlik & Yetkilendirme", "tags": ["auth"]},
        {"name": "Test Yonetimi", "tags": ["tspm", "automation"]},
        {"name": "AI Zeka", "tags": ["ai", "agents"]},
        {"name": "Kalite & Kapsam", "tags": ["coverup", "playwright-mcp", "api-testing"]},
        {"name": "Altyapi", "tags": ["jobs", "artifacts", "notifications", "audit"]},
        {"name": "Veri & Kurallar", "tags": ["catalog", "rules", "synthetic"]},
        {"name": "Entegrasyonlar", "tags": ["cicd", "n8n"]},
        {"name": "Platform", "tags": ["products", "billing"]},
    ]

    app.openapi_schema = schema
    return schema
