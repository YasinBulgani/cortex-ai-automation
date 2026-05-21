# BGTS Test Dönüşüm — Engine (Flask Otomasyon Motoru) Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Base URL:** `http://127.0.0.1:5001`  
**Framework:** Flask, Playwright, pytest-bdd, Allure  
**Blueprint Sayısı:** 16  

> Engine platformun test otomasyon motorudur. Gherkin feature yönetimi, test çalıştırma (pytest + Allure SSE), AI ile test üretimi, görsel regresyon, erişilebilirlik testi, test kaydedici ve veri simülasyonu gibi yeteneklere sahiptir.

---

## 1. Blueprint Endpoint Özeti

| Blueprint | Prefix | Endpoint | Kapsam |
|-----------|--------|----------|--------|
| `auth` | `/api/auth/*` | 9 | Kullanıcı yönetimi, login, register |
| `feature` | `/api/features/*` | 9 | Gherkin feature CRUD |
| `regression` | `/api/regression-sets/*` | 7 | Regresyon seti yönetimi |
| `manual` | `/api/manual-tests/*` | 16 | Manuel test senaryoları |
| `locators` | `/api/locators/*` | 6 | Object repository (XPath/CSS) |
| `runner` | `/api/run/*` | 34 | Test çalıştırma + SSE stream |
| `ai` | `/api/generate-feature/*` | 11 | AI ile test üretimi |
| `visual` | `/api/visual/*` | 28 | Görsel regresyon testleri |
| `a11y` | `/api/a11y/*` | 26 | WCAG erişilebilirlik testleri |
| `recorder` | `/api/recorder/*` | 34 | Test kaydedici |
| `datasim` | `/api/datasim/*` | 35 | Veri simülasyonu |
| `project` | `/api/projects/*` | 9 | Proje yönetimi |
| `lifecycle` | `/api/*` | 3 | Yaşam döngüsü |
| `registry` | `/api/registry/*` | 22 | Object/element registry |
| `playback` | `/api/playback/*` | 20 | Test oynatıcı |
| `utility` | `/api/*` | 18 | Yardımcı endpoint'ler |
| **TOPLAM** | | **~287** | |

---

## 2. Test Senaryoları — Kritik Blueprint'ler

### TS-ENG-01: Engine Auth Testleri

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0101 | Engine login başarılı | Pozitif | Critical | Session oluşturulur; `user_id` session'a yazılır |
| ENG-0102 | Engine login hatalı parola | Negatif | Critical | 401 Unauthorized |
| ENG-0103 | Oturum olmadan API erişimi | Negatif | Critical | 401; `{"error": "Unauthorized"}` |
| ENG-0104 | Kullanıcı kaydı (register) | Pozitif | High | Yeni kullanıcı oluşturulur |
| ENG-0105 | Public endpoint'lere oturumsuz erişim | Pozitif | Medium | Health, login sayfası erişilebilir |

### TS-ENG-02: Feature (Gherkin) Yönetimi

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0201 | Feature dosyası listeleme | Pozitif | High | Klasör ağacı (tree) formatında döner |
| ENG-0202 | Yeni feature dosyası oluşturma | Pozitif | High | `.feature` dosyası kaydedilir |
| ENG-0203 | Feature dosyası güncelleme | Pozitif | High | İçerik güncellenir |
| ENG-0204 | Feature dosyası silme | Pozitif | Medium | Dosya silinir |
| ENG-0205 | Klasör oluşturma | Pozitif | Medium | Alt klasör oluşturulur |
| ENG-0206 | Geçersiz dosya adı (path traversal) | Güvenlik | Critical | `../` içeren ad reddedilir |

### TS-ENG-03: Test Çalıştırma (Runner)

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0301 | Test çalıştırma (POST /api/run) | Pozitif | Critical | run_id döner; pytest subprocess başlar |
| ENG-0302 | SSE stream ile gerçek zamanlı çıktı | Pozitif | Critical | Server-Sent Events ile test çıktısı stream edilir |
| ENG-0303 | Belirli feature dosyası ile çalıştırma | Pozitif | High | Sadece seçilen feature çalışır |
| ENG-0304 | Marker bazlı filtreleme | Pozitif | Medium | `"not ai"` gibi marker ile filtreleme |
| ENG-0305 | Allure raporu üretimi | Pozitif | High | Allure results dizini oluşturulur |
| ENG-0306 | Eşzamanlı test koşusu | Concurrency | High | 2 paralel koşu çakışmamalı |
| ENG-0307 | Test çalıştırma sonucu kayıt | Pozitif | High | `record_test_run()` ile DB'ye kaydedilir |

### TS-ENG-04: AI ile Test Üretimi

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0401 | Gherkin feature üretimi | Pozitif | High | Gereksinimden Gherkin senaryoları üretilir |
| ENG-0402 | Gereksinim metni olmadan üretim | Negatif | High | 400; `"Gereksinim metni eksik"` |
| ENG-0403 | API analizi | Pozitif | Medium | Request/response analizi döner |
| ENG-0404 | Güvenlik taraması | Pozitif | Medium | URL üzerinde güvenlik taraması |
| ENG-0405 | Sayfa inspektörü (inspect) | Pozitif | Medium | DOM analizi başlatılır |
| ENG-0406 | AI key olmadan üretim | Exception | High | Anlaşılır hata mesajı |

### TS-ENG-05: Görsel Regresyon Testleri

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0501 | Baseline listesi | Pozitif | High | Domain bazlı baseline listesi |
| ENG-0502 | Yeni baseline oluşturma | Pozitif | High | Screenshot alınır ve kaydedilir |
| ENG-0503 | Görsel karşılaştırma (compare) | Pozitif | Critical | SSIM skoru hesaplanır; diff görseli üretilir |
| ENG-0504 | Baseline güncelleme (approve) | Pozitif | High | Mevcut ekran yeni baseline olur |
| ENG-0505 | Eşik değeri altında geçme | Pozitif | Medium | SSIM > threshold → PASS |
| ENG-0506 | Eşik değeri üstünde kalma | Negatif | Medium | SSIM < threshold → FAIL |
| ENG-0507 | Baseline silme | Pozitif | Low | Seçili baseline silinir |

### TS-ENG-06: Erişilebilirlik (a11y) Testleri

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0601 | WCAG testi çalıştırma | Pozitif | High | URL üzerinde WCAG AA testi |
| ENG-0602 | İhlal raporu | Pozitif | High | Severity, rule, element detayları |
| ENG-0603 | Test konfigürasyonu | Pozitif | Medium | WCAG level (A/AA/AAA), ignore rules |
| ENG-0604 | Batch test (çoklu URL) | Pozitif | Medium | Birden fazla URL test edilir |
| ENG-0605 | Rapor indirme | Pozitif | Medium | HTML/JSON formatında rapor |

### TS-ENG-07: Test Kaydedici (Recorder)

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0701 | Kayıt oturumu başlatma | Pozitif | Critical | session_id döner; kayıt başlar |
| ENG-0702 | Oturum adı zorunlu | Boundary | High | Ad boşsa 400 |
| ENG-0703 | Aksiyon kaydı | Pozitif | High | click, type, navigate aksiyonları kaydedilir |
| ENG-0704 | Kayıt durdurma | Pozitif | High | Kayıt sonlandırılır |
| ENG-0705 | Kod üretimi (Playwright/Cucumber/POM) | Pozitif | Critical | Kaydedilen aksiyonlardan test kodu üretilir |
| ENG-0706 | Eşzamanlı kayıt oturumları | Concurrency | Medium | Birden fazla oturum birbirini etkilemez |

### TS-ENG-08: Manuel Test Yönetimi

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0801 | Manuel test oluşturma | Pozitif | High | Test kaydedilir |
| ENG-0802 | Başlık olmadan oluşturma | Boundary | Medium | 400; `"Başlık gerekli"` |
| ENG-0803 | Test adımı ekleme | Pozitif | High | action + expected ile adım eklenir |
| ENG-0804 | Eksik adım bilgisi | Boundary | Medium | 400; `"Aksiyon ve beklenen sonuç zorunludur"` |
| ENG-0805 | Test durumu güncelleme | Pozitif | High | Status güncellenir |
| ENG-0806 | Test silme | Pozitif | Medium | Test silinir |
| ENG-0807 | Adım durumu güncelleme | Pozitif | Medium | Adım passed/failed olarak işaretlenir |

### TS-ENG-09: Veri Simülasyonu (DataSim)

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-0901 | Dataset kataloğu | Pozitif | Medium | Mevcut veri setleri listelenir |
| ENG-0902 | Dataset yükleme/preview | Pozitif | High | CSV yüklenir ve önizleme gösterilir |
| ENG-0903 | Sentetik veri üretimi | Pozitif | High | Seçilen datasetten sentetik veri üretilir |
| ENG-0904 | Streaming üretim (SSE) | Pozitif | Medium | Üretim ilerlemesi SSE ile stream edilir |
| ENG-0905 | CSV/JSON export | Pozitif | High | Üretilen veri indirilir |

### TS-ENG-10: Object Registry & Playback

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-1001 | Locator kaydı (XPath/CSS) | Pozitif | High | Element tanımı kaydedilir |
| ENG-1002 | Locator arama | Pozitif | Medium | İsim/tip ile aranır |
| ENG-1003 | Playback oturumu başlatma | Pozitif | High | Kaydedilen test oynatılır |
| ENG-1004 | Playback sonuç raporu | Pozitif | High | Adım bazında passed/failed rapor |
| ENG-1005 | Hatalı locator ile playback | Exception | Medium | Element bulunamadığında anlaşılır hata |

---

## 3. Engine Genel (Cross-Cutting) Testleri

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| ENG-CC01 | Health endpoint | Pozitif | Critical | `GET /health` → `{"status": "ok"}` |
| ENG-CC02 | CORS yapılandırması | Güvenlik | High | `supports_credentials=True` doğru çalışır |
| ENG-CC03 | Session-based auth tüm API'lerde | Güvenlik | Critical | `user_id` session'da yoksa tüm `/api/*` → 401 |
| ENG-CC04 | SQLite veritabanı init | Pozitif | High | `init_db()` tabloları oluşturur |
| ENG-CC05 | Active project session yönetimi | Pozitif | Medium | `settings.set_active_project()` doğru çalışır |
| ENG-CC06 | Static dosya servisi | Pozitif | Low | UI template ve static dosyalar erişilebilir |
| ENG-CC07 | Secret key güvenliği | Güvenlik | High | Varsayılan secret production'da değiştirilmeli |

---

## 4. Engine Toplam Test Sayısı

| Kategori | Sayı |
|----------|------|
| Auth | 5 |
| Feature (Gherkin) | 6 |
| Runner | 7 |
| AI Üretimi | 6 |
| Görsel Regresyon | 7 |
| Erişilebilirlik | 5 |
| Recorder | 6 |
| Manuel Test | 7 |
| Veri Simülasyonu | 5 |
| Object Registry & Playback | 5 |
| Cross-Cutting | 7 |
| **Toplam** | **66** |

---

## TÜM PLATFORM — BÜYÜK NİHAİ TOPLAM

| Bileşen | Test Sayısı |
|---------|------------|
| Backend TSPM (Ana) | 75 |
| Backend Sentetik Veri | 38 |
| Backend Engine Proxy & Notifications | 25 |
| Engine (Flask) | 66 |
| E2E UI | 59 |
| Güvenlik | 33 |
| Performans | 28 |
| RBAC Matrisi | 180+ |
| API Contract | 45+ |
| Cross-Cutting | 42 |
| İleri Seviye | 84 |
| Uzmanlaşmış | 49 |
| n8n + AI Chat | 24 |
| Smoke / Release | 30 |
| **PLATFORM TOPLAM** | **778+** |
