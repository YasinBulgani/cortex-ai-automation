# TestwrightAI + test-automation Birleştirme Planı

> **Not:** Tarihsel doküman — projenin eski kod adı olan "BGTS Test Dönüşüm" döneminde
> yazılmıştır. Aşağıda geçen "BGTS" referansları mevcut TestwrightAI monorepo'suna karşılık
> gelir. Tarihsel doğruluğu korumak için kullanılan orijinal terimler muhafaza edilmiştir.

## Özet

| | test-automation | BGTS_Test_Donusum |
|---|---|---|
| **Yol** | `/Users/yasin_bulgan/test-automation` | `/Users/yasin_bulgan/Desktop/BGTS_Test_Donusum` |
| **Boyut** | ~3.6 GB | ~1.9 GB |
| **Tür** | Standalone Flask + pytest-bdd | Monorepo (FastAPI + Flask + Next.js) |
| **Karar** | → Kaynak (taşınacak) | ← Hedef (ana proje) |

---

## Adım 1 — Benzersiz Route'ları Taşı

`test-automation/routes/` → `BGTS_Test_Donusum/engine/routes/`

| Dosya | Açıklama | Eylem |
|---|---|---|
| `analytics_routes.py` | Test metrik/analytics endpoint'leri | Kopyala → `engine/routes/analytics_routes.py` |
| `banking_routes.py` | Bankacılık API endpoint'leri | Kopyala → `engine/routes/banking_routes.py` |
| `editor_routes.py` | IDE tarzı editör arayüzü | Kopyala → `engine/routes/editor_routes.py` |
| `magic_test_routes.py` | Sihirli test üretimi | Kopyala → `engine/routes/magic_test_routes.py` |

**app.py'ye eklenecek blueprint kayıtları:**
```python
from routes.analytics_routes import analytics_bp
from routes.banking_routes import banking_bp
from routes.editor_routes import editor_bp
from routes.magic_test_routes import magic_test_bp
```

---

## Adım 2 — Benzersiz Core Modülleri Taşı

`test-automation/core/` → `BGTS_Test_Donusum/engine/core/`

| Dosya | Açıklama | Eylem |
|---|---|---|
| `analytics_engine.py` | Analytics hesaplama motoru | Kopyala → `engine/core/analytics_engine.py` |
| `reporting_engine.py` | Test raporlama sistemi | Kopyala → `engine/core/reporting_engine.py` |
| `test_case_manager.py` | Test case yönetim katmanı | Kopyala → `engine/core/test_case_manager.py` |
| `ai_engine_extensions.py` | AI motor eklentileri | Kopyala → `engine/core/ai_engine_extensions.py` |
| `monkey_test_engine.py` | Fuzzy/rastgele test motoru | Kopyala → `engine/core/monkey_test_engine.py` |

**Not:** `monkey_test_engine.py` BGTS'deki `monkey_routes.py` ile bağlanacak.

---

## Adım 3 — Banking/Sentetik Veri Modülünü Taşı

`test-automation/core/banking/` → `BGTS_Test_Donusum/engine/core/banking/`

Taşınacak dosyalar:
- `core/banking/ai_data_generator.py`
- `core/banking/db_schema_reader.py`
- `core/banking/schema_aware_generator.py`
- `core/banking/factories/` (tüm factory sınıfları)
- `core/banking/generators/` (tüm generator sınıfları)

---

## Adım 4 — Sentetik Veri Platformlarını Birleştir

`test-automation/` → `BGTS_Test_Donusum/backend/synthetic-data/`

| Kaynak | Hedef | Not |
|---|---|---|
| `synthetic-data-platform-v4/` | `backend/synthetic-data/` | En güncel versiyon, ana platform |
| `synthetic-data-platform-v3/` | `backend/synthetic-data-v3/` | Referans için tut |
| `synthetic-data-platform-v2/` | `backend/synthetic-data-v2/` | Referans için tut |
| `banking-synthetic-data/` | `backend/banking-data/` | Banking veri örnekleri |
| `ai_synthetic_data/` | Zaten BGTS'de mevcut | Birleştir/karşılaştır |

**Not:** BGTS backend'i FastAPI kullanıyor. Sentetik veri platformları FastAPI router olarak entegre edilecek.

---

## Adım 5 — Konfigürasyon Dosyalarını Birleştir

`test-automation/config/` → `BGTS_Test_Donusum/engine/config/`

| Dosya | Eylem |
|---|---|
| `a11y_config.json` | Kopyala → `engine/config/a11y_config.json` (BGTS'de yoksa) |
| `visual_config.json` | Kopyala → `engine/config/visual_config.json` (BGTS'de yoksa) |
| `settings.py` | **Birleştir**: BGTS `settings.py` temel alınır, benzersiz değerler eklenir |

---

## Adım 6 — Feature/Steps/Tests Birleştir

### Features
- `test-automation/features/Otomasyonlar/` → `engine/features/Otomasyonlar/` (mevcut dosyalara ekle)

### Steps
- `test-automation/steps/common_steps.py` → BGTS `engine/steps/common_steps.py` ile birleştir

### Tests
- `test-automation/tests/` → `engine/tests/` altında uygun klasöre yerleştir

---

## Adım 7 — Veri/Dataset'leri Taşı

| Kaynak | Hedef |
|---|---|
| `test-automation/datasets/` | `engine/datasets/` (mevcut ile birleştir) |
| `test-automation/data/` | `engine/test_data/` altına taşı |

---

## Adım 8 — Script'leri Birleştir

`test-automation/scripts/` → `BGTS_Test_Donusum/engine/scripts/` (yeni/benzersiz olanlar)

---

## Adım 9 — "Test Otomasyon" Klasörü

`test-automation/Test Otomasyon/` → `BGTS_Test_Donusum/docs/test-otomasyon/`

Türkçe dokümantasyon/UI materyalleri merkezi docs klasörüne taşınır.

---

## Adım 10 — Git Geçmişini Koru

```bash
# BGTS ana repo'suna test-automation geçmişini ekle
cd /Users/yasin_bulgan/Desktop/BGTS_Test_Donusum
git remote add legacy-automation /Users/yasin_bulgan/test-automation
git fetch legacy-automation
# Her modülü git subtree ile taşı (geçmişi koruyarak)
git subtree add --prefix=engine/core/banking legacy-automation/main:core/banking
```

---

## Çakışan Dosyalar — Karar Matrisi

| Dosya | test-automation | BGTS | Karar |
|---|---|---|---|
| `core/ai_engine.py` | Temel AI | Genişletilmiş AI + 6 AI alt modül | **BGTS sürümü koru** |
| `core/db.py` | Temel SQLite | Test yönetimi tablolarıyla genişletilmiş | **BGTS sürümü koru** |
| `core/reporter.py` | Temel | Allure entegre | **BGTS sürümü koru** |
| `core/browser.py` | Playwright | Playwright + kayıt | **BGTS sürümü koru** |
| `routes/ai_routes.py` | Temel AI | AI extract + service tests eklenmiş | **BGTS sürümü koru** |
| `app.py` | Temel Flask | Tüm blueprint'ler kayıtlı | **BGTS sürümü koru, yeni bp'ler ekle** |

---

## Taşıma Öncelik Sırası

```
1. [YÜKSEKöncelik] Core modüller (analytics, reporting, banking)
2. [YÜKSEKöncelik] Routes (analytics, banking, editor, magic_test)
3. [ORTA]           Sentetik veri platformu v4
4. [ORTA]           Config dosyaları
5. [DÜŞÜK]          Feature/steps/tests
6. [DÜŞÜK]          Datasets, scripts
7. [EN SON]         Git geçmiş birleştirme
```

---

## Temizlenecekler (Birleştirme Sonrası)

1. `test-automation/venv312/`, `venv_clean/`, `venv_new/`, `venv_platform/` → SİL (dev ortamları)
2. `test-automation/allure-report/`, `test-automation/allure-results/` → SİL (generated artifacts)
3. `test-automation/screenshots/` → Gerekirse `engine/screenshots/` altına taşı
4. Eski `test-automation/` dizinini arşivle veya sil

---

## docker-compose Entegrasyonu

`BGTS_Test_Donusum/docker-compose.yml`'a sentetik veri servisi eklenecek:

```yaml
  synthetic-data:
    build: ./backend/synthetic-data
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=${DATABASE_URL}
```

---

## Tahmini Süre

| Adım | Süre |
|---|---|
| Route + Core kopyalama | 30 dk |
| Sentetik veri birleştirme | 1 saat |
| Config birleştirme | 15 dk |
| Test/Feature taşıma | 45 dk |
| Docker entegrasyon | 30 dk |
| **Toplam** | **~3 saat** |
