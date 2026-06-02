# Test Kapsama Raporu — 2026-05-27

## Özet

| Katman | Test Dosyası | Tahmini Test Sayısı | Kapsama |
|---|---|---|---|
| Backend Unit (temt/Neurex_QA) | 312 dosya | 3.500+ test | ~87% |
| Backend Unit (Cortex_Ai_Automation) | 321 dosya | 3.600+ test | ~87% |
| Engine Unit | 45 dosya (her iki repoda) | 500+ test | ~82% |
| AI Gateway Tests | 3 dosya (her iki repoda) | 50+ test | ~85% |
| Frontend Hook Tests | 4 dosya | 50+ test | ~80% |
| Integration Tests | 4 dosya | 40+ test | ~75% |
| **Toplam (temt/Neurex_QA)** | **364+** | **4.140+** | **~85%** |

## Backend Domain Kapsama

[Tüm domainler için bkz: backend-domain-coverage.md]

Yeni eklenenler (Wave 24):
- rate_limiting ✅ (test_rate_limiting.py — 14 test, AI gateway rate limit uygulama)
- exceptions ✅ (test_rate_limit_and_exceptions.py — 10 test, RateLimitError + handler kapsama)

Önceki sprintlerde tamamlananlar:
- rbac ✅ (service + router + 36 test)
- navigation ✅ (service + router + 21 test)
- email ✅ (service + router + 12 test)
- automation_templates ✅ (service + 14 test)
- migration ✅ (service + 12 test)
- pilot ✅ (router — 16 test)
- artifacts ✅ (router — 10 test)
- jobs ✅ (router — 12 test)
- rules ✅ (router — 11 test)

## Senkronizasyon Durumu (Wave 24)

| Repo | Backend Birim Test Dosyaları | Engine Birim Test Dosyaları | AI Gateway Testleri |
|---|---|---|---|
| temt/Neurex_QA | 312 | 45 | 3 |
| Cortex_Ai_Automation | 321 | 45 | 3 |

Wave 24'te 19 test dosyası Cortex_Ai_Automation'dan temt/Neurex_QA'ya portlandı (kümülatif toplam: 312).

## Engine Kapsama

Tüm 39 route dosyası unit testlere sahip.
Tüm 8 servis (llm_gateway, anomaly_detector, bdd_generator, vs.) test kapsamında.
Engine birim test dosya sayısı: 45 (her iki repoda eşit).

## AI Gateway Rate Limiting

- `test_rate_limiting.py` — 14 test (Wave 24):
  - `check_llm_rate_limit` limit aşımı → `RateLimitError`
  - Redis bağlantı hatası → `RuntimeError`
  - Başarılı istek akışı, sliding-window sayaç
  - `RateLimitError.retry_after_seconds` varsayılan/özel değer
  - 429 yanıt formatı + `Retry-After` başlık
  - Multi-tenant izolasyon senaryosu

## Frontend Hook Testleri

| Hook | Test Dosyası | Test Sayısı | Açıklama |
|---|---|---|---|
| useKnowledgeBase | useKnowledgeBase.test.ts | — | Backend-first pattern |
| useCustomDashboard | useCustomDashboard.test.ts | — | Widget state yönetimi |
| useNotifications | useNotifications.test.ts | 13 | Backend-first, hata geri alma, okundu/okunmadı |
| useLearningChecklist | useLearningChecklist.test.ts | 12 | Tamamlanma yüzdesi, backend hata senaryoları |

## Entegrasyon Testleri

| Dosya | Açıklama |
|---|---|
| test_router_registration.py | Router kaydı doğrulaması |
| test_service_layer_contracts.py | Servis katmanı kontrat doğrulaması (7 test) |
| test_exception_handler_coverage.py | HTTPException, ValidationError, unhandled exception |
| test_domain_endpoints.py | Domain endpoint erişilebilirlik doğrulaması |

## Frontend Bileşen Ayrıştırması

Toplam ayrıştırılan bileşen dosyası: **50+**

Wave 24'te eklenenler (10 bileşen):
- `monkey/`: MonkeyReportViewer, MonkeyActionTypeSelector
- `schedules/`: ScheduleCard, ScheduleForm
- `environments/`: EnvironmentCard, VariableEditor
- `ai-quality/`: QualityMetricsPanel, EvalHistoryList
- `dsl-catalog/`: DslActionCard, DslSearchBar

Sayfa satır azaltımları:
- `new-project/page.tsx`: 2787 → 1851 satır (Wave 22 tamamlandı)
- Diğer sayfalar ayrıştırma devam ediyor
## Güvenlik Tarama Bulguları

Tarih: 2026-05-26 — `backend/app/domains/auth/router.py`

| # | Bulgu | Öncelik | Dosya / Satır | Durum |
|---|---|---|---|---|
| 1 | Rate limiting no-op riski — slowapi yoksa `_limit` dekoratörü çalışmaz | P1 | auth/router.py: `_limit()` | TODO eklendi |
| 2 | `/refresh` endpoint'i dahili `ValueError` mesajını `detail` olarak sızdırıyor | P2 | auth/router.py: `refresh_token()` | TODO eklendi |
| 3 | Timing attack riski — kullanıcı yoksa erken dönüş, parola hash kontrolü atlanıyor olabilir | P1 | auth/router.py: `login()` | TODO eklendi |

Tüm bulgular için `# SECURITY TODO` yorumları ilgili satırlara eklendi. Gerçek düzeltmeler ayrı PR'da ele alınmalıdır.

## Backend Core Değişiklikleri (Wave 24)

- `backend/app/core/exceptions.py`: `RateLimitError(Exception)` — HTTP 429 karşılığı
- `backend/app/core/exception_handlers.py`: `rate_limit_error_handler` + `register_exception_handlers()` kaydı
- `backend/app/services/llm_rate_limiter.py`: HTTPException tamamen kaldırıldı → `RateLimitError` / `RuntimeError`
- `docs/backend-domain-coverage.md`: her iki repoda güncellendi
