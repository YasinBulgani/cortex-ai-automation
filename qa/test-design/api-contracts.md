# BGTS Test Dönüşüm — API Contract Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Base URL:** `http://127.0.0.1:8000/api/v1`  
**Araçlar:** Schemathesis, Dredd, Pydantic model doğrulama

---

## 1. Genel API Kontrat Kuralları

| Kural | Açıklama |
|-------|----------|
| Content-Type | Tüm yanıtlar `application/json` |
| HTTP Kodları | 200 (OK), 201 (Created), 204 (No Content), 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden), 404 (Not Found), 422 (Validation Error) |
| ID Format | UUID v4 string |
| Tarih Format | ISO 8601 UTC (`2026-04-03T12:00:00+00:00`) |
| Sayfalandırma | `page`, `page_size` query parametreleri (uygulamaya göre) |
| Hata Yanıtı | `{ "detail": "Mesaj" }` formatı |

---

## 2. Endpoint Contract Testleri

### AUTH Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-001 | `/auth/login` | POST | `{ email: EmailStr, password: str(min=1) }` | `{ access_token: str, token_type: "bearer" }` | 200 |
| API-002 | `/auth/me` | GET | Header: `Authorization: Bearer <token>` | `{ id: str, email: str, roles: [str], permissions: [str] }` | 200 |

### TSPM Project Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-010 | `/tspm/projects` | GET | — | `[{ id, name, description, archived }]` | 200 |
| API-011 | `/tspm/projects` | POST | `{ name: str(min=1), description?: str }` | `{ id, name, description, archived: false }` | 201 |
| API-012 | `/tspm/projects/{id}/dashboard` | GET | — | `{ scenario_count, pending_approvals, import_count, ai_run_pending, execution_count, latest_run_pass_rate? }` | 200 |

### TSPM Scenario Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-020 | `.../scenarios` | GET | `q?: str` | `[{ id, title, status, current_version, description?, steps?, updated_at? }]` | 200 |
| API-021 | `.../scenarios` | POST | `{ title: str(min=1), description?, status?, steps? }` | `{ id, title, status:"draft", current_version:1 }` | 201 |
| API-022 | `.../scenarios/{id}` | GET | — | `ScenarioOut` | 200 |
| API-023 | `.../scenarios/{id}` | PUT | `{ title?, description?, status?, steps? }` | `ScenarioOut (version+1)` | 200 |
| API-024 | `.../scenarios/bulk-delete` | POST | `{ ids: [str] }` | — | 204 |
| API-025 | `.../scenarios/generate-bdd` | POST | `{ analysis_text: str(min=10), extra_instructions? }` | `{ scenarios: [BddGeneratedScenario] }` | 200 |
| API-026 | `.../scenarios/save-bdd` | POST | `{ scenarios: [BddGeneratedScenario] }` | `[ScenarioOut]` | 201 |

### Execution Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-030 | `.../executions` | GET | — | `[ExecutionOut]` | 200 |
| API-031 | `.../executions` | POST | `{ name?, scenario_ids: [str] }` | `ExecutionOut { status:"running" }` | 201 |
| API-032 | `.../executions/{id}` | GET | — | `ExecutionDetailOut { results: [ExecutionResultOut] }` | 200 |
| API-033 | `.../results/{id}` | PATCH | `{ status: str }` | `{ ok: true }` | 200 |
| API-034 | `.../executions/{id}` | POST | — (re-run) | `ExecutionOut` | 201 |

### Requirement & Coverage Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-040 | `.../requirements` | POST | `{ external_id: str(min=1), title: str(min=1), priority?, source? }` | `RequirementOut` | 201 |
| API-041 | `.../requirements` | GET | — | `[RequirementOut { scenario_count }]` | 200 |
| API-042 | `.../scenarios/{id}/requirements` | POST | `{ requirement_ids: [str] }` | `{ ok: true }` | 201 |
| API-043 | `.../coverage-matrix` | GET | — | `CoverageMatrixOut { rows, total_requirements, covered_count, coverage_percent }` | 200 |
| API-044 | `.../coverage-gaps` | GET | — | `[RequirementOut]` | 200 |

### Schedule Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-050 | `.../schedules` | POST | `{ name: str(min=1), cron_expression: str(min=1), scenario_ids?, regression_set_id?, is_active? }` | `ScheduleOut` | 201 |
| API-051 | `.../schedules/{id}/trigger` | POST | — | `ExecutionOut` | 201 |

### Regression Set Endpoints

| ID | Endpoint | Metod | Request Schema | Response Schema | Status |
|----|----------|-------|---------------|-----------------|--------|
| API-060 | `.../regression-sets` | POST | `{ name: str(min=1), description? }` | `RegressionSetOut` | 201 |
| API-061 | `.../regression-sets/{id}/add` | POST | `{ scenario_ids: [str] }` | `{ ok: true, count: int }` | 200 |
| API-062 | `.../regression-sets/suggest` | POST | `{ extra_instructions? }` | `RegressionSuggestResponse { sets }` | 200 |

---

## 3. Contract Test Senaryoları

### Şema Doğrulama Testleri

| ID | Başlık | Test |
|----|--------|------|
| CT-001 | Tüm GET list endpoint'leri JSON array döner | Her list endpoint'in yanıtı `[]` formatında |
| CT-002 | Tüm POST endpoint'leri 201 ile id döner | Oluşturma endpoint'leri UUID id içermeli |
| CT-003 | Tüm 404 yanıtları detail mesajı içerir | `{ "detail": "..." }` formatı |
| CT-004 | Tüm 422 yanıtları validation error formatında | Pydantic error format |
| CT-005 | DateTime alanları ISO 8601 formatında | `created_at`, `updated_at` timezone-aware |
| CT-006 | Boolean alanları true/false (string değil) | `archived`, `is_active` |
| CT-007 | JSONB alanları null veya valid JSON | `steps`, `nodes`, `edges`, `config` |
| CT-008 | Optional alanlar null olabilir | `description`, `decided_at`, `note` |

### Backward Compatibility Testleri

| ID | Başlık | Test |
|----|--------|------|
| CT-010 | Ek alan gönderimi yok sayılır | Extra field'lar ile POST yapıldığında hata vermemeli |
| CT-011 | Eksik optional alan varsayılan değer alır | description gönderilmezse "" olmalı |
| CT-012 | API versiyonu header'ı | `/api/v1/` prefix korunmalı |

### Error Response Contract

| HTTP Kodu | Durum | Response Format |
|-----------|-------|----------------|
| 400 | Bad Request | `{ "detail": "Türkçe açıklama" }` |
| 401 | Unauthorized | `{ "detail": "..." }` |
| 403 | Forbidden | `{ "detail": "..." }` |
| 404 | Not Found | `{ "detail": "X bulunamadı" }` |
| 422 | Validation Error | `{ "detail": [{ "loc": [...], "msg": "...", "type": "..." }] }` |

---

## 4. OpenAPI Spec Uyumluluk

| Test | Açıklama |
|------|----------|
| Swagger UI erişilebilir | `GET /docs` → HTML sayfa |
| OpenAPI JSON erişilebilir | `GET /openapi.json` → valid JSON |
| Tüm endpoint'ler dokümante | openapi.json'da tüm path'ler mevcut |
| Request body şemaları tanımlı | Her POST/PUT için schema mevcut |
| Response şemaları tanımlı | Her endpoint için response model |

**Toplam API Contract Test Sayısı: 45+**
