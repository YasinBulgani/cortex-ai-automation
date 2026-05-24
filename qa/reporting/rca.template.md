# BGTS Root-Cause Analysis (Kök Neden Analizi) Rapor Yapısı

## 1. Başarısız Test Sınıflandırma Taksonomisi

Her başarısız test aşağıdaki kategorilerden birine atanır:

```
ROOT CAUSE KATEGORİLERİ
│
├── PRODUCT_BUG          Gerçek uygulama hatası
│   ├── functional       İşlevsel hata (yanlış davranış)
│   ├── regression       Regresyon (önceden çalışıyordu)
│   ├── ui               Arayüz/görsel hata
│   └── data             Veri bütünlüğü/tutarsızlık
│
├── TEST_ISSUE           Test kodundaki sorun
│   ├── flaky            Kararsız test (bazen geçer/kalır)
│   ├── stale_locator    Güncelliğini yitirmiş selector/locator
│   ├── wrong_assertion  Hatalı doğrulama kriteri
│   ├── timing           Zamanlama/bekleme sorunu
│   └── test_data        Test verisi eksik veya uyumsuz
│
├── ENVIRONMENT          Ortam kaynaklı sorun
│   ├── infra_down       Servis erişilemez (DB, Redis, API)
│   ├── network          Ağ bağlantı sorunu
│   ├── resource         Yetersiz kaynak (CPU, bellek, disk)
│   ├── config           Yanlış yapılandırma
│   └── dependency       Dış bağımlılık hatası
│
├── AUTOMATION_DEBT      Otomasyon teknik borcu
│   ├── missing_wait     Eksik bekleme stratejisi
│   ├── hard_coded       Hard-coded değer (URL, port, veri)
│   ├── coupling         Testler arası bağımlılık
│   └── setup_teardown   Hazırlık/temizlik eksikliği
│
└── UNKNOWN              Henüz sınıflandırılmadı
```

## 2. Root-Cause Analysis Rapor Şablonu

### Başarısız Test — RCA Kaydı

```
┌─────────────────────────────────────────────────────────────┐
│ RCA-{ID}                                                     │
│                                                               │
│ Test:        {TEST_ADI}                                       │
│ Dosya:       {DOSYA_YOLU}:{SATIR}                            │
│ Execution:   Run #{RUN_ID} — {TARIH}                         │
│ Modül:       {MODUL}                                          │
│ Öncelik:     {P0/P1/P2}                                      │
│                                                               │
│ ─────────────────────────────────────────────────────────── │
│                                                               │
│ HATA MESAJI:                                                  │
│ {ERROR_MESSAGE}                                               │
│                                                               │
│ KÖK NEDEN KATEGORİSİ:                                       │
│ {CATEGORY} > {SUBCATEGORY}                                    │
│                                                               │
│ ANALİZ:                                                       │
│ {DETAYLI_ACIKLAMA}                                           │
│                                                               │
│ ETKİLENEN GEREKSİNİMLER:                                    │
│ - {REQ_ID_1}: {REQ_BASLIK_1}                                │
│ - {REQ_ID_2}: {REQ_BASLIK_2}                                │
│                                                               │
│ AKSİYON:                                                      │
│ {YAPILACAK_IS}                                                │
│                                                               │
│ SORUMLU: {KISI}                                              │
│ HEDEF:   {TARIH}                                             │
│ DURUM:   Açık / Çözülüyor / Çözüldü / Kapatıldı            │
│                                                               │
│ KANITLAR:                                                     │
│ - Screenshot: {SCREENSHOT_PATH}                               │
│ - Trace: {TRACE_PATH}                                        │
│ - Log: {LOG_SNIPPET}                                         │
└─────────────────────────────────────────────────────────────┘
```

## 3. Örnek RCA Kayıtları

### Örnek 1: Product Bug

```
RCA-042-001

Test:        senaryo aranabilmeli
Dosya:       e2e/scenarios.spec.ts:56
Execution:   Run #42 — 03.04.2026
Modül:       Senaryolar
Öncelik:     P1

HATA MESAJI:
TimeoutError: locator.getByText("Arama123456789")
  → Waiting for selector exceeded 10000ms

KÖK NEDEN KATEGORİSİ:
PRODUCT_BUG > functional

ANALİZ:
Arama alanına metin girildiğinde backend /api/v1/tspm/scenarios
endpoint'i filtreleme yapıyor ancak LIKE sorgusu büyük/küçük harf
duyarlı. Türkçe karakterli aramalarda (İ, Ş, Ö vb.) sonuç dönmüyor.
Backend'de case-insensitive ILIKE kullanılmalı.

ETKİLENEN GEREKSİNİMLER:
- REQ-SCN-001: Senaryo CRUD
- REQ-SCN-003: Senaryo arama ve filtreleme

AKSİYON:
Backend TSPM router'da LIKE → ILIKE değişikliği yapılacak.
Türkçe karakter normalize fonksiyonu eklenecek.

SORUMLU: Backend Dev
HEDEF:   04.04.2026
DURUM:   Çözülüyor

KANITLAR:
- Screenshot: reports/screenshots/rca-042-001.png
- Trace: e2e/test-results/scenarios-search-trace.zip
- Log: "SELECT ... WHERE title LIKE '%Arama%'" (case-sensitive)
```

### Örnek 2: Test Issue (Flaky)

```
RCA-042-002

Test:        toplu silme yapılabilmeli
Dosya:       e2e/scenarios.spec.ts:68
Execution:   Run #42 — 03.04.2026 (2/5 çalıştırmada başarısız)
Modül:       Senaryolar
Öncelik:     P1

HATA MESAJI:
Error: locator.check() - Element not visible
  → checkbox[name="Sil1_1712160000000"] not found

KÖK NEDEN KATEGORİSİ:
TEST_ISSUE > flaky

ANALİZ:
Test, önceki test tarafından oluşturulan senaryoları silmeye çalışıyor
ancak sayfa yüklenmeden checkbox'ları aramaya başlıyor. Race condition:
API'den gelen veri listesi henüz render edilmemiş olabiliyor. Ayrıca
timestamp bazlı senaryo adı nadiren çakışabiliyor.

AKSİYON:
1. page.waitForSelector() ile liste yüklenmesini bekle
2. UUID bazlı benzersiz isim kullan (Date.now() yerine)
3. Test izolasyonu için her test kendi verisini oluştursun

SORUMLU: QA Engineer
HEDEF:   05.04.2026
DURUM:   Açık

KANITLAR:
- Screenshot: reports/screenshots/rca-042-002.png
- Son 5 çalıştırma: PASS, FAIL, PASS, PASS, FAIL
```

### Örnek 3: Environment Issue

```
RCA-042-003

Test:        execution tamamlanmalı
Dosya:       e2e/executions.spec.ts:45
Execution:   Run #42 — 03.04.2026
Modül:       Execution
Öncelik:     P0

HATA MESAJI:
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8765

KÖK NEDEN KATEGORİSİ:
ENVIRONMENT > infra_down

ANALİZ:
Backend servisi test çalıştırması sırasında OOM (Out of Memory) ile
çökmüş. Docker container bellek limiti 512MB olarak ayarlanmış ancak
büyük veri seti analizi sırasında 800MB+ kullanım görülmüş.

AKSİYON:
1. Docker compose'da backend bellek limitini 1GB'a çıkar
2. Büyük veri seti analizi için streaming/chunk işleme ekle
3. Health check monitoring ekle

SORUMLU: DevOps + Backend Dev
HEDEF:   04.04.2026
DURUM:   Açık
```

## 4. RCA Özet Tablosu (Execution Bazlı)

| # | Test | Kategori | Alt Kategori | Etki | Öncelik | Durum |
|---|------|----------|-------------|------|---------|-------|
| RCA-042-001 | senaryo aranabilmeli | PRODUCT_BUG | functional | REQ-SCN-001 | P1 | Çözülüyor |
| RCA-042-002 | toplu silme | TEST_ISSUE | flaky | REQ-SCN-001 | P1 | Açık |
| RCA-042-003 | execution tamamlanmalı | ENVIRONMENT | infra_down | REQ-EXEC-001 | P0 | Açık |
| RCA-042-004 | rapor indirme | AUTOMATION_DEBT | missing_wait | REQ-RPT-001 | P2 | Açık |

### Dağılım

```
Bu Çalıştırma (#42):
  PRODUCT_BUG:     1  (25%)  ████████
  TEST_ISSUE:      1  (25%)  ████████
  ENVIRONMENT:     1  (25%)  ████████
  AUTOMATION_DEBT: 1  (25%)  ████████
  
Son 10 Çalıştırma Trendi:
  PRODUCT_BUG:     12 (30%)
  TEST_ISSUE:       8 (20%) — flaky: 6
  ENVIRONMENT:      8 (20%)
  AUTOMATION_DEBT: 12 (30%)
```

## 5. RCA Veri Modeli (JSON)

```json
{
  "rca_id": "RCA-042-001",
  "execution_id": "uuid",
  "test": {
    "name": "senaryo aranabilmeli",
    "file": "e2e/scenarios.spec.ts",
    "line": 56,
    "module": "scenarios",
    "tags": ["regression", "p1"],
    "scenario_id": "uuid",
    "requirement_ids": ["REQ-SCN-001", "REQ-SCN-003"]
  },
  "failure": {
    "error_type": "TimeoutError",
    "message": "locator.getByText() exceeded 10000ms",
    "stack_trace": "...",
    "screenshot": "reports/screenshots/rca-042-001.png",
    "trace": "e2e/test-results/trace.zip"
  },
  "root_cause": {
    "category": "PRODUCT_BUG",
    "subcategory": "functional",
    "description": "Case-sensitive LIKE sorgusu Türkçe karakterlerde başarısız",
    "affected_component": "backend/app/domains/tspm/router.py",
    "is_regression": false
  },
  "action": {
    "description": "LIKE → ILIKE değişikliği + Türkçe normalize",
    "assignee": "backend-dev",
    "target_date": "2026-04-04",
    "status": "in_progress",
    "ticket_url": "https://github.com/org/repo/issues/123"
  },
  "metadata": {
    "analyzed_by": "qa-engineer",
    "analyzed_at": "2026-04-03T14:30:00Z",
    "previous_occurrences": 0,
    "is_known_issue": false
  }
}
```

## 6. Tekrarlayan Başarısızlık Tespiti

Aynı test son N çalıştırmada birden fazla başarısız oluyorsa:

| Test | Son 10 Run | Başarısızlık Oranı | Pattern | Aksiyon |
|------|-----------|-------------------|---------|---------|
| toplu silme | P-F-P-P-F-P-F-P-P-F | 40% | Flaky | Stabilize et |
| execution tamamlanmalı | P-P-P-P-P-P-P-F-P-P | 10% | Ara sıra | İzle |
| rapor indirme | F-F-F-P-P-P-P-P-P-P | 30% (son 3'te 0%) | Çözülmüş | Kapat |
