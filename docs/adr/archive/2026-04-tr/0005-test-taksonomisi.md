# ADR-0005: Test katmanları ve konumları

**Durum:** Kabul edildi
**Tarih:** 2026-04-19
**Karar verenler:** @yasin_bulgan

## Bağlam

Proje'de test kodu 8+ yerde vardı:

- `e2e/`
- `api-tests/`
- `tests/` (root, belirsiz)
- `engine/tests/`
- `backend/tests/`
- `frameworks/playwright-cucumber-ts/`
- `apps/web/app/__tests__/`
- `synthetic-data/*/tests/`

Yeni gelen developer "yeni test nereye yazayım?" sorusuna 3 farklı cevap alıyordu. Aynı davranış birden çok yerde test ediliyordu (ör: login hem unit hem E2E). Test piramidi belirsizdi.

## Karar

Her test tipi için **tek ve resmi** bir konum tanımlandı. Karar ağacı ile `qa/strategy/test-strategy.md`'de yazıldı.

Özet:

| Katman | Konum | Hedef % |
|---|---|---|
| Unit (Python) | `backend/tests/unit/`, `engine/tests/unit/` | %70 |
| Unit (TS) | `apps/web/app/__tests__/` | (aynı havuzda) |
| Integration | `backend/tests/integration/`, `engine/tests/integration/` | %25 |
| API contract | `api-tests/contracts/` | (aynı havuzda) |
| API regression | `api-tests/` | (aynı havuzda) |
| E2E | `e2e/` | %5 |
| BDD | `frameworks/playwright-cucumber-ts/features/` | (E2E içinde) |

Her test bir **marker/tag** taşımalı:
- `smoke` — her PR'da çalışır (~2 dk)
- `regression` — nightly + pre-merge (~10 dk)
- `slow` — >5 s süren
- `ai` — LLM çağırır (ücret)
- `requires_db`, `requires_redis` — altyapı bağımlılığı

## Alternatifler

### A. Tek `tests/` klasörü, hepsi orada
**Red sebebi:**
- Python + TS testleri aynı dizinde → runner konfigi karmaşa
- Backend vs engine vs frontend testleri ayrı runtime gerektiriyor
- Test çalıştırma hızı yönetilemez

### B. Test'leri kodla yan yana (`src/foo.py` + `src/test_foo.py`)
**Red sebebi:**
- Distro/paket oluşurken test'ler ship edilmemeli → filtreleme yükü
- Python'da kabul edilmiş pattern değil (TS'de yaygın)
- `backend/app/` içine test koymak Django/FastAPI topluluğunun kullandığı pattern değil

### C. Mevcut durumu koru (8 farklı dizin)
**Red sebebi:** Ana problem buydu.

## Sonuçlar

### Olumlu
- "Yeni test nereye?" sorusunun tek cevabı: karar ağacı
- Marker/tag sistemi ile `make test-smoke` her zaman hızlı
- Piramit hedefleri PR'larda konuşulabilir (`%70-25-5`)
- CI'da her katman ayrı job → paralelleştirilebilir

### Olumsuz / takas
- Mevcut testlerin taşınması gerekiyor (özellikle root `tests/`)
- Marker disiplini → unutulursa `test-smoke` çalışmaz
- Team eğitimi gerekli

### Takip işleri
- [x] Doküman: `qa/strategy/test-strategy.md` (2026-04-19)
- [x] `tests/load/`, `tests/performance/` → `performance-tests/` (2026-04-19)
- [x] Root `tests/` dizinini sil — kırık Python entegrasyon test'leri silindi (2026-04-19, hardcoded `/sessions/zealous-lucid-bell/` path'leri nedeniyle çalışmıyorlardı)
- [ ] CI'da marker-based matrix: smoke / regression / full jobs
- [ ] CONTRIBUTING.md'ye test karar ağacı linki ekle
- [ ] Pre-commit hook: yeni test dosyaları için marker kontrolü

## İlgili

- [qa/strategy/test-strategy.md](../../qa/strategy/test-strategy.md)
- [ADR-0001](0001-monorepo-yapisi.md)
