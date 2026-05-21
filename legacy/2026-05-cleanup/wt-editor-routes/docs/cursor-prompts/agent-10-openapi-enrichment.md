# Agent 10: OpenAPI Documentation Zenginlestirme

## Cursor'a yapistir:

```
Sen bir API muhendisisin. BGTS bankacilik test otomasyon platformunun
OpenAPI/Swagger dokumantasyonunu zenginlestireceksin.

## KURALLAR
- Python 3.9 uyumlu
- Tum dosyalar ast.parse gecmeli
- Mevcut endpoint logic'e dokunma
- Swagger UI'da gorunen bilgileri zenginlestir

## MEVCUT DURUM
- backend/app/core/openapi_config.py — OpenAPI config dosyasi MEVCUT
  (custom_openapi_schema, API_TITLE, OPENAPI_TAGS, vb.)
- backend/app/main.py — OpenAPI config BAGLANMIS
  (app.openapi = lambda: custom_openapi_schema(app))
- Tum router'larda tags VAR

## YAPILACAKLAR

### Gorev 1: Tag Description'lari Zenginlestir

backend/app/core/openapi_config.py dosyasini oku. OPENAPI_TAGS listesindeki
her tag'in description'ini detayli yap. Mevcut kisa description'lari asagidaki
formatta genislet:

```python
OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "**Kimlik Dogrulama & Yetkilendirme**\n\n"
            "Kullanici girisi, kayit, JWT token yonetimi ve rol tabanli erisim kontrolu (RBAC).\n\n"
            "### Temel Akislar\n"
            "1. `POST /auth/login` ile JWT token alin\n"
            "2. Token'i `Authorization: Bearer <token>` header'inda gonderin\n"
            "3. `POST /auth/refresh` ile token yenileyin\n\n"
            "### Roller\n"
            "- **admin**: Tam yetki\n"
            "- **operator**: Test yonetimi\n"
            "- **viewer**: Salt okunur erisim"
        ),
    },
    {
        "name": "tspm",
        "description": (
            "**Test Suite & Process Management**\n\n"
            "Proje, senaryo, gereksinim, kosu, akis, zamanlama ve izlenebilirlik yonetimi.\n"
            "Platform'un en buyuk domain'i (~148 endpoint).\n\n"
            "### Endpoint Gruplari\n"
            "- `GET/POST /tspm/projects` — Proje CRUD\n"
            "- `GET/POST /tspm/projects/{id}/scenarios` — Senaryo CRUD\n"
            "- `GET/POST /tspm/projects/{id}/requirements` — Gereksinim yonetimi\n"
            "- `GET/POST /tspm/projects/{id}/executions` — Kosu yonetimi\n"
            "- `GET /tspm/projects/{id}/dashboard` — Proje istatistikleri\n"
            "- `GET /tspm/projects/{id}/traceability` — Izlenebilirlik matrisi\n"
            "- `GET/POST /tspm/projects/{id}/defects` — Hata kayitlari"
        ),
    },
    {
        "name": "ai",
        "description": (
            "**AI Zeka Katmani**\n\n"
            "LLM destekli chat, senaryo uretimi, test analizi ve streaming.\n"
            "OpenAI, Anthropic ve Ollama (local) provider destegi.\n\n"
            "### Endpoint Gruplari\n"
            "- `POST /ai/chat/{session}/message` — AI chat\n"
            "- `POST /ai/stream/scenarios` — SSE ile senaryo uretimi\n"
            "- `POST /ai/stream/analysis` — SSE ile test analizi\n"
            "- `POST /ai/{project}/suggest-scenarios` — Senaryo onerisi\n"
            "- `GET /ai/providers` — Mevcut LLM provider'lar"
        ),
    },
    {
        "name": "agents",
        "description": (
            "**AI Agent Sistemi**\n\n"
            "Bankacilik QA ekibi ajanlari, heal pipeline ve locator intelligence.\n\n"
            "### Alt Sistemler\n"
            "- **Heal Pipeline**: Kirilan selector'lari otomatik onarir\n"
            "- **Locator Intelligence**: 6 stratejili selector fallback zinciri\n"
            "- **Banking Team**: Senaryo, analiz, onceliklendirme ajanlari"
        ),
    },
    {
        "name": "coverup",
        "description": (
            "**CoverUp — Kod Kapsam Analizi**\n\n"
            "Coverage raporu yukleme, bosluk tespiti ve AI destekli test uretimi.\n"
            "LCOV, Istanbul, Cobertura ve Coverage.py formatlari desteklenir.\n\n"
            "### Akis\n"
            "1. `POST /coverup/upload` ile coverage raporu yukleyin\n"
            "2. `POST /coverup/analyze` ile bosluklari analiz edin\n"
            "3. `POST /coverup/generate` ile eksik testleri AI ile uretin"
        ),
    },
    {
        "name": "playwright-mcp",
        "description": (
            "**Playwright MCP — Browser Otomasyonu**\n\n"
            "Canli browser session yonetimi, DOM analizi, selector dogrulama ve\n"
            "ekran goruntusu alma. Self-healing icin Playwright live verification.\n\n"
            "### Endpoint Gruplari\n"
            "- `POST/GET/DELETE /playwright-mcp/sessions` — Session CRUD\n"
            "- `POST /playwright-mcp/sessions/{id}/navigate` — Sayfa navigasyonu\n"
            "- `POST /playwright-mcp/sessions/{id}/screenshot` — Ekran goruntusu\n"
            "- `POST /playwright-mcp/sessions/{id}/dom` — DOM snapshot\n"
            "- `POST /playwright-mcp/sessions/{id}/selectors/validate` — Selector dogrulama"
        ),
    },
    # Diger tag'ler icin de benzer detayli aciklamalar yaz:
    # catalog, rules, jobs, artifacts, notifications, audit,
    # automation, api-testing, synthetic, cicd, n8n
]
```

Her tag icin 3-8 satirlik Markdown description yaz. Endpoint ornekleri dahil et.

### Gorev 2: x-tagGroups Extension Ekle

custom_openapi_schema fonksiyonunda, schema dondurulmeden once tag gruplari ekle:

```python
    # Tag gruplari (ReDoc'ta gruplu gorunum icin)
    schema["x-tagGroups"] = [
        {"name": "Kimlik & Yetkilendirme", "tags": ["auth"]},
        {"name": "Test Yonetimi", "tags": ["tspm", "automation"]},
        {"name": "AI Zeka", "tags": ["ai", "agents"]},
        {"name": "Kalite & Kapsam", "tags": ["coverup", "playwright-mcp", "api-testing"]},
        {"name": "Altyapi", "tags": ["jobs", "artifacts", "notifications", "audit"]},
        {"name": "Veri & Kurallar", "tags": ["catalog", "rules", "synthetic"]},
        {"name": "Entegrasyonlar", "tags": ["cicd", "n8n"]},
    ]
```

### Gorev 3: Kritik Endpoint'lere Response Ornekleri Ekle

En cok kullanilan 5 endpoint'e response ornegi ekle (router dosyalarinda):

#### 1. backend/app/domains/auth/router.py — login endpoint
```python
@router.post(
    "/auth/login",
    responses={
        200: {
            "description": "Basarili giris",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "token_type": "bearer",
                        "expires_in": 1800,
                    }
                }
            },
        },
        401: {"description": "Hatali e-posta veya parola"},
        422: {"description": "Gecersiz istek formati"},
    },
)
```

#### 2. /health endpoint (main.py)
```python
@app.get(
    "/health",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"status": "ok", "service": "bgts-backend"}
                }
            }
        }
    },
)
```

#### 3. /ready endpoint (main.py)
```python
@app.get(
    "/ready",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "ready": True,
                        "checks": {
                            "database": {"status": "ok"},
                            "engine": {"status": "ok"},
                            "rate_limiter": {"status": "ok"},
                        },
                    }
                }
            }
        },
        503: {"description": "Servis hazir degil"},
    },
)
```

#### 4. TSPM — create project (tspm/router.py)
(router'dan endpoint decorator'unu bul ve responses ekle)

#### 5. AI — chat message (ai/router.py)
(router'dan endpoint decorator'unu bul ve responses ekle)

### Gorev 4: OpenAPI Test Guncelle

backend/tests/integration/test_openapi.py MEVCUT mu kontrol et.
Mevcutsa icerigini kontrol et, yoksa olustur:

```python
"""OpenAPI schema dogrulama testleri."""
from fastapi.testclient import TestClient


class TestOpenAPI:

    def test_openapi_json_available(self, client: TestClient):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema["info"]["title"] == "BGTS Nexus QA Platform API"

    def test_has_security_scheme(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in schemes

    def test_has_all_tags(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        tag_names = {t["name"] for t in schema.get("tags", [])}
        required = {"auth", "tspm", "ai", "agents", "coverup", "playwright-mcp"}
        missing = required - tag_names
        assert not missing, f"Eksik tag'ler: {missing}"

    def test_tags_have_descriptions(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        for tag in schema.get("tags", []):
            assert tag.get("description"), f"Tag '{tag['name']}' description'i bos"

    def test_has_tag_groups(self, client: TestClient):
        schema = client.get("/openapi.json").json()
        assert "x-tagGroups" in schema, "x-tagGroups extension eksik"

    def test_docs_endpoint(self, client: TestClient):
        assert client.get("/docs").status_code == 200

    def test_redoc_endpoint(self, client: TestClient):
        assert client.get("/redoc").status_code == 200
```

## DOGRULAMA
```bash
python3 -c "
import ast
for f in ['backend/app/core/openapi_config.py', 'backend/app/main.py',
          'backend/app/domains/auth/router.py']:
    ast.parse(open(f).read())
    print(f'✅ {f}')
"
```
```
