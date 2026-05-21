# BGTS Test Dönüşüm — Test Analiz Dokümanı

**Hazırlayan:** QA Analiz Ekibi  
**Tarih:** 2026-04-03  
**Versiyon:** 1.0  
**Durum:** Taslak

---

## 1. Test Kapsamı ve Hedefleri

### 1.1 Proje Özeti

BGTS Test Dönüşüm, bankacılık sektörüne yönelik bir **test yönetim ve otomasyon platformudur**. Platform üç ana servisten oluşur:

| Servis | Teknoloji | Port | Sorumluluk |
|--------|-----------|------|------------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind | 3000 | Kullanıcı arayüzü, senaryo yönetimi, dashboard |
| Backend | FastAPI, SQLAlchemy 2, PostgreSQL, Redis/RQ | 8000 | İş mantığı, veri yönetimi, TSPM, kimlik doğrulama |
| Engine | Flask, Playwright, pytest-bdd, Allure | 5001 | Test otomasyonu, AI destekli test üretimi, raporlama |

### 1.2 Test Hedefleri

1. **Fonksiyonel doğruluk:** Tüm CRUD operasyonlarının, iş kurallarının ve kullanıcı akışlarının doğru çalıştığını garanti etmek
2. **Güvenlik:** JWT tabanlı kimlik doğrulama, yetkilendirme ve veri koruma mekanizmalarının sağlamlığını doğrulamak
3. **Entegrasyon bütünlüğü:** Frontend ↔ Backend ↔ Engine servis iletişiminin tutarlılığını test etmek
4. **Performans:** Yoğun kullanım senaryolarında sistem davranışını ölçmek (bankacılık SLA gereksinimleri)
5. **Regresyon koruma:** Yeni geliştirmelerin mevcut işlevselliği bozmadığını sürekli doğrulamak
6. **Erişilebilirlik:** WCAG 2.1 AA standartlarına uyumluluğu sağlamak
7. **Veri bütünlüğü:** PostgreSQL veri tutarlılığı, migration güvenliği ve audit trail doğruluğu

### 1.3 Kapsam Dışı

- Üçüncü taraf servislerin (OpenAI, Anthropic) dahili işleyişi
- n8n workflow engine'in dahili testleri
- MinIO object storage performans testleri
- Ağ altyapısı ve DNS testleri

---

## 2. Test Türleri

### 2.1 Fonksiyonel Testler

| Alan | Kapsam | Tahmini Senaryo |
|------|--------|-----------------|
| Kimlik doğrulama | Login, logout, JWT yaşam döngüsü, parola doğrulama | 12 |
| Proje yönetimi | CRUD, listeleme, dashboard, üye yönetimi | 18 |
| Senaryo yönetimi | CRUD, arama, filtre, versiyon, bulk işlemler, BDD üretimi | 25 |
| Onay iş akışı | Kuyruk, onay/red kararı, split view | 10 |
| İçe aktarma | Dosya yükleme, ayrıştırma, AI işleme, durum takibi | 8 |
| Regresyon setleri | CRUD, senaryo ekleme, AI önerisi, zamanlama | 15 |
| Test koşusu | Koşu oluşturma, sonuç güncelleme, re-run, trendler | 12 |
| API test koleksiyonları | Koleksiyon CRUD, istek CRUD, koşu, sonuç analizi | 14 |
| Gereksinimler | CRUD, senaryo bağlama, kapsam matrisi, boşluk analizi | 10 |
| Test verisi | Veri seti CRUD, senaryo bağlama, genişletilmiş senaryo | 8 |
| Akışlar | Flow CRUD, graf güncelleme | 6 |
| Zamanlamalar | CRUD, tetikleme, cron ayarları | 8 |
| Entegrasyonlar | CRUD, senkronizasyon | 6 |
| Engine: Feature dosyaları | CRUD, Gherkin yönetimi | 8 |
| Engine: Test çalıştırma | SSE stream, paralel çalıştırma, raporlama | 10 |
| Engine: AI üretimi | Test üretimi, aksiyon çalıştırma | 6 |
| Engine: Görsel regresyon | Ekran görüntüsü karşılaştırma, SSIM | 5 |
| Engine: Erişilebilirlik | WCAG tarama, rapor | 4 |
| Engine: Recorder | Test kaydı, kod üretimi | 5 |
| Engine: Veri simülasyonu | Simülasyon senaryoları | 4 |
| **Toplam** | | **~194** |

### 2.2 Regresyon Testleri

Regresyon test seti, her sprint sonrasında çalıştırılacak kritik iş akışlarını kapsar:

- **Tam regresyon:** ~100 senaryo, sprint sonu ve release öncesi
- **Kısmi regresyon:** ~40 senaryo, değişiklikten etkilenen modüller
- **Gece koşusu:** Tam regresyon, zamanlayıcı ile otomatik

### 2.3 Smoke Testler

Her deployment sonrası çalışacak minimum doğrulama seti (~15 senaryo):

1. Servis sağlık kontrolleri (`/health`, `/ready`)
2. Login başarılı
3. Proje listeleme
4. Senaryo oluşturma
5. Onay kuyruğu görüntüleme
6. Import oluşturma
7. Dashboard istatistikleri
8. Engine API erişimi
9. Feature dosyası listeleme
10. Test koşusu oluşturma
11. API koleksiyonu oluşturma
12. Regresyon seti listeleme
13. Zamanlama listeleme
14. Bildirim listesi
15. Logout (token invalidation)

### 2.4 Entegrasyon Testleri

Servisler arası iletişim ve veri tutarlılığı testleri (~30 senaryo):

| Entegrasyon Noktası | Test Sayısı |
|---------------------|-------------|
| Frontend → Backend API (`/api/v1/*`) | 10 |
| Frontend → Engine API (`/api/*`) | 6 |
| Backend → Engine proxy (`/api/v1/automation/proxy/*`) | 5 |
| Backend → PostgreSQL (CRUD tutarlılığı) | 4 |
| Backend → Redis/RQ (iş kuyruğu) | 3 |
| Engine → AI servisleri (OpenAI/Anthropic) | 2 |

### 2.5 API Testleri

Tüm REST endpoint'lerin doğrudan test edilmesi (~50 senaryo):

| Endpoint Grubu | Metod Dağılımı | Test Sayısı |
|----------------|----------------|-------------|
| `/api/v1/auth/*` | POST, GET | 5 |
| `/api/v1/tspm/projects*` | GET, POST | 4 |
| `/api/v1/tspm/projects/{id}/scenarios*` | GET, POST, PUT, DELETE | 8 |
| `/api/v1/tspm/projects/{id}/approvals*` | GET, POST | 4 |
| `/api/v1/tspm/projects/{id}/imports*` | POST | 2 |
| `/api/v1/tspm/projects/{id}/executions*` | GET, POST, PATCH | 5 |
| `/api/v1/tspm/projects/{id}/regression-sets*` | GET, POST | 4 |
| `/api/v1/tspm/projects/{id}/requirements*` | GET, POST, PUT, DELETE | 5 |
| `/api/v1/tspm/projects/{id}/flows*` | GET, POST, PUT | 3 |
| `/api/v1/tspm/projects/{id}/schedules*` | GET, POST, PUT, DELETE | 4 |
| `/api/v1/tspm/projects/{id}/test-data*` | GET, POST, PUT, DELETE | 4 |
| `/api/v1/tspm/projects/{id}/api-tests*` | GET, POST, PUT, DELETE | 6 |
| `/api/v1/tspm/projects/{id}/members*` | GET, POST, DELETE | 3 |
| `/api/v1/tspm/projects/{id}/integrations*` | GET, POST, PUT, DELETE | 4 |
| `/health`, `/ready` | GET | 2 |

### 2.6 UI Testleri (E2E)

Playwright ile uçtan uca kullanıcı arayüzü testleri:

| Sayfa | Test Sayısı |
|-------|-------------|
| `/login` — Form validasyonu, başarılı/başarısız giriş | 5 |
| `/projects` — Kart görünümü, listeleme, oluşturma | 6 |
| `/p/[projectId]` — Dashboard, metrik kartları, navigasyon | 4 |
| `/p/[projectId]/scenarios` — Tablo, arama, filtre, bulk | 8 |
| `/p/[projectId]/scenarios/new` — Form, önizleme, kaydetme | 4 |
| `/p/[projectId]/approvals` — Split view, onay/red | 5 |
| `/p/[projectId]/import` — Dosya yükleme, durum | 4 |
| **Toplam** | **~36** |

### 2.7 Performans Testleri

| Senaryo | Hedef | Metrik |
|---------|-------|--------|
| Eşzamanlı kullanıcı girişi | 100 kullanıcı / 30 sn | Ortalama yanıt < 2sn |
| Senaryo listeleme (1000+ kayıt) | Sayfalama performansı | P95 < 500ms |
| Bulk senaryo silme (100 kayıt) | Toplu işlem süresi | < 5sn |
| Dashboard istatistik sorgulama | Karmaşık SQL performansı | < 1sn |
| Dosya içe aktarma (10MB) | Upload + parse süresi | < 30sn |
| API koleksiyonu çalıştırma (50 istek) | Ardışık HTTP çağrıları | < 60sn |
| SSE test stream (50 eşzamanlı) | Gerçek zamanlı iletişim | Bağlantı kaybı < %1 |

---

## 3. Modül Bazlı Risk Analizi

### 3.1 Risk Matrisi

| Modül | Etki (1-5) | Olasılık (1-5) | Risk Skoru | Risk Seviyesi |
|-------|-----------|----------------|------------|---------------|
| Kimlik doğrulama (Auth) | 5 | 3 | 15 | **Kritik** |
| Senaryo yönetimi (TSPM Scenarios) | 5 | 3 | 15 | **Kritik** |
| Onay iş akışı (Approvals) | 5 | 2 | 10 | **Yüksek** |
| İçe aktarma (Import + AI) | 4 | 4 | 16 | **Kritik** |
| Test koşusu (Executions) | 4 | 3 | 12 | **Yüksek** |
| Proje yönetimi (Projects) | 4 | 2 | 8 | **Orta** |
| Regresyon setleri | 3 | 2 | 6 | **Orta** |
| API test koleksiyonları | 3 | 3 | 9 | **Yüksek** |
| Gereksinim-senaryo bağlama | 4 | 2 | 8 | **Orta** |
| Zamanlamalar (Schedules) | 3 | 3 | 9 | **Yüksek** |
| Engine: Test çalıştırma | 5 | 3 | 15 | **Kritik** |
| Engine: AI test üretimi | 4 | 4 | 16 | **Kritik** |
| Engine: Görsel regresyon | 3 | 3 | 9 | **Yüksek** |
| Engine: Erişilebilirlik | 2 | 2 | 4 | **Düşük** |
| Engine: Recorder | 3 | 3 | 9 | **Yüksek** |
| Veri simülasyonu | 3 | 2 | 6 | **Orta** |
| Akış editörü (Flows) | 3 | 2 | 6 | **Orta** |
| Test verisi (Data Sets) | 3 | 2 | 6 | **Orta** |
| Entegrasyonlar | 3 | 3 | 9 | **Yüksek** |
| Bildirimler | 2 | 2 | 4 | **Düşük** |

### 3.2 Risk Detayları

#### Kritik Riskler (Skor ≥ 15)

**R-01: Kimlik doğrulama zafiyeti**
- **Açıklama:** JWT token sızıntısı, yetkisiz erişim, session hijacking
- **Etki:** Tüm kullanıcı verilerine yetkisiz erişim, bankacılık regülasyonu ihlali
- **Önlem:** Token süre kontrolü, HTTPS zorunluluğu, rate limiting, brute-force koruması
- **Test stratejisi:** Negatif testler, boundary testleri, güvenlik tarama araçları

**R-02: AI tarafından üretilen senaryolarda veri kaybı**
- **Açıklama:** Import → AI analiz → onay zincirinde veri kaybı veya bozulma
- **Etki:** Yanlış test senaryoları bankacılık uygulamasında hatalı test kapsamına yol açar
- **Önlem:** Her adımda veri doğrulama, audit trail, rollback mekanizması
- **Test stratejisi:** Uçtan uca akış testleri, veri tutarlılığı kontrolleri

**R-03: Engine test çalıştırma hatası**
- **Açıklama:** Playwright test koşusunun beklenmeyen durumda başarısız olması
- **Etki:** Yanlış test sonuçları, raporlama hataları
- **Önlem:** Retry mekanizması, timeout yönetimi, izole test ortamı
- **Test stratejisi:** Paralel çalıştırma testleri, hata durumu simülasyonları

**R-04: Senaryo versiyonlama hatası**
- **Açıklama:** Eşzamanlı düzenleme, versiyon çakışması, veri kaybı
- **Etki:** Onaylanmış senaryoların üzerine yazılması
- **Önlem:** Optimistic locking, versiyon numarası kontrolü
- **Test stratejisi:** Concurrent update testleri, version diff doğrulaması

#### Yüksek Riskler (Skor 9-14)

**R-05: Onay iş akışı tutarsızlığı**
- **Açıklama:** Onay durumunun senaryo durumu ile uyumsuz kalması
- **Test stratejisi:** Durum geçiş testleri, kenar durum senaryoları

**R-06: API koleksiyonu çalıştırma hatası**
- **Açıklama:** Harici API çağrılarında timeout, connection hataları
- **Test stratejisi:** Mock servislerle hata simülasyonu, timeout testleri

**R-07: Zamanlama tetikleme hatası**
- **Açıklama:** Cron ifadesi yanlış yorumlanması, koşunun tetiklenmemesi
- **Test stratejisi:** Cron parser doğrulama, manual trigger testleri

---

## 4. Öncelik Matrisi (P0-P3)

### 4.1 P0 — Kritik (Blokçu)

Sistem kullanılabilirliğini doğrudan etkileyen, deployment öncesi mutlaka geçmesi gereken testler.

| ID | Senaryo | Modül | Risk |
|----|---------|-------|------|
| P0-001 | Başarılı kullanıcı girişi | Auth | R-01 |
| P0-002 | Geçersiz parola ile giriş reddi | Auth | R-01 |
| P0-003 | JWT token doğrulama | Auth | R-01 |
| P0-004 | Devre dışı hesap erişim engeli | Auth | R-01 |
| P0-005 | Proje oluşturma | TSPM Projects | R-04 |
| P0-006 | Senaryo oluşturma | TSPM Scenarios | R-02 |
| P0-007 | Senaryo güncelleme + versiyon | TSPM Scenarios | R-04 |
| P0-008 | Onay kararı (approve/reject) | Approvals | R-05 |
| P0-009 | İçe aktarma oluşturma | Import | R-02 |
| P0-010 | BDD senaryo üretimi | AI/BDD | R-02 |
| P0-011 | Test koşusu oluşturma | Executions | R-03 |
| P0-012 | Sonuç durumu güncelleme | Executions | R-03 |
| P0-013 | Servis sağlık kontrolü | Infrastructure | — |
| P0-014 | Veritabanı bağlantı kontrolü | Infrastructure | — |
| P0-015 | Kullanıcı bilgisi sorgulama (/me) | Auth | R-01 |

### 4.2 P1 — Yüksek

Temel iş akışlarını etkileyen, sprint kapanışı öncesi geçmesi gereken testler.

| ID | Senaryo | Modül |
|----|---------|-------|
| P1-001 | Proje listesi sorgulama | Projects |
| P1-002 | Dashboard istatistikleri | Dashboard |
| P1-003 | Senaryo listeleme ve arama | Scenarios |
| P1-004 | Senaryo toplu silme | Scenarios |
| P1-005 | BDD senaryoları kaydetme | AI/BDD |
| P1-006 | Onay listesi sorgulama | Approvals |
| P1-007 | Senaryo versiyon geçmişi | Versions |
| P1-008 | Versiyon karşılaştırma (diff) | Versions |
| P1-009 | Regresyon seti oluşturma | Regression |
| P1-010 | Regresyon setine senaryo ekleme | Regression |
| P1-011 | Koşu detayı sorgulama | Executions |
| P1-012 | Koşu yeniden çalıştırma (re-run) | Executions |
| P1-013 | Zamanlama oluşturma | Schedules |
| P1-014 | Zamanlama tetikleme | Schedules |
| P1-015 | Gereksinim oluşturma | Requirements |
| P1-016 | Senaryo-gereksinim bağlama | Requirements |
| P1-017 | Kapsam matrisi sorgulama | Coverage |
| P1-018 | API koleksiyonu oluşturma | API Tests |
| P1-019 | API isteği oluşturma | API Tests |
| P1-020 | API koleksiyonu çalıştırma | API Tests |
| P1-021 | Test verisi oluşturma | Test Data |
| P1-022 | Senaryo-veri bağlama | Test Data |
| P1-023 | Proje üyesi ekleme | Members |
| P1-024 | Engine: Feature dosyası CRUD | Engine Features |
| P1-025 | Engine: Test koşusu başlatma | Engine Runner |

### 4.3 P2 — Orta

İş süreçlerini zenginleştiren, release öncesi tamamlanması beklenen testler.

| ID | Senaryo | Modül |
|----|---------|-------|
| P2-001 | Koşu trendleri sorgulama | Execution Trends |
| P2-002 | Koşu istatistikleri | Execution Stats |
| P2-003 | Flaky test tespiti | Flaky Tests |
| P2-004 | Kapsam boşlukları sorgulama | Coverage Gaps |
| P2-005 | Gereksinim güncelleme | Requirements |
| P2-006 | Gereksinim silme | Requirements |
| P2-007 | Akış oluşturma | Flows |
| P2-008 | Akış graf güncelleme | Flows |
| P2-009 | Zamanlama güncelleme | Schedules |
| P2-010 | Zamanlama silme | Schedules |
| P2-011 | Test verisi güncelleme | Test Data |
| P2-012 | Test verisi silme | Test Data |
| P2-013 | Genişletilmiş senaryo görüntüleme | Expanded Scenario |
| P2-014 | AI regresyon set önerisi | AI Suggest |
| P2-015 | Önerilen setleri kabul etme | AI Suggest |
| P2-016 | Entegrasyon oluşturma | Integrations |
| P2-017 | Entegrasyon senkronizasyonu | Integrations |
| P2-018 | API isteği güncelleme/silme | API Tests |
| P2-019 | API test koşusu geçmişi | API Tests |
| P2-020 | Engine: Görsel regresyon testi | Engine Visual |
| P2-021 | Engine: Erişilebilirlik tarama | Engine A11y |
| P2-022 | Engine: Test kaydedici | Engine Recorder |
| P2-023 | Engine: AI test üretimi | Engine AI |
| P2-024 | Engine: Veri simülasyonu | Engine DataSim |
| P2-025 | Bildirim listeleme | Notifications |

### 4.4 P3 — Düşük

Ek özellikler, kozmetik iyileştirmeler, release sonrası tamamlanabilecek testler.

| ID | Senaryo | Modül |
|----|---------|-------|
| P3-001 | Entegrasyon güncelleme | Integrations |
| P3-002 | Entegrasyon silme | Integrations |
| P3-003 | Proje üyesi çıkarma | Members |
| P3-004 | API koleksiyonu silme | API Tests |
| P3-005 | Akış detay sorgulama | Flows |
| P3-006 | Regresyon seti detayı | Regression |
| P3-007 | Dark/light tema geçişi | UI |
| P3-008 | Responsive tasarım testleri | UI |
| P3-009 | Tarayıcı uyumluluk testleri | Cross-Browser |
| P3-010 | Performans testleri (yük) | Performance |

---

## 5. Test Ortamı Gereksinimleri

### 5.1 Ortam Matrisi

| Ortam | Kullanım | Servisler |
|-------|----------|-----------|
| Geliştirme (DEV) | Günlük geliştirme ve birim testler | Tümü, yerel |
| Test (QA) | Fonksiyonel, entegrasyon, regresyon | Tümü, Docker Compose |
| Staging (STG) | Kabul testleri, performans | Tümü, prod-benzeri |
| Üretim (PROD) | Smoke testler, izleme | Sınırlı erişim |

### 5.2 Test Verisi

- **Seed data:** 5 proje, 200 senaryo, 50 onay, 10 koşu
- **Performans verisi:** 50 proje, 10.000 senaryo, 1.000 koşu
- **PII maskeleme:** Bankacılık verisi kullanılmayacak, sentetik veri üretilecek

### 5.3 Araçlar

| Araç | Kullanım |
|------|----------|
| pytest + pytest-bdd | Backend ve Engine birim/BDD testleri |
| Playwright | E2E ve UI testleri |
| Allure | Test raporlama |
| httpx / requests | API testleri |
| Locust / k6 | Performans testleri |
| Docker Compose | Ortam yönetimi |
| GitHub Actions | CI/CD entegrasyonu |

---

## 6. Test Takvimi ve Çıkış Kriterleri

### 6.1 Sprint İçi Test Takvimi

| Gün | Aktivite |
|-----|----------|
| Her commit | Smoke test (CI/CD) |
| Günlük | Birim testleri, etkilenen modül regresyonu |
| Sprint ortası | Entegrasyon testleri |
| Sprint sonu | Tam regresyon, performans testi |
| Release öncesi | Kabul testleri, güvenlik taraması |

### 6.2 Çıkış Kriterleri

| Kriter | Eşik |
|--------|------|
| P0 testleri geçme oranı | %100 |
| P1 testleri geçme oranı | %100 |
| P2 testleri geçme oranı | ≥ %95 |
| Genel test geçme oranı | ≥ %95 |
| Açık kritik hata | 0 |
| Açık yüksek hata | ≤ 2 |
| Kod kapsamı (backend) | ≥ %80 |
| API yanıt süresi (P95) | < 2 saniye |
| UI yanıt süresi (P95) | < 3 saniye |
