"""OpenAPI / Swagger UI configuration for TestwrightAI Platform."""
from __future__ import annotations

# ── API Metadata ────────────────────────────────────────────────────────

API_TITLE = "TestwrightAI Platform API"
API_VERSION = "2.0.0"
API_DESCRIPTION = (
    "TestwrightAI — AI-powered test automation platform "
    "for banking and fintech applications.\n\n"
    "## Features\n"
    "- **Test Process Management (TSPM)**: Projects, scenarios, executions, requirements\n"
    "- **AI Intelligence**: LLM-powered test generation, analysis, and streaming\n"
    "- **Playwright MCP**: Browser automation with live DOM healing\n"
    "- **CoverUp**: Code coverage analysis and AI test generation\n"
    "- **Locator Intelligence**: Self-healing selectors with 6-strategy fallback\n"
    "- **API Testing**: Postman-compatible collection runner\n"
    "- **Banking Compliance**: KVKK, BDDK, PCI-DSS aware testing\n\n"
    "## Authentication\n"
    "All endpoints (except /health, /ready) require a Bearer JWT token.\n"
    "Obtain a token via `POST /api/v1/auth/login`.\n\n"
    "## Rate Limiting\n"
    "Default: 60 requests/minute per user. AI endpoints: 20/minute."
)

API_CONTACT = {
    "name": "TestwrightAI Platform Team",
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
    ]

    app.openapi_schema = schema
    return schema
