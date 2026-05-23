# BGTS Test Dönüşüm — Test Seti Tanımları

**Hazırlayan:** QA Analiz Ekibi  
**Tarih:** 2026-04-03  
**Versiyon:** 1.0

---

## 1. Smoke Test Seti (~15 Senaryo)

**Amaç:** Her deployment sonrası platformun temel fonksiyonlarının çalışır durumda olduğunu doğrulamak.  
**Çalıştırma Zamanı:** Her deployment, her commit (CI/CD pipeline)  
**Tahmini Süre:** 3-5 dakika  
**Başarı Kriteri:** %100 geçme zorunlu — başarısızlıkta deployment geri alınır  
**Feature Dosyası:** `engine/features/BGTS/smoke.feature`

| # | Senaryo ID | Senaryo Adı | Modül | Öncelik |
|---|-----------|-------------|-------|---------|
| 1 | SMOKE-01 | Backend sağlık kontrolü (`GET /health`) | Altyapı | P0 |
| 2 | SMOKE-02 | Veritabanı bağlantı kontrolü (`GET /ready`) | Altyapı | P0 |
| 3 | SMOKE-03 | Başarılı kullanıcı girişi | Auth | P0 |
| 4 | SMOKE-04 | Proje listesi görüntüleme | Projects | P0 |
| 5 | SMOKE-05 | Senaryo listesi görüntüleme | Scenarios | P0 |
| 6 | SMOKE-06 | Senaryo oluşturma formu erişimi | Scenarios | P0 |
| 7 | SMOKE-07 | Onay kuyruğu erişimi | Approvals | P0 |
| 8 | SMOKE-08 | İçe aktarma sayfası erişimi | Import | P0 |
| 9 | SMOKE-09 | Dashboard istatistikleri | Dashboard | P0 |
| 10 | SMOKE-10 | Engine feature listesi erişimi | Engine | P0 |
| 11 | SMOKE-11 | Auth API token alma | Auth API | P0 |
| 12 | SMOKE-12 | TSPM proje API erişimi | TSPM API | P0 |
| 13 | SMOKE-13 | Kullanıcı çıkış işlemi | Auth | P0 |
| 14 | SMOKE-14 | Korumalı sayfa erişim engeli | Auth | P0 |
| 15 | SMOKE-15 | Regresyon seti API erişimi | Regression API | P0 |

### Smoke Test Akış Diyagramı

```
Başla → Sağlık Kontrolü → DB Kontrolü → Login → Proje Listesi
  → Senaryo Listesi → Senaryo Formu → Onay Kuyruğu → İçe Aktarma
  → Dashboard → Engine API → Auth API → TSPM API → Logout
  → Erişim Engeli → Regresyon API → Bitti
```

### Başarısızlık Prosedürü

1. Herhangi bir smoke test başarısız → deployment otomatik geri alınır
2. Hata detayları Allure raporunda ve Slack kanalında paylaşılır
3. Sorumlu geliştirici hemen bilgilendirilir
4. Düzeltme sonrası smoke test tekrar çalıştırılır

---

## 2. Regresyon Test Seti (~100 Senaryo)

**Amaç:** Sprint sonu ve release öncesi tüm kritik iş akışlarının tam doğrulaması.  
**Çalıştırma Zamanı:** Sprint sonu, release öncesi, gece koşusu (cron: 02:00)  
**Tahmini Süre:** 30-45 dakika  
**Başarı Kriteri:** ≥ %95 geçme oranı  
**Feature Dosyası:** `engine/features/BGTS/regression.feature`

### 2.1 Kimlik Doğrulama Regresyonu (8 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 1 | REG-AUTH-001 | Başarılı giriş ve yönlendirme | TC-AUTH-001 |
| 2 | REG-AUTH-002 | Hatalı parola ile giriş reddi | TC-AUTH-002 |
| 3 | REG-AUTH-003 | Geçersiz e-posta ile giriş reddi | TC-AUTH-003 |
| 4 | REG-AUTH-004 | Devre dışı hesap erişim engeli | TC-AUTH-004 |
| 5 | REG-AUTH-005 | JWT kullanıcı bilgisi sorgulama | TC-AUTH-005 |
| 6 | REG-AUTH-006 | Geçersiz token ile erişim reddi | TC-AUTH-006 |
| 7 | REG-AUTH-007 | Kullanıcı menüsü görünürlüğü | login.feature |
| 8 | REG-AUTH-008 | Oturum kapatma akışı | login.feature |

### 2.2 Proje Yönetimi Regresyonu (10 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 9 | REG-PRJ-001 | Proje listesi erişimi | TC-PRJ-002 |
| 10 | REG-PRJ-002 | Yeni proje oluşturma | TC-PRJ-001 |
| 11 | REG-PRJ-003 | Proje dashboard erişimi | TC-PRJ-003 |
| 12 | REG-PRJ-004 | Dashboard istatistik doğruluğu | TC-PRJ-003 |
| 13 | REG-PRJ-005 | Olmayan proje ID ile 404 hatası | TC-PRJ-004 |
| 14 | REG-PRJ-006 | Proje üyesi ekleme | TC-PRJ-005 |
| 15 | REG-PRJ-007 | Proje navigasyonu — Senaryolar | projects.feature |
| 16 | REG-PRJ-008 | Proje navigasyonu — Onaylar | projects.feature |
| 17 | REG-PRJ-009 | Proje navigasyonu — İçe Aktarma | projects.feature |
| 18 | REG-PRJ-010 | Proje adı olmadan oluşturma hatası | projects.feature |

### 2.3 Senaryo Yönetimi Regresyonu (20 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 19 | REG-SCN-001 | Senaryo listesi erişimi | TC-SCN-003 |
| 20 | REG-SCN-002 | Yeni senaryo oluşturma | TC-SCN-001 |
| 21 | REG-SCN-003 | Senaryo arama fonksiyonu | TC-SCN-003 |
| 22 | REG-SCN-004 | Senaryo detay görüntüleme | scenarios.feature |
| 23 | REG-SCN-005 | Senaryo düzenleme | TC-SCN-002 |
| 24 | REG-SCN-006 | Senaryo güncelleme + versiyon artışı | TC-SCN-002 |
| 25 | REG-SCN-007 | Versiyon geçmişi | TC-SCN-007 |
| 26 | REG-SCN-008 | Versiyon karşılaştırma (diff) | TC-SCN-008 |
| 27 | REG-SCN-009 | BDD senaryo üretimi | TC-SCN-005 |
| 28 | REG-SCN-010 | BDD senaryoları kaydetme | TC-SCN-006 |
| 29 | REG-SCN-011 | Toplu seçim fonksiyonu | scenarios.feature |
| 30 | REG-SCN-012 | Toplu silme | TC-SCN-004 |
| 31 | REG-SCN-013 | Senaryo başlığı olmadan kaydetme hatası | scenarios.feature |
| 32 | REG-SCN-014 | Boş arama sonucu | scenarios.feature |
| 33 | REG-SCN-015 | Başka projenin senaryosuna erişim engeli | TC-SCN-009 |
| 34 | REG-SCN-016 | Senaryo adım ekleme | scenarios.feature |
| 35 | REG-SCN-017 | Senaryo-gereksinim bağlama | TC-REQ-002 |
| 36 | REG-SCN-018 | Genişletilmiş senaryo görüntüleme | TC-SYN-006 |
| 37 | REG-SCN-019 | Test verisi bağlama | TC-SYN-006 |
| 38 | REG-SCN-020 | Senaryo durum güncelleme | TC-SCN-002 |

### 2.4 Onay İş Akışı Regresyonu (10 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 39 | REG-APR-001 | Onay kuyruğu listesi | TC-APR-001 |
| 40 | REG-APR-002 | Onay detay split view | TC-APR-005 |
| 41 | REG-APR-003 | Kaynak doküman inceleme | approvals.feature |
| 42 | REG-APR-004 | AI taslak inceleme | approvals.feature |
| 43 | REG-APR-005 | Onaylama akışı | TC-APR-002 |
| 44 | REG-APR-006 | Reddetme akışı | TC-APR-003 |
| 45 | REG-APR-007 | Düzenleyerek onaylama | approvals.feature |
| 46 | REG-APR-008 | Olmayan onay ID ile hata | TC-APR-004 |
| 47 | REG-APR-009 | Onaylanan taslağın senaryo havuzuna eklenmesi | approvals.feature |
| 48 | REG-APR-010 | Bekleyen onay sayısı doğrulama | approvals.feature |

### 2.5 İçe Aktarma Regresyonu (6 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 49 | REG-IMP-001 | İçe aktarma sayfası erişimi | TC-IMP-001 |
| 50 | REG-IMP-002 | Dosya yükleme alanı | import.feature |
| 51 | REG-IMP-003 | Dosya seçimi ve yükleme | import.feature |
| 52 | REG-IMP-004 | AI işleme sonuçları | import.feature |
| 53 | REG-IMP-005 | İçe aktarma geçmişi | import.feature |
| 54 | REG-IMP-006 | Geçersiz dosya formatı hatası | TC-IMP-003 |

### 2.6 Test Koşusu Regresyonu (10 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 55 | REG-EXC-001 | Koşu oluşturma | TC-EXC-001 |
| 56 | REG-EXC-002 | Koşu sonucu güncelleme | TC-EXC-002 |
| 57 | REG-EXC-003 | Koşu yeniden çalıştırma | TC-EXC-003 |
| 58 | REG-EXC-004 | Koşu listesi erişimi | regression.feature |
| 59 | REG-EXC-005 | Koşu detayı görüntüleme | regression.feature |
| 60 | REG-EXC-006 | Koşu trendleri | TC-EXC-004 |
| 61 | REG-EXC-007 | Koşu istatistikleri | manual-test-scenarios |
| 62 | REG-EXC-008 | Flaky test tespiti | TC-EXC-005 |
| 63 | REG-EXC-009 | Koşu metrik doğrulaması | TSPM router |
| 64 | REG-EXC-010 | Re-run isim formatı doğrulama | TC-EXC-003 |

### 2.7 Regresyon Seti ve Zamanlama Regresyonu (8 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 65 | REG-REG-001 | Regresyon seti oluşturma | TC-REG-001 |
| 66 | REG-REG-002 | Sete senaryo ekleme | TC-REG-002 |
| 67 | REG-REG-003 | AI set önerisi | TC-REG-003 |
| 68 | REG-REG-004 | Öneri kabul etme | TC-REG-004 |
| 69 | REG-SCH-001 | Zamanlama oluşturma | TC-SCH-001 |
| 70 | REG-SCH-002 | Zamanlama tetikleme | TC-SCH-002 |
| 71 | REG-SCH-003 | Boş zamanlama tetikleme hatası | TC-SCH-003 |
| 72 | REG-SCH-004 | Zamanlama güncelleme | manual-test-scenarios |

### 2.8 Gereksinim ve Kapsam Regresyonu (8 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 73 | REG-REQ-001 | Gereksinim oluşturma | TC-REQ-001 |
| 74 | REG-REQ-002 | Senaryo-gereksinim bağlama | TC-REQ-002 |
| 75 | REG-REQ-003 | Kapsam matrisi sorgulama | TC-REQ-003 |
| 76 | REG-REQ-004 | Kapsam boşlukları | TC-REQ-004 |
| 77 | REG-REQ-005 | Gereksinim güncelleme | manual-test-scenarios |
| 78 | REG-REQ-006 | Gereksinim silme | manual-test-scenarios |
| 79 | REG-REQ-007 | Senaryo-gereksinim bağlantısı kaldırma | TSPM router |
| 80 | REG-REQ-008 | Kapsam yüzdesi doğrulama | TC-REQ-003 |

### 2.9 Sentetik Veri Regresyonu (6 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 81 | REG-DATA-001 | Veri seti yükleme | TC-SYN-001 |
| 82 | REG-DATA-002 | Veri analizi | TC-SYN-001 |
| 83 | REG-DATA-003 | PII tespiti | TC-SYN-003 |
| 84 | REG-DATA-004 | Sentetik veri üretimi | TC-SYN-002 |
| 85 | REG-DATA-005 | Dışa aktarma | TC-SYN-004 |
| 86 | REG-DATA-006 | TSPM test veri seti oluşturma | TC-SYN-005 |

### 2.10 API Endpoint Regresyonu (8 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 87 | REG-API-001 | Backend sağlık kontrolü | TC-INF-001 |
| 88 | REG-API-002 | Veritabanı hazırlık kontrolü | TC-INF-002 |
| 89 | REG-API-003 | Auth login API | TC-AUTH-001 |
| 90 | REG-API-004 | Auth me API | TC-AUTH-005 |
| 91 | REG-API-005 | TSPM proje API | api_tests.feature |
| 92 | REG-API-006 | TSPM senaryo API | api_tests.feature |
| 93 | REG-API-007 | Engine feature API | api_tests.feature |
| 94 | REG-API-008 | Engine run API | api_tests.feature |

### 2.11 Navigasyon ve UI Regresyonu (6 senaryo)

| # | Senaryo ID | Senaryo Adı | Kaynak |
|---|-----------|-------------|--------|
| 95 | REG-NAV-001 | Ana menü — Projeler navigasyonu | regression.feature |
| 96 | REG-NAV-002 | Proje içi — Senaryolar navigasyonu | regression.feature |
| 97 | REG-NAV-003 | Proje içi — Onaylar navigasyonu | regression.feature |
| 98 | REG-NAV-004 | Proje içi — İçe Aktarma navigasyonu | regression.feature |
| 99 | REG-UI-001 | Login sayfası form elemanları | login.feature |
| 100 | REG-UI-002 | Proje kartı görünümü | projects.feature |

### Regresyon Seti Özet

| Kategori | Senaryo Sayısı |
|----------|---------------|
| Kimlik Doğrulama | 8 |
| Proje Yönetimi | 10 |
| Senaryo Yönetimi | 20 |
| Onay İş Akışı | 10 |
| İçe Aktarma | 6 |
| Test Koşusu | 10 |
| Regresyon Seti / Zamanlama | 8 |
| Gereksinim / Kapsam | 8 |
| Sentetik Veri | 6 |
| API Endpoint | 8 |
| Navigasyon / UI | 6 |
| **Toplam** | **100** |

---

## 3. Entegrasyon Test Seti (~30 Senaryo)

**Amaç:** Servisler arası iletişim, veri tutarlılığı ve uçtan uca iş akışlarının doğrulanması.  
**Çalıştırma Zamanı:** Sprint ortası, mimari değişiklik sonrası  
**Tahmini Süre:** 15-25 dakika  
**Başarı Kriteri:** ≥ %95 geçme oranı

### 3.1 Frontend → Backend API Entegrasyonu (10 senaryo)

| # | Senaryo ID | Senaryo Adı | Endpoint |
|---|-----------|-------------|----------|
| 1 | INT-FB-001 | Login akışı: Form → JWT token | `POST /api/v1/auth/login` |
| 2 | INT-FB-002 | Proje listesi: Sayfa → API → Kart görünümü | `GET /api/v1/tspm/projects` |
| 3 | INT-FB-003 | Senaryo oluşturma: Form → API → Tablo güncelleme | `POST .../scenarios` |
| 4 | INT-FB-004 | Senaryo arama: Input → Query parameter → Filtrelenmiş sonuç | `GET .../scenarios?q=` |
| 5 | INT-FB-005 | Onay kararı: Buton → API → Durum güncelleme | `POST .../approvals/{id}/decide` |
| 6 | INT-FB-006 | İçe aktarma: Dosya yükleme → API → Durum gösterimi | `POST .../imports` |
| 7 | INT-FB-007 | Dashboard: Sayfa yükleme → API → İstatistik kartları | `GET .../dashboard` |
| 8 | INT-FB-008 | BDD üretimi: Metin → API → AI sonuç → Senaryo listesi | `POST .../generate-bdd` |
| 9 | INT-FB-009 | Toplu silme: Checkbox seçim → API → Tablo güncelleme | `POST .../bulk-delete` |
| 10 | INT-FB-010 | Token expire: Geçersiz token → 401 → Login yönlendirme | `GET .../me` |

### 3.2 Frontend → Engine API Entegrasyonu (6 senaryo)

| # | Senaryo ID | Senaryo Adı | Endpoint |
|---|-----------|-------------|----------|
| 11 | INT-FE-001 | Feature listesi: Sayfa → Engine API → Liste | `GET /api/features/` |
| 12 | INT-FE-002 | Test koşusu: Başlat → SSE stream → İlerleme | `POST /api/run/` |
| 13 | INT-FE-003 | AI test üretimi: URL → Engine AI → Gherkin | `POST /api/generate-feature/` |
| 14 | INT-FE-004 | Görsel regresyon: Karşılaştırma → Sonuç | `POST /api/visual/compare` |
| 15 | INT-FE-005 | Erişilebilirlik: URL → Tarama → Rapor | `POST /api/a11y/scan` |
| 16 | INT-FE-006 | Test kaydedici: Başlat → Aksiyonlar → Kod üretimi | `POST /api/recorder/start` |

### 3.3 Backend → Engine Proxy Entegrasyonu (5 senaryo)

| # | Senaryo ID | Senaryo Adı | Endpoint |
|---|-----------|-------------|----------|
| 17 | INT-BE-001 | Proxy üzerinden feature listesi | `GET /api/v1/automation/proxy/features` |
| 18 | INT-BE-002 | Proxy üzerinden test koşusu | `POST /api/v1/automation/proxy/run` |
| 19 | INT-BE-003 | Proxy üzerinden regresyon seti | `GET /api/v1/automation/proxy/regression-sets` |
| 20 | INT-BE-004 | Proxy timeout yönetimi | Timeout senaryosu |
| 21 | INT-BE-005 | Engine kapalıyken proxy hata yönetimi | Connection refused |

### 3.4 Backend → Veritabanı Entegrasyonu (4 senaryo)

| # | Senaryo ID | Senaryo Adı | Alan |
|---|-----------|-------------|------|
| 22 | INT-BD-001 | Senaryo CRUD tutarlılığı | Create → Read → Update → Delete |
| 23 | INT-BD-002 | Versiyon kayıt doğrulama | Update → Version record oluşturuldu |
| 24 | INT-BD-003 | Cascade delete doğrulama | Proje sil → İlişkili kayıtlar |
| 25 | INT-BD-004 | Eşzamanlı güncelleme | Concurrent PUT → Versiyon tutarlılığı |

### 3.5 Backend → Redis/RQ Entegrasyonu (3 senaryo)

| # | Senaryo ID | Senaryo Adı | Alan |
|---|-----------|-------------|------|
| 26 | INT-BR-001 | İş kuyruğu oluşturma ve durum takibi | `POST /api/v1/generate` → Job |
| 27 | INT-BR-002 | İş tamamlanma callback'i | Job done → Status update |
| 28 | INT-BR-003 | Redis kapalıyken hata yönetimi | Connection refused |

### 3.6 Uçtan Uca İş Akışı Entegrasyonu (2 senaryo)

| # | Senaryo ID | Senaryo Adı | Akış |
|---|-----------|-------------|------|
| 29 | INT-E2E-001 | İçe aktarma → AI işleme → Onay → Senaryo | Import → AI → Approval → Scenario |
| 30 | INT-E2E-002 | Senaryo → Regresyon seti → Zamanlama → Koşu | Scenario → RegSet → Schedule → Execution |

---

## 4. API Test Seti (~50 Senaryo)

**Amaç:** Tüm REST endpoint'lerin doğrudan HTTP istekleriyle test edilmesi.  
**Çalıştırma Zamanı:** Sprint sonu, API değişikliği sonrası  
**Tahmini Süre:** 10-15 dakika  
**Başarı Kriteri:** ≥ %98 geçme oranı  
**Feature Dosyası:** `engine/features/BGTS/api_tests.feature`

### 4.1 Auth API (5 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 1 | API-AUTH-001 | POST | `/api/v1/auth/login` — geçerli kimlik | 200 + token |
| 2 | API-AUTH-002 | POST | `/api/v1/auth/login` — geçersiz kimlik | 401 |
| 3 | API-AUTH-003 | POST | `/api/v1/auth/login` — devre dışı hesap | 403 |
| 4 | API-AUTH-004 | GET | `/api/v1/auth/me` — geçerli token | 200 + user |
| 5 | API-AUTH-005 | GET | `/api/v1/auth/me` — geçersiz token | 401 |

### 4.2 TSPM Projects API (4 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 6 | API-PRJ-001 | GET | `/api/v1/tspm/projects` | 200 + array |
| 7 | API-PRJ-002 | POST | `/api/v1/tspm/projects` | 201 + project |
| 8 | API-PRJ-003 | GET | `/api/v1/tspm/projects/{id}/dashboard` | 200 + stats |
| 9 | API-PRJ-004 | GET | `/api/v1/tspm/projects/invalid/dashboard` | 404 |

### 4.3 TSPM Scenarios API (8 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 10 | API-SCN-001 | GET | `.../scenarios` | 200 + array |
| 11 | API-SCN-002 | GET | `.../scenarios?q=login` | 200 + filtered |
| 12 | API-SCN-003 | POST | `.../scenarios` | 201 + scenario |
| 13 | API-SCN-004 | GET | `.../scenarios/{sid}` | 200 + detail |
| 14 | API-SCN-005 | PUT | `.../scenarios/{sid}` | 200 + version++ |
| 15 | API-SCN-006 | POST | `.../scenarios/bulk-delete` | 204 |
| 16 | API-SCN-007 | POST | `.../scenarios/generate-bdd` | 200 + scenarios |
| 17 | API-SCN-008 | POST | `.../scenarios/save-bdd` | 201 + created |

### 4.4 TSPM Versions API (2 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 18 | API-VER-001 | GET | `.../scenarios/{sid}/versions` | 200 + array |
| 19 | API-VER-002 | GET | `.../scenarios/{sid}/versions/1/diff/2` | 200 + diff |

### 4.5 TSPM Approvals API (3 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 20 | API-APR-001 | GET | `.../approvals` | 200 + array |
| 21 | API-APR-002 | POST | `.../approvals/{aid}/decide` — approve | 200 |
| 22 | API-APR-003 | POST | `.../approvals/{aid}/decide` — reject | 200 |

### 4.6 TSPM Imports API (1 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 23 | API-IMP-001 | POST | `.../imports` | 201 + import |

### 4.7 TSPM Executions API (5 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 24 | API-EXC-001 | GET | `.../executions` | 200 + array |
| 25 | API-EXC-002 | POST | `.../executions` | 201 + execution |
| 26 | API-EXC-003 | GET | `.../executions/{runId}` | 200 + detail |
| 27 | API-EXC-004 | PATCH | `.../executions/{runId}/results/{resId}` | 200 |
| 28 | API-EXC-005 | POST | `.../executions/{runId}` (re-run) | 201 |

### 4.8 TSPM Regression & Schedules API (5 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 29 | API-REG-001 | POST | `.../regression-sets` | 201 |
| 30 | API-REG-002 | POST | `.../regression-sets/{setId}/add` | 200 |
| 31 | API-REG-003 | POST | `.../regression-sets/suggest` | 200 |
| 32 | API-SCH-001 | POST | `.../schedules` | 201 |
| 33 | API-SCH-002 | POST | `.../schedules/{id}/trigger` | 201 |

### 4.9 TSPM Requirements & Coverage API (4 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 34 | API-REQ-001 | POST | `.../requirements` | 201 |
| 35 | API-REQ-002 | POST | `.../scenarios/{sid}/requirements` | 201 |
| 36 | API-REQ-003 | GET | `.../coverage-matrix` | 200 + matrix |
| 37 | API-REQ-004 | GET | `.../coverage-gaps` | 200 + array |

### 4.10 TSPM Test Data & Flows API (4 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 38 | API-DAT-001 | POST | `.../test-data` | 201 |
| 39 | API-DAT-002 | POST | `.../scenarios/{sid}/bind-data` | 201 |
| 40 | API-FLW-001 | POST | `.../flows` | 201 |
| 41 | API-FLW-002 | PUT | `.../flows/{fid}/graph` | 200 |

### 4.11 TSPM API Testing API (3 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 42 | API-COL-001 | POST | `.../api-tests/collections` | 201 |
| 43 | API-COL-002 | POST | `.../api-tests/collections/{cid}/requests` | 201 |
| 44 | API-COL-003 | POST | `.../api-tests/collections/{cid}/run` | 200 + results |

### 4.12 TSPM Integrations & Members API (3 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 45 | API-INT-001 | POST | `.../integrations` | 201 |
| 46 | API-INT-002 | POST | `.../integrations/{id}/sync` | 200 |
| 47 | API-MBR-001 | POST | `.../members` | 201 |

### 4.13 Infrastructure & Health API (2 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 48 | API-INF-001 | GET | `/health` | 200 + ok |
| 49 | API-INF-002 | GET | `/ready` | 200 + ready |

### 4.14 Execution Trends API (1 senaryo)

| # | Senaryo ID | Metod | Endpoint | Beklenen |
|---|-----------|-------|----------|----------|
| 50 | API-TRD-001 | GET | `.../execution-trends?days=30` | 200 + data_points |

### API Test Seti Özet

| Endpoint Grubu | Senaryo Sayısı |
|---------------|---------------|
| Auth | 5 |
| Projects | 4 |
| Scenarios | 8 |
| Versions | 2 |
| Approvals | 3 |
| Imports | 1 |
| Executions | 5 |
| Regression / Schedules | 5 |
| Requirements / Coverage | 4 |
| Test Data / Flows | 4 |
| API Testing | 3 |
| Integrations / Members | 3 |
| Infrastructure | 2 |
| Trends | 1 |
| **Toplam** | **50** |

---

## 5. Test Seti Karşılaştırma Tablosu

| Özellik | Smoke | Regresyon | Entegrasyon | API |
|---------|-------|-----------|-------------|-----|
| Senaryo Sayısı | ~15 | ~100 | ~30 | ~50 |
| Tahmini Süre | 3-5 dk | 30-45 dk | 15-25 dk | 10-15 dk |
| Çalıştırma Sıklığı | Her deployment | Sprint sonu | Sprint ortası | Sprint sonu |
| Başarı Kriteri | %100 | ≥ %95 | ≥ %95 | ≥ %98 |
| Otomasyon Seviyesi | %100 | %90 | %80 | %100 |
| Kapsam Derinliği | Yüzeysel | Derin | Servis arası | API katmanı |
| CI/CD Entegrasyonu | Pipeline gate | Gece koşusu | Manuel tetikleme | Pipeline |
| Paralel Çalıştırma | Hayır | Evet (5 worker) | Kısmi | Evet |
| Allure Raporu | Evet | Evet | Evet | Evet |

---

## 6. Test Seti Çalıştırma Takvimi

| Gün | Saat | Test Seti | Tetikleme |
|-----|------|-----------|-----------|
| Her commit | — | Smoke | CI/CD otomatik |
| Her gün | 02:00 | Regresyon | Cron zamanlayıcı |
| Pazartesi | 09:00 | Entegrasyon | Manuel / zamanlayıcı |
| Perşembe | 09:00 | API | Manuel / zamanlayıcı |
| Sprint sonu | — | Tümü | Manuel tetikleme |
| Release öncesi | — | Tümü + Performans | Manuel tetikleme |
