# BGTS Test Dönüşüm — İleri Seviye Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** Concurrency, Race Condition, Negative E2E Journeys, Accessibility, Browser Compatibility, Data Integrity

---

## TS-ADV-01: Concurrency / Race Condition Testleri

### Eşzamanlılık Riskleri

| ID | Başlık | Senaryo | Öncelik | Beklenen |
|----|--------|---------|---------|----------|
| CONC-01 | Aynı anda 2 kullanıcı aynı senaryoyu günceller | User-A ve User-B aynı senaryo ID'sine paralel PUT gönderir | Critical | Son yazan kazanır (last-write-wins); versiyon sayısı doğru artmalı; veri kaybı olmamalı |
| CONC-02 | Paralel toplu silme istekleri | Aynı senaryo ID listesi ile eşzamanlı 2 bulk-delete | High | İlk başarılı, ikinci yok sayılır; 500 hatası olmamalı |
| CONC-03 | Koşu oluşturma sırasında senaryo silme | Koşu oluşturuluyor, aynı anda senaryo siliniyor | High | Koşu oluşur ama silinen senaryo için result kaydı "orphan" olmamalı veya graceful handle edilmeli |
| CONC-04 | Paralel onay kararı | Aynı approval_id'ye eşzamanlı "approved" ve "rejected" | Critical | İlk gelen karar geçerli; ikinci istek zaten karar verilmiş onayı değiştirmemeli |
| CONC-05 | Eşzamanlı proje oluşturma (aynı isimle) | 2 istek aynı proje adı ile paralel POST | Medium | Her ikisi de başarılı (unique constraint yoksa); veya biri reddedilir |
| CONC-06 | Regresyon setine paralel senaryo ekleme | İki istek aynı sete farklı senaryo ID'leri ekler | High | Her iki senaryo grubu da sete eklenmeli; veri kaybı olmamalı |
| CONC-07 | Eşzamanlı coverage matrix hesaplama | 10 paralel istek coverage-matrix endpoint'ine | Medium | Hepsi doğru sonuç döner; race condition yok |
| CONC-08 | DB connection pool tükenmesi | 50+ paralel DB-intensive istek | High | Connection pool queue bekletmeli; timeout verip 503 dönebilir; crash olmamalı |

### Test Yaklaşımı

```
1. Python asyncio + httpx ile paralel istek gönderimi
2. k6 ile eşzamanlı senaryoları yük testi formatında çalıştırma
3. PostgreSQL advisory lock kontrolü ile deadlock tespiti
4. Sonuç doğrulama: DB state'in tutarlı olduğunu SQL ile kontrol et
```

---

## TS-ADV-02: Negative E2E User Journeys (Hata Akışları)

### Uçtan Uca Negatif Kullanıcı Yolculukları

| ID | Başlık | Yolculuk | Beklenen |
|----|--------|----------|----------|
| NEG-01 | Token süresi dolan kullanıcı | Login → Proje oluştur → 30dk bekle → Senaryo oluştur (expired token) | UI "Oturum süresi doldu" mesajı gösterir; login'e yönlendirir |
| NEG-02 | Silinen projeye erişim | Proje oluştur → URL kaydet → Proje sil → URL'den erişim dene | 404 sayfası; "Proje bulunamadı" mesajı |
| NEG-03 | Ağ kesintisi sırasında kaydetme | Senaryo formunu doldur → Ağı kes → Kaydet | UI hata mesajı; veri kaybolmaz (form state korunur) |
| NEG-04 | Backend kapalıyken frontend | Backend'i durdur → Frontend sayfalarını gezin | API hatası toast mesajı; UI çökmez; retry önerisi |
| NEG-05 | Aynı anda farklı tarayıcılarda login | Chrome'da login → Firefox'ta login → Chrome'da işlem yap | Her iki oturum da çalışmalı (stateless JWT) |
| NEG-06 | Geçersiz UUID ile URL navigasyonu | `/p/not-a-uuid/scenarios` sayfasını ziyaret et | 404 sayfası veya "Proje bulunamadı" |
| NEG-07 | Çok uzun metin yapıştırma | BDD üretim alanına 100.000+ karakter yapıştır → Üret | Graceful timeout veya karakter limiti uyarısı |
| NEG-08 | Tarayıcı geri tuşu ile form kaybı | Senaryo formu doldur → Tarayıcı geri → İleri | Form state mümkünse korunmalı veya uyarı verilmeli |
| NEG-09 | Çift tıklama ile duplicate oluşturma | "Kaydet" butonuna hızlıca 2 kez tıkla | Tek kayıt oluşmalı; buton disable olmalı |
| NEG-10 | Onaylanan senaryoyu tekrar silme | Onay kuyruğundan senaryo onayla → Senaryoyu sil → Koşu oluştur | Silinen senaryo ID'si koşuya eklenemez veya uyarı verilir |

---

## TS-ADV-03: Erişilebilirlik (Accessibility / a11y) Testleri

### WCAG 2.1 AA Uyumluluk Kontrolleri

| ID | Başlık | Kontrol | Sayfa | Öncelik |
|----|--------|---------|-------|---------|
| A11Y-01 | Klavye navigasyonu — Tab sırası | Tab ile tüm interaktif elementlere ulaşılabilmeli | Tüm sayfalar | Critical |
| A11Y-02 | Klavye navigasyonu — Enter/Space aktivasyon | Butonlar Enter/Space ile tıklanabilmeli | Tüm sayfalar | Critical |
| A11Y-03 | Focus göstergesi (outline) | Tab ile gezinirken focus ring görünmeli | Tüm sayfalar | High |
| A11Y-04 | aria-label doğruluğu | Tüm iconluk butonlarda aria-label mevcut | Sidebar, Header | High |
| A11Y-05 | Form label eşleştirmesi | Tüm input'lar `<label>` ile eşleştirilmiş olmalı (`htmlFor`/`id`) | Login, Senaryo form | Critical |
| A11Y-06 | Renk kontrastı (4.5:1 minimum) | Metin/arka plan kontrast oranı yeterli | Tüm sayfalar | High |
| A11Y-07 | Dark mode kontrast | Dark temada da kontrast oranı yeterli | Tüm sayfalar | Medium |
| A11Y-08 | Hata mesajları screen reader uyumlu | Hata mesajları `role="alert"` veya `aria-live="polite"` ile | Login, Formlar | High |
| A11Y-09 | Heading hiyerarşisi | h1 → h2 → h3 sıralaması doğru | Tüm sayfalar | Medium |
| A11Y-10 | img/svg alt text | Tüm görsellerde alt veya aria-label mevcut | Logo, ikonlar | Medium |
| A11Y-11 | Zoom 200% kullanılabilirlik | Sayfa %200 zoom'da düzgün görünmeli | Tüm sayfalar | Medium |
| A11Y-12 | Reduced motion | `prefers-reduced-motion` media query desteği | Animasyonlar | Low |
| A11Y-13 | Autocomplete nitelikleri | Login formunda `autocomplete="email"` ve `autocomplete="current-password"` | Login | High |
| A11Y-14 | Skip to content link | Sayfa başında "İçeriğe geç" linki | Tüm sayfalar | Medium |

### Mevcut Erişilebilirlik Durumu (Analiz)

| Element | Durum | Kaynak |
|---------|-------|--------|
| Login — email input `autocomplete="email"` | ✅ Mevcut | `login/page.tsx:68` |
| Login — password `autocomplete="current-password"` | ✅ Mevcut | `login/page.tsx:80` |
| Login — SVG `aria-label="BGTEST"` | ✅ Mevcut | BgtestLogo component |
| Sidebar — `data-testid` mevcut | ✅ Mevcut | `AppShell.tsx:59` |
| Header — user menu `aria-label="Kullanıcı menüsü"` | ✅ Mevcut | `AppShell.tsx:99` |
| Senaryo checkbox — `aria-label` | ✅ Mevcut | `generate/page.tsx:246` |
| Hata mesajları — `role="alert"` | ❌ EKSİK | Hata mesajlarına role eklenmeli |
| Skip to content | ❌ EKSİK | Ana layout'a eklenmeli |
| Focus ring görünürlüğü | ⚠️ Kısmi | Tailwind `focus:ring` bazı yerlerde var |

---

## TS-ADV-04: Browser / Device Uyumluluk Matrisi

### Hedef Tarayıcılar

| Tarayıcı | Versiyon | Platform | Öncelik | Durum |
|----------|---------|----------|---------|-------|
| Chrome | 120+ | Windows/Mac/Linux | P0 | Ana geliştirme |
| Firefox | 115+ | Windows/Mac | P1 | Test edilmeli |
| Safari | 17+ | Mac/iOS | P1 | Test edilmeli |
| Edge | 120+ | Windows | P2 | Chromium tabanlı |
| Chrome Mobile | Latest | Android | P2 | Responsive test |
| Safari Mobile | Latest | iOS | P2 | Responsive test |

### Viewport Kırılma Noktaları

| Breakpoint | Genişlik | Cihaz Tipi | Test Edilecek Sayfalar |
|-----------|----------|------------|----------------------|
| Mobile S | 320px | Eski telefon | Login, Proje listesi |
| Mobile M | 375px | iPhone SE | Tüm sayfalar |
| Mobile L | 425px | iPhone 12 | Tüm sayfalar |
| Tablet | 768px | iPad | Tüm sayfalar |
| Laptop | 1024px | Laptop | Tüm sayfalar |
| Desktop | 1440px | Desktop | Tüm sayfalar (ana) |
| 4K | 2560px | Geniş ekran | Layout bozulmaması |

### Her Viewport İçin Kontroller

| # | Kontrol |
|---|---------|
| 1 | Sidebar: mobilde gizli/hamburger, tablet'te collapsed, desktop'ta full |
| 2 | Form layoutları: tek kolon (mobil) → iki kolon (desktop) |
| 3 | Tablo: yatay scroll veya responsive card görünümü |
| 4 | Butonlar: dokunma hedefi minimum 44x44px (mobil) |
| 5 | Metin: kesilme (truncation) düzgün çalışıyor |
| 6 | Modal/Dialog: mobilde tam ekran, desktop'ta centered |

---

## TS-ADV-05: Data Integrity / Cross-Module Veri Bütünlüğü

### Modüller Arası Veri Tutarlılığı Testleri

| ID | Başlık | Senaryo | Doğrulama |
|----|--------|---------|-----------|
| DI-01 | Senaryo silindiğinde koşu sonuçları | Senaryo sil → Koşu detayını kontrol et | Sonuç kaydı orphan olmamalı veya graceful handle |
| DI-02 | Senaryo silindiğinde gereksinim bağlantısı | Senaryo sil → Coverage matrix kontrol et | Bağlantı cascade silinmeli; coverage yeniden hesaplanmalı |
| DI-03 | Senaryo silindiğinde regresyon seti | Senaryo sil → Regresyon set detay kontrol et | Silinen ID hâlâ listede ama senaryo verisi yok (stale reference) |
| DI-04 | Proje silindiğinde tüm alt veriler | Proje sil → Tüm alt tabloları SQL ile kontrol et | Hiçbir orphan kayıt olmamalı |
| DI-05 | Koşu re-run veri bağımsızlığı | Koşu-1 re-run → Koşu-1 sonuçlarını güncelle | Koşu-2 sonuçları etkilenmemeli |
| DI-06 | Senaryo güncelleme sonrası koşu referansı | Senaryo başlığını güncelle → Eski koşu detayı | Eski koşu doğru (güncel) senaryo başlığını göstermeli |
| DI-07 | Test verisi silme sonrası binding | Test veri seti sil → Bağlı senaryonun expanded view'ı | Hata vermemeli; boş genişletme döner |
| DI-08 | Gereksinim güncelleme sonrası coverage | Gereksinim external_id güncelle → Coverage matrix | Güncel external_id gösterilmeli |
| DI-09 | Zamanlama regression set referansı | Regression set sil → Zamanlama tetikle | 400 veya boş koşu; crash olmamalı |
| DI-10 | Eşzamanlı senaryo güncelleme versiyonu | User-A v1→v2, User-B v1→v3 | Her iki versiyon da saklanmalı; version_number doğru |

### Referential Integrity SQL Kontrolleri

```sql
-- Orphan koşu sonuçları (senaryosu silinmiş)
SELECT er.id, er.scenario_id 
FROM tspm_execution_results er
LEFT JOIN tspm_scenarios s ON s.id = er.scenario_id
WHERE s.id IS NULL;

-- Orphan senaryo-gereksinim bağlantıları
SELECT sr.scenario_id, sr.requirement_id
FROM tspm_scenario_requirements sr
LEFT JOIN tspm_scenarios s ON s.id = sr.scenario_id
LEFT JOIN tspm_requirements r ON r.id = sr.requirement_id
WHERE s.id IS NULL OR r.id IS NULL;

-- Stale regression set scenario_ids
SELECT rs.id, rs.name, 
  ARRAY(
    SELECT unnest(rs.scenario_ids) 
    EXCEPT 
    SELECT id FROM tspm_scenarios WHERE project_id = rs.project_id
  ) AS stale_ids
FROM tspm_regression_sets rs
WHERE rs.scenario_ids IS NOT NULL;
```

---

## TS-ADV-06: Test Otomasyon Fizibilite Değerlendirmesi

### Otomasyon Uygunluk Matrisi

| Test Kategorisi | Toplam | Otomatize Edilebilir | Araç | Öncelik |
|-----------------|--------|---------------------|------|---------|
| API Manuel (75) | 75 | **70** (%93) | pytest + httpx | P0 |
| E2E UI (59) | 59 | **45** (%76) | Playwright | P1 |
| Güvenlik (33) | 33 | **25** (%76) | OWASP ZAP, Schemathesis | P1 |
| Performans (28) | 28 | **28** (%100) | k6, Locust | P1 |
| RBAC (180+) | 180 | **180** (%100) | pytest parametrize | P0 |
| API Contract (45) | 45 | **45** (%100) | Schemathesis, Dredd | P0 |
| Cross-cutting (42) | 42 | **35** (%83) | pytest | P1 |
| Concurrency (8) | 8 | **8** (%100) | asyncio + httpx | P2 |
| Data Integrity (10) | 10 | **10** (%100) | pytest + SQL | P1 |
| **TOPLAM** | **480** | **446** (%93) | | |

### Otomasyon Yatırım Değerlendirmesi

| Faz | Süre | Kapsam | ROI |
|-----|------|--------|-----|
| Faz 1 (2 hafta) | API + RBAC + Contract | 300 test | YÜKSEK — en çok tekrar eden testler |
| Faz 2 (3 hafta) | E2E UI + Performans | 73 test | ORTA — UI değişikliklerine duyarlı |
| Faz 3 (2 hafta) | Güvenlik + Cross-cutting | 60 test | YÜKSEK — güvenlik otomasyonu kritik |
| Faz 4 (1 hafta) | Concurrency + Data Integrity | 18 test | ORTA — spesifik senaryolar |

### Önerilen Otomasyon Mimarisi

```
tests/
├── api/                    # API testleri (pytest + httpx)
│   ├── test_auth.py
│   ├── test_projects.py
│   ├── test_scenarios.py
│   ├── test_executions.py
│   ├── test_requirements.py
│   ├── test_regression.py
│   ├── test_schedules.py
│   ├── test_test_data.py
│   ├── test_integrations.py
│   ├── test_api_tests.py
│   └── test_members.py
├── rbac/                   # RBAC matris testleri
│   └── test_rbac_matrix.py # parametrize ile 180+ test
├── security/               # Güvenlik testleri
│   ├── test_injection.py
│   ├── test_auth_security.py
│   └── test_rate_limiting.py
├── contract/               # API contract testleri
│   └── test_contracts.py
├── performance/            # k6 scriptleri
│   ├── load_test.js
│   ├── stress_test.js
│   └── spike_test.js
├── integrity/              # Veri bütünlüğü
│   └── test_data_integrity.py
├── e2e/                    # Playwright (mevcut)
│   └── *.spec.ts
├── conftest.py             # Ortak fixture'lar
└── helpers/
    ├── api_client.py       # HTTP client wrapper
    └── data_factory.py     # Test veri fabrikası
```

---

## TS-ADV-07: Sprint Bazlı Test Execution Planı

### Sprint N (Mevcut — İlk Planlama)

| Gün | Aktivite | Test Sayısı | Sorumluluk |
|-----|---------|------------|------------|
| Gün 1-2 | Smoke test + P0 regresyon | 25 + 17 = 42 | QA Lead |
| Gün 3-4 | P1 fonksiyonel testler | 16 | QA Engineer |
| Gün 5 | Güvenlik smoke (critical) | 8 | Security QA |
| Gün 6-7 | E2E UI testleri (mevcut 34) | 34 | QA Automation |
| Gün 8 | Performans baseline | 5 | Performance QA |
| Gün 9 | Bug fix doğrulama | Varies | QA Team |
| Gün 10 | Release checklist + Go/No-Go | 25 | QA Lead |

### Sprint N+1 (Otomasyon Başlangıcı)

| Gün | Aktivite |
|-----|---------|
| Gün 1-3 | API test otomasyon framework kurulumu |
| Gün 4-6 | Auth + Proje + Senaryo API testleri |
| Gün 7-8 | RBAC matris otomasyon (parametrize) |
| Gün 9-10 | CI/CD pipeline entegrasyonu |

### Sprint N+2 (Tam Otomasyon)

| Gün | Aktivite |
|-----|---------|
| Gün 1-5 | Kalan API testleri + Contract testler |
| Gün 6-8 | Güvenlik test otomasyonu |
| Gün 9-10 | k6 performans testleri |

---

## Toplam İleri Seviye Test Sayısı

| Kategori | Sayı |
|----------|------|
| Concurrency | 8 |
| Negative E2E Journeys | 10 |
| Accessibility | 14 |
| Browser Compatibility | 7 viewport × 6 kontrol = 42 |
| Data Integrity | 10 |
| **Toplam** | **84** |
