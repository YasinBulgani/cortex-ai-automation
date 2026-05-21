# BGTS Test Platformu — Master Index

**Oluşturulma Tarihi:** 2026-04-03
**Platform Sürümü:** v1.0.0

---

## Hızlı Erişim

| Ne Yapmak İstiyorsun? | Nereye Bak |
|------------------------|------------|
| Testleri çalıştır | `engine/scripts/run_bgts_tests.sh --smoke` |
| Manuel test senaryoları | `docs/test-analysis/manual-test-scenarios.md` |
| API'leri test et (Postman) | `collections/postman/BGTS_Backend_API.postman_collection.json` |
| Yeni POM ekle | `engine/pages/` — `BasePage`'den türet |
| Yeni feature ekle | `engine/features/BGTS/` — Türkçe Gherkin |
| Rapor oluştur | `python engine/bgts_runner.py --smoke --report` |
| CI durumunu gör | `.github/workflows/bgts-e2e.yml` |
| Platform kılavuzu | `docs/test-platform-guide.md` |

---

## Dosya Haritası (81 Dosya)

### 1. Dokümantasyon (5 dosya)

| Dosya | Açıklama |
|-------|----------|
| `docs/test-analysis/test-analysis.md` | Kapsamlı test analizi — scope, risk, öncelik matrisi |
| `docs/test-analysis/manual-test-scenarios.md` | 77 manuel test senaryosu (P0-P3) |
| `docs/test-analysis/test-sets.md` | Smoke / Regression / Integration / API set tanımları |
| `docs/test-platform-guide.md` | Kullanıcı kılavuzu |
| `docs/validation-report.md` | Agent doğrulama raporu |

### 2. Gherkin Feature Dosyaları (9 dosya, 196 senaryo)

| Dosya | Senaryo Sayısı | Kapsam |
|-------|---------------|--------|
| `engine/features/BGTS/login.feature` | 11 | Kimlik doğrulama |
| `engine/features/BGTS/projects.feature` | 10 | Proje CRUD |
| `engine/features/BGTS/scenarios.feature` | 14 | Senaryo yönetimi |
| `engine/features/BGTS/approvals.feature` | 11 | Onay iş akışı |
| `engine/features/BGTS/import.feature` | 10 | İçe aktarma |
| `engine/features/BGTS/synthetic_data.feature` | 14 | Sentetik veri |
| `engine/features/BGTS/api_tests.feature` | 39 | API endpoint testleri |
| `engine/features/BGTS/regression.feature` | 33 | Regresyon seti |
| `engine/features/BGTS/smoke.feature` | 15 | Smoke seti |

### 3. API Koleksiyonları (7 dosya, 141 endpoint)

| Dosya | Format | Endpoint |
|-------|--------|----------|
| `collections/postman/BGTS_Backend_API.postman_collection.json` | Postman v2.1 | 72 |
| `collections/postman/BGTS_Engine_API.postman_collection.json` | Postman v2.1 | 69 |
| `collections/postman/BGTS_Environment_Dev.postman_environment.json` | Postman Env | Dev |
| `collections/postman/BGTS_Environment_Staging.postman_environment.json` | Postman Env | Staging |
| `collections/http/backend-api.http` | VS Code REST | ~52 |
| `collections/http/engine-api.http` | VS Code REST | ~54 |
| `collections/http/smoke-tests.http` | VS Code REST | ~19 |

### 4. Locator & Page Object Model (15 dosya, 10 POM, 120+ locator)

| Dosya | Tür |
|-------|-----|
| `engine/locators/locator_repository.json` | Merkezi locator deposu |
| `engine/locators/locator_manager.py` | Self-healing locator yöneticisi |
| `engine/pages/login_page.py` | Login POM |
| `engine/pages/dashboard_page.py` | Dashboard POM |
| `engine/pages/projects_page.py` | Projeler POM |
| `engine/pages/scenarios_page.py` | Senaryolar POM (List + Form) |
| `engine/pages/approvals_page.py` | Onaylar POM |
| `engine/pages/import_page.py` | İçe Aktarma POM |
| `engine/pages/common_nav.py` | Ortak Navigasyon POM |
| `engine/pages/executions_page.py` | Koşumlar POM |
| `engine/pages/flows_page.py` | Akışlar POM |
| `engine/pages/regression_page.py` | Regresyon POM |

### 5. Step Definitions (9 dosya)

| Dosya | Feature Bağlantısı |
|-------|-------------------|
| `engine/steps/bgts_login_steps.py` | login.feature |
| `engine/steps/bgts_project_steps.py` | projects.feature |
| `engine/steps/bgts_scenario_steps.py` | scenarios.feature |
| `engine/steps/bgts_approval_steps.py` | approvals.feature |
| `engine/steps/bgts_import_steps.py` | import.feature |
| `engine/steps/bgts_synthetic_steps.py` | synthetic_data.feature |
| `engine/steps/bgts_smoke_steps.py` | smoke.feature |
| `engine/steps/bgts_regression_steps.py` | regression.feature |
| `engine/steps/bgts_api_steps.py` | api_tests.feature |

### 6. E2E Test Dosyaları (13 dosya)

| Dosya | Marker | Senaryo |
|-------|--------|---------|
| `engine/tests/e2e/conftest.py` | — | Playwright + POM fixture |
| `engine/tests/e2e/test_login.py` | functional | 11 |
| `engine/tests/e2e/test_projects.py` | functional | 10 |
| `engine/tests/e2e/test_scenarios.py` | functional | 14 |
| `engine/tests/e2e/test_approvals.py` | functional | 11 |
| `engine/tests/e2e/test_import.py` | functional | 10 |
| `engine/tests/e2e/test_synthetic_data.py` | functional | 14 |
| `engine/tests/e2e/test_smoke.py` | smoke | 15 |
| `engine/tests/e2e/test_regression.py` | regression | 33 |
| `engine/tests/e2e/test_api_bdd.py` | api | 39 |
| `engine/tests/e2e/test_api_integration.py` | api | 13 (httpx) |

### 7. Test Data (10 dosya)

| Dosya | İçerik |
|-------|--------|
| `engine/test_data/users.json` | 6 test kullanıcı profili |
| `engine/test_data/projects.json` | 5 test projesi |
| `engine/test_data/scenarios.json` | 20 test senaryosu |
| `engine/test_data/api_payloads.json` | 9 API istek şablonu |
| `engine/test_data/synthetic_data_config.json` | Sentetik veri profilleri |
| `engine/test_data/locator_test_data.json` | UI element doğrulama verisi |
| `engine/test_data/environments.json` | Dev/Staging/Prod ortam config |
| `engine/test_data/fixtures.py` | Python fixture fonksiyonları (TCKN, IBAN üretici) |

### 8. Runner & Reporter (3 dosya)

| Dosya | Açıklama |
|-------|----------|
| `engine/bgts_runner.py` | CLI test runner (--smoke, --regression, --api, --parallel) |
| `engine/core/bgts_reporter.py` | HTML/JSON/CSV rapor üretici |
| `engine/scripts/run_bgts_tests.sh` | Shell script runner |

### 9. CI/CD Pipeline (2 dosya)

| Dosya | Tetikleme |
|-------|-----------|
| `.github/workflows/bgts-e2e.yml` | Push/PR → smoke + api + regression |
| `.github/workflows/bgts-scheduled.yml` | Hafta içi 05:00 (TR) → tam regresyon |

### 10. Rapor Şablonları (6 dosya)

| Dosya | Format |
|-------|--------|
| `reports/templates/html_report.html` | Tailwind dark theme rapor |
| `reports/templates/email_report.html` | Email uyumlu inline CSS rapor |
| `reports/templates/execution_report.html` | Koşum detay raporu |
| `reports/templates/execution_report_schema.json` | Rapor JSON şeması |
| `reports/templates/execution_summary.md` | Markdown özet şablonu |
| `reports/README.md` | Rapor dokümantasyonu |

### 11. Konfigürasyon (2 dosya)

| Dosya | Açıklama |
|-------|----------|
| `engine/config/test_config.py` | Test ortam konfigürasyonu |
| `engine/allure-environment.properties` | Allure ortam bilgisi |

---

## Test Çalıştırma Komutları

```bash
# Smoke testleri (hızlı, ~5 dk)
cd engine && ./scripts/run_bgts_tests.sh --smoke

# Regresyon testleri (tam, ~30 dk)
cd engine && ./scripts/run_bgts_tests.sh --regression

# API testleri
cd engine && ./scripts/run_bgts_tests.sh --api

# Tüm testler (paralel)
cd engine && ./scripts/run_bgts_tests.sh --all --parallel

# Python CLI ile
cd engine && python bgts_runner.py --suite smoke --report
```

## İstatistikler

| Metrik | Değer |
|--------|-------|
| Toplam dosya | 81 |
| Toplam satır | ~18,000+ |
| Gherkin senaryo | 196 |
| BDD test fonksiyonu | 196 |
| API test (httpx) | 13 |
| POM sınıfı | 10 |
| Locator elementi | 120+ |
| API koleksiyon endpoint | 141 |
| Manuel test senaryosu | 77 |
| CI/CD pipeline | 2 |
| Rapor şablonu | 5 |
