# BGTS Test Dönüşüm — Test Tasarımı Master Index

**Oluşturma Tarihi:** 2026-04-03  
**Hazırlayan:** Analysis to Test Design Agent  
**Platform:** BGTS Test Dönüşüm — Test Yönetimi, Sentetik Veri, AI Destekli Otomasyon

---

## Doküman Haritası

```
docs/test-design/
├── README.md                           ← Bu dosya (Master Index)
│
│   ── ANA TEST TASARIMI ──
├── BGTS_Test_Design.md                 ← Ana test tasarımı (75 senaryo, 17 iş kuralı)
├── BGTS_Test_Design.json               ← Ana test tasarımı (JSON format)
│
│   ── GENİŞLETİLMİŞ TEST KATEGORİLERİ ──
├── BGTS_E2E_UI_Test_Scenarios.md       ← E2E/UI test senaryoları (59 yeni)
├── BGTS_Security_Tests.md              ← Güvenlik test senaryoları (33)
├── BGTS_Performance_Tests.md           ← Performans/Yük testleri (28)
├── BGTS_RBAC_Test_Matrix.md            ← RBAC yetkilendirme matrisi (180+)
├── BGTS_API_Contract_Tests.md          ← API kontrat testleri (45+)
├── BGTS_CrossCutting_Tests.md          ← Cross-cutting concerns (42)
├── BGTS_Advanced_Scenarios.md          ← İleri seviye (84: concurrency, a11y, DI)
├── BGTS_Specialized_Tests.md           ← Uzmanlaşmış (49: WebSocket, i18n, edge)
├── BGTS_N8N_AiChat_Tests.md            ← n8n workflow + AI chat (24)
├── BGTS_SynData_Module_Tests.md        ← Sentetik veri modülü (38)
├── BGTS_Engine_Proxy_Notification_Tests.md ← Engine proxy + notification (25)
├── BGTS_Engine_Module_Tests.md         ← Flask Engine tüm blueprint'ler (66)
├── BGTS_Exploratory_UAT.md             ← Keşifsel test + UAT (32)
├── BGTS_Extended_Traceability.md       ← Genişletilmiş traceability matrisi
│
│   ── OPERASYONEL REHBERLER ──
├── BGTS_Smoke_Release_Checklist.md     ← Smoke test + release go/no-go
├── BGTS_Test_Data_Guide.md             ← Test verisi hazırlama rehberi
├── BGTS_Risk_Findings.md               ← 10 kritik risk bulgusu + aksiyon planı
├── BGTS_BDD_Step_Definitions_Map.md    ← BDD step definitions eşleştirme
│
│   ── GHERKIN BDD FEATURE DOSYALARI ──
└── features/
    ├── authentication.feature
    ├── project_management.feature
    ├── scenario_management.feature
    ├── execution_and_analytics.feature
    ├── requirements_coverage.feature
    ├── regression_sets.feature
    └── schedules_and_test_data.feature
```

---

## Genel İstatistikler

| Metrik | Değer |
|--------|-------|
| **Toplam Doküman** | 21 dosya |
| **Gherkin Feature Dosyası** | 11 dosya |
| **Toplam Doküman Satırı** | ~6.500+ |
| **Risk Bulgusu** | 10 (2 critical, 3 high) |

### Test Senaryo Sayıları

| Kategori | Sayı |
|----------|------|
| Ana Manuel Test Senaryoları | 75 |
| E2E / UI Test Senaryoları (yeni) | 59 |
| Güvenlik Test Senaryoları | 33 |
| Performans Test Senaryoları | 28 |
| RBAC Matris Kombinasyonları | 180+ |
| API Contract Testleri | 45+ |
| Cross-Cutting Testleri | 42 |
| Concurrency / Race Condition | 8 |
| Negative E2E Journeys | 10 |
| Erişilebilirlik (a11y) | 14 |
| Browser / Viewport uyumluluk | 42 |
| Data Integrity | 10 |
| Smoke / Release Checklist | 30 |
| Uzmanlaşmış (WebSocket, i18n, Edge) | 49 |
| n8n + AI Chat | 24 |
| Sentetik Veri Modülü | 38 |
| Engine Proxy & Notifications | 25 |
| Engine Flask (16 blueprint) | 66 |
| Keşifsel Test + UAT | 32 |
| **GENEL TOPLAM** | **810+** |

### Ana Test Tasarımı Dağılımı (75 senaryo)

| Tip | Sayı | Yüzde |
|-----|------|-------|
| Pozitif | 42 | %56 |
| Negatif | 16 | %21 |
| Boundary | 16 | %21 |
| Exception | 1 | %2 |

| Öncelik | Sayı |
|---------|------|
| Critical | 10 |
| High | 35 |
| Medium | 25 |
| Low | 5 |

---

## Kapsanan Modüller

| # | Modül | BR Sayısı | Test Sayısı | BDD Feature |
|---|-------|-----------|-------------|-------------|
| 1 | Kimlik Doğrulama (Auth) | BR-001 | 10 | ✅ `authentication.feature` |
| 2 | Proje Yönetimi | BR-002 | 8 | ✅ `project_management.feature` |
| 3 | Senaryo Yönetimi | BR-003 | 9 | ✅ `scenario_management.feature` |
| 4 | BDD Üretimi | BR-004 | 4 | ✅ (scenario_management içinde) |
| 5 | Onay Kuyruğu | BR-005 | 4 | ✅ (authentication feature içinde) |
| 6 | İçe Aktarma | BR-006 | 4 | ⏳ (stub) |
| 7 | Test Koşuları | BR-007 | 6 | ✅ `execution_and_analytics.feature` |
| 8 | Koşu Analitikleri | BR-008 | 5 | ✅ (execution feature içinde) |
| 9 | Akış Editörü | BR-009 | 3 | — |
| 10 | Regresyon Setleri | BR-010 | 6 | ✅ `regression_sets.feature` |
| 11 | Gereksinimler/Kapsam | BR-011 | 7 | ✅ `requirements_coverage.feature` |
| 12 | Zamanlamalar | BR-012 | 5 | ✅ `schedules_and_test_data.feature` |
| 13 | Test Verisi | BR-013 | 4 | ✅ (schedules feature içinde) |
| 14 | Entegrasyonlar | BR-014 | 3 | — |
| 15 | API Testi | BR-015 | 4 | — |
| 16 | Proje Üyeleri | BR-016 | 3 | — |
| 17 | Versiyonlama | BR-017 | 3 | ✅ (scenario feature içinde) |

---

## Doküman Açıklamaları

### 1. [BGTS_Test_Design.md](./BGTS_Test_Design.md)
**Ana test tasarım dokümanı.** 17 iş kuralı, 16 test seti, 75 detaylı test senaryosu, BDD feature özetleri (Gherkin), traceability matrisi. Hem markdown hem [JSON](./BGTS_Test_Design.json) formatında.

### 2. [BGTS_E2E_UI_Test_Scenarios.md](./BGTS_E2E_UI_Test_Scenarios.md)
**Frontend E2E test analizi.** Mevcut 34 Playwright testinin kapsam analizi, 59 yeni eksik E2E senaryo önerisi. Login, proje, senaryo, koşu, akış, regresyon, gereksinim, zamanlama, test verisi, entegrasyon ve cross-cutting UI testleri.

### 3. [BGTS_Security_Tests.md](./BGTS_Security_Tests.md)
**Güvenlik test senaryoları.** 33 senaryo: authentication (JWT manipulation, brute force), authorization (IDOR, RBAC bypass), injection (SQL, XSS, NoSQL, CRLF), CORS, rate limiting, veri güvenliği. Risk matrisi dahil.

### 4. [BGTS_Performance_Tests.md](./BGTS_Performance_Tests.md)
**Performans ve yük test senaryoları.** 28 senaryo: API yanıt süreleri (12 endpoint), yük testleri (normal/stres/spike/soak), veritabanı performansı (N+1 query, index), frontend performansı (Lighthouse, bundle size).

### 5. [BGTS_RBAC_Test_Matrix.md](./BGTS_RBAC_Test_Matrix.md)
**RBAC yetkilendirme test matrisi.** 60+ endpoint × 3 rol (admin/operator/viewer) = 180+ kombinasyon. Endpoint bazında izin gereksinimleri, erişim/reddetme beklentileri. Kritik güvenlik bulguları ve öneriler.

### 6. [BGTS_API_Contract_Tests.md](./BGTS_API_Contract_Tests.md)
**API kontrat testleri.** 45+ test: endpoint şema doğrulama, request/response format, HTTP durum kodları, backward compatibility, OpenAPI spec uyumluluk. Schemathesis/Dredd araçları ile otomatize edilebilir.

### 7. [BGTS_CrossCutting_Tests.md](./BGTS_CrossCutting_Tests.md)
**Cross-cutting concerns testleri.** 42 senaryo: audit logging (7), webhooks (7), rate limiting (5), error handling (7), data versioning (4), quality dashboard (3), export templates (5), import (4).

### 8. [BGTS_Advanced_Scenarios.md](./BGTS_Advanced_Scenarios.md)
**İleri seviye test senaryoları.** Concurrency/race condition (8), negative E2E user journeys (10), erişilebilirlik/a11y (14), browser/viewport uyumluluk (42), data integrity (10). Test otomasyon fizibilite değerlendirmesi (%93 otomatize edilebilir). Sprint bazlı execution plan.

### 9. [BGTS_Smoke_Release_Checklist.md](./BGTS_Smoke_Release_Checklist.md)
**Smoke test ve release kontrol listesi.** 25 maddelik pre-release smoke, 5 maddelik post-release doğrulama, P0/P1/P2 regresyon matrisi, Go/No-Go karar kriterleri.

### 10. [BGTS_Risk_Findings.md](./BGTS_Risk_Findings.md)
**Kritik risk bulguları.** 10 bulgu: RBAC enforce eksikliği (9/10), IDOR (9/10), JWT secret varsayılan (6/10), SSRF API runner (5/10), CORS açık (5/10). Aksiyon planı ve sprint bazlı çözüm önerileri.

### 11. [BGTS_Test_Data_Guide.md](./BGTS_Test_Data_Guide.md)
**Test verisi hazırlama rehberi.** Kullanıcı seed verileri, API ile veri oluşturma scriptleri (curl), farklı ölçeklerde veri setleri (smoke/fonksiyonel/performans), veritabanı temizleme komutları, test veri durumları matrisi.

### 12. [features/](./features/)
**Çalıştırılabilir Gherkin BDD feature dosyaları.** 7 dosya, Türkçe (`# language: tr`), pytest-bdd veya Behave ile çalıştırılabilir. Tag'ler: `@critical`, `@high`, `@pozitif`, `@negatif`, `@boundary`.

---

## Kullanım Önerileri

1. **Sprint Planlama:** Ana test tasarımındaki (75 senaryo) öncelik ve tip bilgilerini kullanarak sprint bazında test kapsamı belirleyin
2. **Otomasyon:** Gherkin feature dosyalarını pytest-bdd framework'üne entegre edin
3. **Regresyon:** RBAC matrisini her release öncesi koşun; güvenlik bulguları acil çözülmeli
4. **CI/CD:** API contract testlerini pipeline'a ekleyin
5. **Performans:** Performans test hedeflerini SLA olarak kabul edin; k6 ile otomatize edin
6. **Test Verisi:** `BGTS_Test_Data_Guide.md` rehberini kullanarak ortam hazırlayın
