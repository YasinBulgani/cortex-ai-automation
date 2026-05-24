# BGTS Nexus QA — Improvement Plan (Cursor Agent Prompts)

Mevcut skor: **8.2/10** → Hedef: **9.5/10**

## Ozet: 10 Agent, 4 Faz

| Faz | Agent | Alan | Oncelik | Tahmini Dosya |
|-----|-------|------|---------|---------------|
| 1 | Agent 1 | AI Router Error Handling | CRITICAL | 1 dosya |
| 1 | Agent 2 | Diger Router'lar Error Handling | CRITICAL | 8 dosya |
| 2 | Agent 3 | Config Hardening & Secrets | HIGH | 2 dosya |
| 2 | Agent 4 | In-Memory → DB Migrasyonu | HIGH | 2 dosya |
| 2 | Agent 5 | Graceful Shutdown | HIGH | 2 dosya |
| 3 | Agent 6 | TSPM Test Suite (148 endpoint) | CRITICAL | 3-4 yeni dosya |
| 3 | Agent 7 | API Testing Domain Tests | HIGH | 1-2 yeni dosya |
| 3 | Agent 8 | Kalan Untested Domain'ler | HIGH | 3-4 yeni dosya |
| 4 | Agent 9 | Router Docstring'ler | MEDIUM | 12 dosya |
| 4 | Agent 10 | OpenAPI Ornekler & Response Model | MEDIUM | 5 dosya |

---

## FAZ 1: ERROR HANDLING STANDARDIZASYONU (6.5 → 9.0)

### AGENT 1: AI Router Error Handling Cleanup

```
Sen bir backend muhendisisin. BGTS bankacılık test otomasyon platformunda
backend/app/domains/ai/router.py dosyasindaki error handling'i standardize et.

KURALLAR:
- Python 3.9 uyumlu
- Dosya ast.parse gecmeli
- Mevcut davranisi bozma
- Tum hata mesajlari TURKCE olmali (proje dili Turkce)

SORUNLAR (16 adet raw 500 HTTPException):

1. Satirlar: 664, 773, 811, 834, 889, 931, 1085, 1115, 1143, 1168, 1193, 1214, 1253, 1284, 1315, 1342
   Hepsi su formatta:
   raise HTTPException(500, f"... hatası: {str(e)}")

   BUNLARI SU FORMATA DONUSTUR:
   raise HTTPException(
       status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
       detail={"error": "ai_service_error", "message": "...", "code": "AI_XXX"}
   )

2. Dosyanin basina ekle (yoksa):
   from fastapi import status
   import logging
   logger = logging.getLogger(__name__)

3. Her except blogunun ICINE logging ekle:
   except Exception as e:
       logger.exception("AI endpoint hatasi: %s", request.url.path)
       raise HTTPException(...)

4. Bare except blokları (satir 125, 185, 216, 258):
   Bunlara da logger.exception() ekle.

5. Error code mapping olustur (dosyanin basinda):
   ERROR_CODES = {
       "assert_advisor": "AI_001",
       "batch_ingest": "AI_002",
       "search": "AI_003",
       "cleanup": "AI_004",
       "router_stats": "AI_005",
       "fewshot_stats": "AI_006",
       "qa_plan": "AI_007",
       "qa_execute": "AI_008",
       "qa_verify": "AI_009",
       "qa_full_cycle": "AI_010",
       "qa_explore": "AI_011",
       "qa_status": "AI_012",
       "nl_generate": "AI_013",
       "nl_batch": "AI_014",
       "nl_suggest": "AI_015",
       "code_validate": "AI_016",
   }

6. Yardimci fonksiyon olustur:
   def _error_response(code: str, message: str, detail: str = "") -> dict:
       return {"error": code, "message": message, "detail": detail[:300]}

DOSYA: backend/app/domains/ai/router.py
SADECE error handling degistir, endpoint logic'e dokunma.
```

---

### AGENT 2: Diger Router'lar Error Handling Standardizasyonu

```
Sen bir backend muhendisisin. BGTS bankacılık test otomasyon platformunda
tum router dosyalarindaki error handling'i standardize et.

KURALLAR:
- Python 3.9 uyumlu
- Tum dosyalar ast.parse gecmeli
- Hata mesajlari TURKCE
- Her router dosyasina logger ekle
- Structured error response format kullan

HEDEF FORMAT (tum router'larda ayni):
{
    "error": "<DOMAIN>_<CODE>",
    "message": "Turkce aciklama",
    "detail": "teknik detay (opsiyonel)"
}

DUZELTILECEK DOSYALAR:

1. backend/app/domains/agents/router.py
   - Satir 267, 274, 284: bare except without logging
   - Logger ekle, exception logla

2. backend/app/domains/notifications/router.py
   - Satir 44: bare except Exception
   - Logger ekle, structured error don

3. backend/app/domains/n8n/router.py
   - Satir 46: raw HTTPException(404, "...")
   - Satir 51: bare except without logging
   - status.HTTP_404_NOT_FOUND kullan

4. backend/app/domains/cicd/router.py
   - Satir 85: raw 401 kullanılıyor
   - Satir 117: raw 401 kullanılıyor
   - status.HTTP_401_UNAUTHORIZED kullan

5. backend/app/domains/automation/router.py
   - Proxy pass-through hatalari yakalanmiyor
   - try/except ekle

6. backend/app/domains/playwright_mcp/router.py
   - Tutarsiz hata formatlari
   - Standardize et

7. backend/app/domains/tspm/router.py
   - Buyuk dosya, 148 endpoint
   - Her except bloguna logger.exception() ekle (yoksa)
   - Raw status code'lari status.HTTP_XXX ile degistir

8. backend/app/domains/coverup/router.py
   - Hata mesajlari standartlastir

HER DOSYA ICIN:
1. Dosyayi oku
2. Basina 'import logging' ve 'from fastapi import status' ekle
3. logger = logging.getLogger(__name__) ekle
4. Her bare except'e logger.exception() ekle
5. Raw status code'lari status constant ile degistir
6. Hata response'lari structured formata donustur
```

---

## FAZ 2: PRODUCTION READINESS (7.0 → 9.0)

### AGENT 3: Config Hardening & Secrets Management

```
Sen bir DevSecOps muhendisisin. BGTS bankacılık platformunun config
dosyasini production-grade yap.

DOSYA: backend/app/config.py

SORUNLAR:
1. Satir 12: _INSECURE_JWT_DEFAULT = "change-me-in-production-use-long-random-secret"
   - Bu deger development'ta bile tehlikeli
   - COZUM: Default'u kaldir, environment variable ZORUNLU yap
   - Development icin .env.example dosyasi olustur

2. Satir 25-28: Hardcoded database credentials
   database_url: str = "postgresql+psycopg2://bgts_user:bgts_pass@127.0.0.1:5432/syndata_db"
   redis_url: str = "redis://127.0.0.1:6379/0"
   - COZUM: Default'lari development-safe yap ama production'da zorunlu kontrol ekle

3. Satir 48-53: LLM API key'ler empty string default
   openai_api_key: str = ""
   anthropic_api_key: str = ""
   - COZUM: Validator ekle — ai_provider secilmisse ilgili key zorunlu olsun

4. Production guard ekle:
   @validator("jwt_secret")
   def check_jwt_secret_production(cls, v):
       if os.getenv("ENVIRONMENT", "development") == "production":
           if v == _INSECURE_JWT_DEFAULT or len(v) < 32:
               raise ValueError("Production'da guvenli JWT secret gerekli (min 32 karakter)")
       return v

5. Yeni .env.example dosyasi olustur (backend/.env.example):
   # BGTS Backend Configuration
   # Copy to .env and fill in values
   
   # REQUIRED
   DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/bgts_db
   JWT_SECRET=<min-32-karakter-rastgele-deger>
   
   # OPTIONAL — AI Provider (ollama|openai|anthropic)
   AI_PROVIDER=ollama
   OPENAI_API_KEY=
   ANTHROPIC_API_KEY=
   OLLAMA_BASE_URL=http://localhost:11434/v1
   
   # OPTIONAL — Monitoring
   SENTRY_DSN=
   PROMETHEUS_ENABLED=false
   
   # OPTIONAL — Environment
   ENVIRONMENT=development
   DEBUG=true

6. README'ye ekle: "Production deployment icin .env dosyasi ZORUNLUDUR"
```

---

### AGENT 4: In-Memory Storage → DB Migration

```
Sen bir backend muhendisisin. BGTS platformundaki in-memory storage'lari
veritabanina tasiyorsun.

SORUN 1: backend/app/domains/cicd/router.py (satir 40-56)
   _events: list[dict] = []  # In-memory — restart'ta kayboluyor!
   _MAX_EVENTS = 500

   COZUM:
   - Yeni tablo olustur: cicd_webhook_events
   - Alembic migration yaz: backend/alembic/versions/20260416_0004_add_cicd_events.py
   
   SQL:
   CREATE TABLE IF NOT EXISTS cicd_webhook_events (
       id SERIAL PRIMARY KEY,
       source VARCHAR(32) NOT NULL,       -- github, gitlab, jenkins
       event_type VARCHAR(64),            -- push, pull_request, pipeline
       payload JSONB NOT NULL DEFAULT '{}',
       commit_sha VARCHAR(64),
       branch VARCHAR(128),
       author VARCHAR(256),
       status VARCHAR(32) DEFAULT 'received',
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX idx_cicd_events_source ON cicd_webhook_events(source, created_at DESC);
   CREATE INDEX idx_cicd_events_branch ON cicd_webhook_events(branch, created_at DESC);
   
   - cicd/router.py'deki _events list'i kaldir
   - DB'ye yazma/okuma fonksiyonlari ekle
   - Mevcut endpoint'leri DB kullanacak sekilde guncelle

SORUN 2: backend/app/domains/coverup/router.py
   _reports: dict = {}  # In-memory coverage reports
   
   COZUM:
   - coverage_reports tablosu ZATEN mevcut (alembic 20260416_0003)
   - router.py'deki _reports dict'i kaldir
   - DB'ye yazma/okuma fonksiyonlari ekle:
     - INSERT INTO coverage_reports ... (upload)
     - SELECT FROM coverage_reports ... (list, get)
   - get_db dependency kullan (from app.infra.database import get_db)

DOSYALAR:
1. backend/alembic/versions/20260416_0004_add_cicd_events.py (YENI)
2. backend/app/domains/cicd/router.py (GUNCELLE)
3. backend/app/domains/coverup/router.py (GUNCELLE)
```

---

### AGENT 5: Graceful Shutdown & Lifecycle

```
Sen bir backend muhendisisin. BGTS platformunun graceful shutdown
mekanizmasini tamamla.

DOSYA: backend/app/main.py (lifespan fonksiyonu)

SORUNLAR:
1. Banking scheduler stop edilmiyor (start var, stop yok)
2. Background thread'ler daemon=True ama cleanup yok
3. Playwright browser sessions kapanmiyor
4. Redis connection pool kapanmiyor

COZUM — lifespan fonksiyonunu guncelle:

async def lifespan(app):
    # ── Startup ──
    start_scheduler()
    _start_banking_scheduler()
    _start_file_watcher()
    logger.info("BGTS Backend baslatildi")
    
    yield
    
    # ── Shutdown (sirali) ──
    logger.info("BGTS Backend kapatiliyor...")
    
    # 1. Playwright sessions kapat
    try:
        from app.domains.playwright_mcp.browser_manager import get_browser_manager
        bm = get_browser_manager()
        await bm.shutdown()
        logger.info("Playwright sessions kapatildi")
    except Exception:
        pass
    
    # 2. File watcher durdur
    try:
        from app.domains.ai.file_watcher import stop_file_watcher
        stop_file_watcher()
    except Exception:
        pass
    
    # 3. Banking scheduler durdur
    try:
        _stop_banking_scheduler()  # BU FONKSIYONU OLUSTUR
    except Exception:
        pass
    
    # 4. Ana scheduler durdur
    shutdown_scheduler()
    
    # 5. Redis connection kapat
    try:
        import redis
        # redis connection pool cleanup
    except Exception:
        pass
    
    logger.info("BGTS Backend kapatildi")

AYRICA:
- _stop_banking_scheduler() fonksiyonunu olustur (nerede start varsa orada)
- Her shutdown adimina timeout ekle (max 5 saniye)
```

---

## FAZ 3: TEST COVERAGE (6.5 → 9.0)

### AGENT 6: TSPM Integration Tests (EN BUYUK BOSLUK)

```
Sen bir QA muhendisisin. BGTS platformunun EN BUYUK test bosligini
kapatiyorsun: TSPM domain'i (148 endpoint, 0 test).

PROJE: /Users/yasin_bulgan/Desktop/Cortex_Ai_Automation
TEST DIZINI: backend/tests/integration/

MEVCUT ALTYAPI:
- backend/tests/conftest.py → client, auth_headers, db_ready fixture'lari
- backend/tests/api/conftest.py → create_project, project_id, create_scenario,
  create_requirement, create_execution, create_regression_set, create_flow,
  create_schedule, create_test_data factory fixture'lari

ROUTER DOSYASI: backend/app/domains/tspm/router.py
Bu dosyayi OKU ve tum endpoint'leri listele.

TSPM ENDPOINT GRUPLARI (tahmini, router'dan dogrula):
1. Projects CRUD: POST/GET/PUT/DELETE /tspm/projects
2. Scenarios CRUD: /tspm/projects/{pid}/scenarios
3. Requirements: /tspm/projects/{pid}/requirements
4. Executions: /tspm/projects/{pid}/executions
5. Steps: /tspm/projects/{pid}/scenarios/{sid}/steps
6. Tags: /tspm/projects/{pid}/tags
7. Regression Sets: /tspm/projects/{pid}/regression-sets
8. Flows: /tspm/projects/{pid}/flows
9. Schedules: /tspm/projects/{pid}/schedules
10. Test Data: /tspm/projects/{pid}/test-data
11. Imports: /tspm/projects/{pid}/imports
12. Dashboard/Stats: /tspm/projects/{pid}/dashboard
13. Traceability Matrix: /tspm/projects/{pid}/traceability
14. Defects: /tspm/projects/{pid}/defects
15. API Test Collections: /tspm/projects/{pid}/api-tests/*

OLUSTUR:

1. backend/tests/integration/test_tspm_core.py
   - TestProjectsCRUD: create, list, get, update, delete
   - TestScenariosCRUD: create, list, get, update, delete, bulk operations
   - TestRequirements: create, list, get, link to scenario
   - TestExecutions: create, list, get, update status

2. backend/tests/integration/test_tspm_advanced.py
   - TestSteps: add step, reorder, delete
   - TestTags: create tag, assign to scenario, filter by tag
   - TestRegressionSets: create, add scenarios, remove
   - TestFlows: create flow, add steps
   - TestSchedules: create, update cron, delete

3. backend/tests/integration/test_tspm_analytics.py
   - TestDashboard: get project dashboard stats
   - TestTraceability: get traceability matrix
   - TestImports: import from text, validate parsing
   - TestTestData: CRUD for test data sets

4. backend/tests/integration/test_tspm_defects.py
   - TestDefects: create, list, get, update, link to scenario/execution

HER TEST ICIN:
- db_ready yoksa skip et
- auth_headers kullan
- CRUD sirasi: create → get → list → update → delete
- Edge case'ler: duplicate name, not found, invalid data
- Temizlik: test bitince olusturdugunu sil (fixture teardown)

MINIMUM 60 TEST fonksiyonu hedefle.
```

---

### AGENT 7: API Testing Domain Tests

```
Sen bir QA muhendisisin. BGTS platformunun api_testing domain'ini
test ediyorsun (47 endpoint, 0 test).

ROUTER: backend/app/domains/api_testing/router.py
ONCELIKLE bu dosyayi OKU.

MEVCUT TESTLER (farkli yerde):
- backend/tests/api/test_api_tests.py → TestApiCollection (6 test)
  Bu testler api_testing altindaki collections endpoint'lerini test ediyor
  AMA tspm router uzerinden (/api/v1/tspm/projects/{pid}/api-tests/)

API Testing domain'in KENDI router'i ayri: /api/v1/api-testing/
Bu router'daki endpoint'ler icin test yaz.

OLUSTUR: backend/tests/integration/test_api_testing_domain.py

Endpoint gruplari (router'dan dogrula):
1. Environments: CRUD
2. OpenAPI Specs: upload, parse, list
3. Endpoints: list from spec, filter
4. Test Cases: AI-generated, manual, CRUD
5. Chains: request chain CRUD, execute
6. Execution Details: run results

HER GRUP ICIN:
- Auth guard testi (401)
- Happy path CRUD
- Edge case (invalid input, not found)
- En az 25 test fonksiyonu
```

---

### AGENT 8: Kalan Untested Domain'ler

```
Sen bir QA muhendisisin. BGTS platformundaki test edilmemis
domain'ler icin testler yaziyorsun.

PROJE: /Users/yasin_bulgan/Desktop/Cortex_Ai_Automation
MEVCUT FIXTURES: backend/tests/conftest.py (client, auth_headers, db_ready)

TEST EDILMEMIS DOMAINLER:

1. notifications (3 endpoint)
   Router: backend/app/domains/notifications/router.py
   ONCE OKU, sonra yaz: backend/tests/integration/test_notifications.py
   - test_list_notification_prefs
   - test_update_notification_prefs
   - test_notifications_requires_auth

2. audit (1+ endpoint)
   Router: backend/app/domains/audit/router.py
   ONCE OKU: backend/tests/integration/test_audit.py
   - test_audit_log_list
   - test_audit_log_requires_auth
   - test_audit_log_filter

3. automation (2 endpoint)
   Router: backend/app/domains/automation/router.py
   ONCE OKU: backend/tests/integration/test_automation.py
   - test_trigger_run
   - test_get_run_status
   - test_automation_requires_auth

4. cicd (7 endpoint)
   Router: backend/app/domains/cicd/router.py
   ONCE OKU: backend/tests/integration/test_cicd.py
   - test_github_webhook_signature_validation
   - test_gitlab_webhook_token_validation
   - test_list_events
   - test_webhook_requires_valid_signature

5. n8n (2 endpoint)
   Router: backend/app/domains/n8n/router.py
   ONCE OKU: backend/tests/integration/test_n8n.py
   - test_list_workflows
   - test_n8n_requires_auth

6. synthetic data (12+ endpoint)
   Router: bazen ai/router.py icinde, bazen synthetic/router.py
   backend/app/domains/synthetic/router.py OKU
   backend/tests/integration/test_synthetic.py
   - test_generate_synthetic_data
   - test_list_generators
   - test_synthetic_requires_auth

ONEMLI:
- Her router dosyasini ONCE OKU
- Endpoint path'lerini router'dan al (tahmin etme)
- Request body schema'larini Pydantic model'lerden al
- db_ready yoksa skip et
- Her domain icin en az 3-5 test
- TOPLAM en az 30 test fonksiyonu
```

---

## FAZ 4: DOCUMENTATION (6.0 → 8.5)

### AGENT 9: Router Endpoint Docstring'ler

```
Sen bir teknik yazar muhendisisin. BGTS platformundaki tum router
endpoint'lerine Turkce docstring ekliyorsun.

KURALLAR:
- Docstring TURKCE olmali
- Kisa ve ozlu: 1-2 satir
- OpenAPI'da gorunecek (Swagger UI)
- Mevcut docstring varsa DOKUNMA
- Python 3.9 uyumlu

FORMAT:
@router.get("/endpoint")
async def my_endpoint():
    """Endpoint'in kisa aciklamasi.

    Daha detayli aciklama gerekiyorsa burada.
    """

DOCSTRING EKSIK OLAN ROUTER'LAR:

1. backend/app/domains/artifacts/router.py — 1 endpoint, 0 docstring
2. backend/app/domains/catalog/router.py — 6 endpoint, 0 docstring
   Ornekler:
   - list_datasets → "Proje veri setlerini listeler."
   - create_dataset → "Yeni veri seti olusturur."
   - get_dataset → "Belirtilen veri setini getirir."

3. backend/app/domains/jobs/router.py — 5 endpoint, 0 docstring
   - list_jobs → "Arka plan islerini listeler."
   - enqueue_job → "Yeni arka plan isi olusturur."
   - get_job → "Is detayini getirir."

4. backend/app/domains/rules/router.py — 3 endpoint, 0 docstring
   - list_rule_sets → "Is kurali setlerini listeler."
   - create_rule_set → "Yeni is kurali seti olusturur."

5. backend/app/domains/auth/router.py — 15 endpoint, ~8 docstring (eksikleri tamamla)
6. backend/app/domains/tspm/router.py — 148 endpoint (sadece docstring OLMAYANLARA ekle)

HER DOSYA ICIN:
1. Dosyayi oku
2. Docstring olmayan endpoint'leri bul
3. Her birine 1-2 satirlik Turkce docstring ekle
4. ast.parse ile dogrula
```

---

### AGENT 10: OpenAPI Response Model & Ornekler

```
Sen bir API muhendisisin. BGTS platformunun OpenAPI dokumantasyonunu
zenginlestiriyorsun.

DOSYA: backend/app/core/openapi_config.py (mevcut)

GOREVLER:

1. Her tag'e detayli description ekle (mevcut tag'leri guncelle):
   Ornek:
   {
       "name": "tspm",
       "description": (
           "Test Suite & Process Management\n\n"
           "Proje, senaryo, gereksinim, kosu, akis, zamanlama yonetimi.\n\n"
           "### Endpoint Gruplari\n"
           "- `GET/POST /tspm/projects` — Proje CRUD\n"
           "- `GET/POST /tspm/projects/{id}/scenarios` — Senaryo CRUD\n"
           "- `GET/POST /tspm/projects/{id}/executions` — Kosu yonetimi\n"
           "- `GET /tspm/projects/{id}/dashboard` — Proje istatistikleri\n"
       ),
   }

2. Ana endpoint'lere response_model ekle (router dosyalarinda):
   Ornek (backend/app/domains/auth/router.py):
   @router.post("/auth/login", response_model=LoginResponse)

3. Ornek response'lar icin openapi_extra ekle:
   @router.post(
       "/auth/login",
       responses={
           200: {"description": "Basarili giris", "content": {"application/json": {"example": {"access_token": "eyJ...", "token_type": "bearer"}}}},
           401: {"description": "Hatali kimlik bilgileri"},
       }
   )

4. Grup basliklari icin x-tagGroups extension ekle:
   schema["x-tagGroups"] = [
       {"name": "Kimlik & Yetkilendirme", "tags": ["auth"]},
       {"name": "Test Yonetimi", "tags": ["tspm", "automation"]},
       {"name": "AI Zeka", "tags": ["ai", "agents"]},
       {"name": "Kalite", "tags": ["coverup", "playwright-mcp", "api-testing"]},
       {"name": "Altyapi", "tags": ["jobs", "artifacts", "notifications", "audit"]},
       {"name": "Veri", "tags": ["catalog", "rules", "synthetic"]},
       {"name": "Entegrasyon", "tags": ["cicd", "n8n"]},
   ]

ONCELIK SIRASI:
1. Tag description'lari zenginlestir (openapi_config.py)
2. En onemli 5 router'a response model ekle (auth, tspm, ai, agents, coverup)
3. Login ve health endpoint'lerine ornek response ekle
```

---

## UYGULAMA SIRASI

```
Faz 1 (Error Handling) → Agent 1 + Agent 2 paralel
Faz 2 (Production)     → Agent 3 + Agent 4 + Agent 5 paralel
Faz 3 (Tests)          → Agent 6 + Agent 7 + Agent 8 paralel
Faz 4 (Docs)           → Agent 9 + Agent 10 paralel
```

Her faz bittikten sonra dogrulama:
```bash
# Backend syntax check
cd backend && python3 -c "
import ast, pathlib
errors = []
for f in pathlib.Path('app').rglob('*.py'):
    try:
        ast.parse(f.read_text())
    except SyntaxError as e:
        errors.append(f'{f}: {e}')
print(f'Checked {len(list(pathlib.Path(\"app\").rglob(\"*.py\")))} files')
if errors:
    print('ERRORS:', *errors, sep='\n')
else:
    print('ALL PASS')
"

# Test suite
cd backend && python3 -m pytest tests/ -v --tb=short -q

# Frontend
cd apps/web && npx tsc --noEmit
```

## BEKLENEN SONUC

| Alan | Once | Sonra |
|------|------|-------|
| Error Handling | 6.5 | 9.0 |
| Production Ready | 7.0 | 9.0 |
| Test Coverage | 6.5 | 9.0 |
| Documentation | 6.0 | 8.5 |
| **GENEL** | **8.2** | **9.3** |
