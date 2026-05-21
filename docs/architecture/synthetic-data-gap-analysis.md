# Synthetic-Data Gap Analysis: platform-v4 → backend merge

> Bu doküman **ADR-0003 Faz 3.B**'nin uygulama öncesi teknik analizidir.
> Tarih: 2026-04-19
> Kapsam: `synthetic-data/platform-v4/` kodunun `backend/app/domains/ai_synthetic_data/`'ya entegrasyonu.

## TL;DR

Platform-v4 ve backend modülü **tamamlayıcı** — birbirinin kopyası değil. Platform-v4'te backend'de bulunmayan **6 temel özellik** var. Tam merge ~2-3 günlük bir iş; öncelik sırasına koyduk.

## Mevcut durum (canlı)

```
synthetic-data/platform-v4/          backend/app/domains/ai_synthetic_data/
├── app/                             ├── __init__.py
│   ├── api/                         ├── advanced_generators.py    (1023 satır)
│   │   ├── generation.py (562)     ├── advanced_schemas.py       ( 119)
│   │   ├── schemas.py    (329)     ├── differential_privacy.py   ( 781)
│   │   └── learning.py   ( 98)     ├── privacy_scanner.py        ( 315)
│   ├── core/                       ├── privacy_schemas.py        ( 149)
│   │   ├── analyzer.py   (160)     └── router.py                 ( 404)
│   │   ├── classifier.py (179)
│   │   ├── rule_engine.py(151)     Toplam: 2.792 satır
│   │   ├── learning_    (199)
│   │   │   engine.py
│   │   └── scenarios.py (274)
│   ├── models/schema_model.py (82)
│   ├── main.py (69)
│   ├── database.py (36)
│   ├── config.py (22)
│   └── templates/index.html (1793)
│
│  Toplam (HTML hariç): 2.161 satır
```

Erişim: `backend/synthetic-data-v4 → ../synthetic-data/platform-v4` symlink'i üzerinden (ADR-0003 Faz 3.C'de temizlenecek).

## Özellik karşılaştırması

| Özellik | Backend | Platform-v4 | Sahip |
|---|---|---|---|
| Advanced generators (Faker, temporal, geo) | ✅ `advanced_generators.py` | ⚠ kısmi (`scenarios.py` içinde) | **Backend** (çok daha kapsamlı) |
| Differential privacy (Laplace, Gaussian) | ✅ `differential_privacy.py` | ❌ | **Backend** |
| PII scanner (TCKN/IBAN Luhn/mod97) | ✅ `privacy_scanner.py` | ❌ | **Backend** |
| k-anonymity, l-diversity, re-id risk | ✅ 4 endpoint | ❌ | **Backend** |
| Banking-specific dataset generator | ✅ `/banking-dataset` | ❌ | **Backend** |
| Privacy reports + suggest-config | ✅ 2 endpoint | ❌ | **Backend** |
| **Schema auto-analyzer** (CSV/Excel → schema) | ❌ | ✅ `analyzer.py` | **Platform-v4** |
| **AI column classifier** (GPT-4 ile kolon türü) | ❌ | ✅ `classifier.py` | **Platform-v4** |
| **Rule engine** (kullanıcı-tanımlı override) | ❌ | ✅ `rule_engine.py` | **Platform-v4** |
| **Learning engine** (geri bildirimden öğrenme) | ❌ | ✅ `learning_engine.py` | **Platform-v4** |
| **Scenario manager** (senaryo şablon yönetimi) | ❌ | ✅ `scenarios.py` | **Platform-v4** |
| Project yönetimi (Project model) | ❌ | ✅ `schema_model.py` | **Platform-v4** |
| HTML standalone UI | ❌ | ✅ `templates/index.html` | Platform-v4 (silinecek — frontend React'te) |
| `/generate` endpoint | ✅ | ⚠ farklı imza | İki farklı API |
| `/analyze` endpoint (file upload → schema) | ❌ | ✅ | **Platform-v4** |
| `/projects` CRUD | ❌ | ✅ | **Platform-v4** |
| `/learning` feedback ingest | ❌ | ✅ | **Platform-v4** |

## Endpoint farkı (API yüzeyi)

### Backend şu an sunuyor (13 endpoint)

```
POST   /api/v1/synthetic-data/generate
POST   /api/v1/synthetic-data/banking-dataset
POST   /api/v1/synthetic-data/quality-check
POST   /api/v1/synthetic-data/privacy-risk
GET    /api/v1/synthetic-data/generators
POST   /api/v1/synthetic-data/privacy/privatize
POST   /api/v1/synthetic-data/privacy/k-anonymity
POST   /api/v1/synthetic-data/privacy/l-diversity
POST   /api/v1/synthetic-data/privacy/reidentification-risk
POST   /api/v1/synthetic-data/privacy/report
POST   /api/v1/synthetic-data/privacy/suggest-config
POST   /api/v1/synthetic-data/privacy/validate-tckn
```

### Platform-v4 şu an sunuyor (~15 endpoint)

```
POST   /api/schemas/analyze            (file upload → detected schema)
GET    /api/schemas/projects
GET    /api/schemas/all
GET    /api/schemas/graph
GET    /api/schemas/{schema_id}
POST   /api/schemas/{schema_id}/rules
PUT    /api/schemas/{schema_id}/rules/{rule_id}
DELETE /api/schemas/{schema_id}/rules/{rule_id}
POST   /api/generation/generate         (DetectedSchema + rules → data)
POST   /api/generation/preview
POST   /api/generation/export
GET    /api/generation/history
POST   /api/learning/feedback           (generated row + label → train)
GET    /api/learning/stats
```

**Çakışma yok** — endpoint prefix'leri farklı (`/schemas`, `/generation`, `/learning` vs `/synthetic-data/*`). Merge sırasında namespacing kararı gerek:

**Önerilen hedef namespace:**
```
/api/v1/synthetic-data/                 (backend tarafı — "hızlı üretim + privacy")
/api/v1/synthetic-data/schemas/         (platform-v4 taşınır)
/api/v1/synthetic-data/generation/      (platform-v4 taşınır)
/api/v1/synthetic-data/learning/        (platform-v4 taşınır)
```

## Veri modeli farkları

### Backend şu an
- **Stateless** — yeni üretim her seferinde sıfırdan, DB'ye project kaydedilmiyor
- Privacy kontrolleri in-memory

### Platform-v4
- 4 tablo: `projects`, `detected_schemas`, `generation_rules`, `generation_history`
- `Project` → çoktan çoğa → `DetectedSchema` → çoktan çoğa → `GenerationRule`
- SQLAlchemy Async (uyumlu backend ile)

**Merge stratejisi:** Platform-v4'ün 4 tablosunu backend'in Alembic migration'ına taşı. Backend zaten `asyncpg` kullanıyor, tablo modelleri **olduğu gibi** kopyalanabilir (namespace düzeltilir: `tspm_synthetic_projects` vs `projects` gibi bir prefix eklenir).

## Bağımlılık farkı

`synthetic-data/platform-v4/requirements.txt` vs `backend/requirements.txt`:

Platform-v4'ün ek bağımlılıkları:
- `pandas` (Excel/CSV analizi için) — backend zaten var
- `openpyxl` (Excel)
- `python-magic` (file type detection)
- `networkx` (schema graph API)

Hepsi backend'e ekleniyor (`requirements.txt`'e merge).

## Uygulama planı (3 gün)

### Gün 1 — Core modüller

1. **Migration yaz** — `backend/alembic/versions/YYYYMMDD_synthetic_platform_tables.py`
   - `tspm_synthetic_projects`, `tspm_detected_schemas`, `tspm_generation_rules`, `tspm_generation_history`
2. **Core modülleri taşı** — backend'e yeni alt-modüller olarak:
   - `backend/app/domains/ai_synthetic_data/schema_analyzer.py` (platform-v4 `analyzer.py`)
   - `backend/app/domains/ai_synthetic_data/column_classifier.py` (platform-v4 `classifier.py`)
   - `backend/app/domains/ai_synthetic_data/rule_engine.py` (platform-v4 `rule_engine.py`)
   - `backend/app/domains/ai_synthetic_data/learning_engine.py` (platform-v4 `learning_engine.py`)
   - `backend/app/domains/ai_synthetic_data/scenarios.py` (platform-v4 `scenarios.py`)
3. **Testler** — her modül için en az 2 unit test (backend/tests/unit/ai_synthetic_data/)

### Gün 2 — API yüzeyi

4. **Router'a endpoint ekle** — `backend/app/domains/ai_synthetic_data/router.py`:
   - `POST /synthetic-data/schemas/analyze`
   - `GET|POST|PUT|DELETE /synthetic-data/schemas/{id}/rules`
   - `POST /synthetic-data/generation/preview`
   - `POST /synthetic-data/learning/feedback`
5. **OpenAPI doc** kontrolü
6. **Integration testler** (`backend/tests/integration/test_synthetic_platform.py`)

### Gün 3 — Frontend + temizlik

7. **Frontend** — `apps/web/lib/hooks/use-synthetic-advanced.ts`'e yeni endpoint'leri ekle
8. **Standalone HTML UI sil** — `synthetic-data/platform-v4/app/templates/index.html` artık gereksiz
9. **`synthetic-data/platform-v4/` dizinini arşivle** — `legacy/2026-04-cleanup/synthetic-data-platform-v4/`
10. **Symlink temizle** — `backend/synthetic-data-v4` sembolik bağı sil (ADR-0003 Faz 3.C)
11. **docker-compose'da eski platform-v4 standalone servisi varsa kaldır** (şu an zaten yok, ama kontrol et)

## Risk analizi

| Risk | Olasılık | Etki | Azaltma |
|---|---|---|---|
| Alembic migration çakışması | Orta | Yüksek | Migration dry-run; `--sql` flag'i ile SQL önizleme |
| Mevcut frontend entegrasyonu kırılır | Düşük | Orta | Eski endpoint'leri deprecated header ile 1 hafta canlı tut |
| Core modüller farklı SQLAlchemy dialect'i bekler | Düşük | Düşük | Her ikisi de async + asyncpg, uyumlu |
| Learning engine training data kaybı | Düşük | Yüksek | `generation_history` migration'da DATA MOVE komutu ile senkronize et |
| Pandas/openpyxl ekleyince build süresi artar | Yüksek | Düşük | Kabul edilebilir |

## Kabul kriterleri (merge tamamlandı)

- [ ] `synthetic-data/platform-v4/` artık çalıştırılmıyor (standalone FastAPI app emekli)
- [ ] `backend/app/domains/ai_synthetic_data/` 12+ endpoint sunuyor (şu an 13 + yeni 7-10)
- [ ] Frontend `/synthetic-data/schemas/analyze` tekrar çalışıyor (daha önce platform-v4'teydi)
- [ ] `alembic upgrade head` yeni tabloları oluşturuyor
- [ ] `backend/tests/integration/test_synthetic_platform.py` — happy path + privacy guard testleri yeşil
- [ ] `docs/adr/0003-synthetic-data-konsolidasyonu.md` takip listesi güncel
- [ ] `legacy/2026-04-cleanup/synthetic-data-platform-v4/` arşivlendi
- [ ] `backend/synthetic-data-v4` symlink'i silindi

## İlgili

- [ADR-0003: Synthetic-data konsolidasyonu](../adr/0003-synthetic-data-konsolidasyonu.md)
- [legacy/README.md](../../legacy/README.md) — neyin arşivlendiği
- [docs/history/MERGER_PLAN.md](../history/MERGER_PLAN.md) — 2025 eski planı (tarihsel)
