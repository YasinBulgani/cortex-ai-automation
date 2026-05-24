# ADR-0003: Synthetic-data v4 ana platform

**Durum:** Kabul edildi
**Tarih:** 2026-04-19
**Karar verenler:** @yasin_bulgan

## Bağlam

Sentetik veri üretim kodu 2026-04 öncesinde 5 farklı yerdeydi:

| Konum | İçerik | Durum |
|---|---|---|
| `backend/synthetic-data-v2/` | Eski FastAPI standalone (6.4 MB) | Kullanılmıyor |
| `backend/synthetic-data-v3/` | V3 deneyi (6.4 MB) | Kullanılmıyor |
| `backend/synthetic-data-bgtsflow/` | BGTSFlow deneyi (116 KB) | Kullanılmıyor |
| `backend/synthetic-data-v4` | `../synthetic-data/platform-v4` symlink'i | Aktif proxy |
| `backend/banking-data` | `../synthetic-data/banking` symlink'i | Aktif proxy |
| `synthetic-data/platform/` | Önceki major sürüm (4.9 MB) | Kullanılmıyor |
| `synthetic-data/platform-v4/` | Güncel standalone FastAPI | Aktif (symlink üzerinden) |
| `synthetic-data/banking/` | Banking-specific servis + veri (335 MB) | Aktif |
| `synthetic-data/mostlyai-datasets/` | MostlyAI model output'ları | Kullanılmıyor |
| `synthetic-data/mostlyai-generators/` | MostlyAI training artefaktları | Kullanılmıyor |
| `backend/app/domains/ai_synthetic_data/` | Canlı FastAPI router | Aktif (ana API) |

Ayrıca `docs/history/MERGER_PLAN.md` bu birleştirmeyi 2025'te planlamış ama tamamlanmamıştı.

Sorun: 5 platform klasörü, tutarsızlık, "hangisini geliştireyim?" karmaşası.

## Karar

1. **Ana giriş noktası:** `backend/app/domains/ai_synthetic_data/` (FastAPI router). Tüm frontend ve dış API çağrıları buradan geçer.
2. **Kod birleştirme hedefi:** `synthetic-data/platform-v4/` → `backend/app/domains/ai_synthetic_data/` (kademeli, Faz 3.B).
3. **Veri birleştirme:** `synthetic-data/banking/` yerinde kalır (335 MB data + küçük FastAPI servisi). Şu an canlı.
4. **Arşivlenenler** (`legacy/2026-04-cleanup/`):
   - `backend/synthetic-data-v2/`
   - `backend/synthetic-data-v3/`
   - `backend/synthetic-data-bgtsflow/`
   - `synthetic-data/platform/`
   - `synthetic-data/mostlyai-datasets/`
   - `synthetic-data/mostlyai-generators/`
5. **Dokunulmayanlar:**
   - `synthetic-data/platform-v4/` — canlı (symlink ile bağlı)
   - `synthetic-data/banking/` — canlı

## Alternatifler

### A. Hepsini tek klasörde tut, `_v2`/`_v3` sufix'li bırak
**Red sebebi:** "Silinmeye aday" tablosu 12 ay önce eklenmişti ama kimse silmedi. Kültürü değiştiremedik, yapıyı değiştiriyoruz.

### B. Symlink'leri kaldır, `synthetic-data/` yapısını düzleştir
**Red sebebi:** Symlink'ler çalışan canlı servisin bir parçası. Değiştirmek için koordine deploy gerekli. Ayrı PR.

### C. MostlyAI artefaktlarını DVC/LFS'e taşı
**Red sebebi:** Kullanılmıyorlar. DVC kurulumu + migration maliyeti kullanım değerinden yüksek. Arşivde kalıp 6 ay sonra silinmesi daha sağlıklı. Gerekirse ileride DVC ile döner.

## Sonuçlar

### Olumlu
- 5 platform → 1 canlı (+1 data dir)
- "Hangi dizin?" karmaşası biter
- Git repo ağırlığı ~13 MB azalır (mostlyai artefaktları dahil ~350 MB)
- Yeni developer onboarding netleşir

### Olumsuz / takas
- `backend/synthetic-data-v4` symlink'i hâlâ var — birisi bunu "niye burada?" diye sorabilir
- `platform-v4/` → `backend/app/domains/` birleştirmesi henüz yapılmadı (Faz 3.B)
- 335 MB banking veri hâlâ repo'da — DVC/LFS adayı

### Takip işleri
- [x] `mostlyai-datasets/` ve `mostlyai-generators/` arşivlendi (2026-04-19)
- [x] Eski `backend/synthetic-data-v2/v3/bgtsflow/` arşivlendi
- [x] `synthetic-data/platform/` arşivlendi
- [x] Faz 3.B gap analizi: `docs/architecture/synthetic-data-gap-analysis.md` (2026-04-19) — platform-v4'ün backend'de eksik 6 özelliği tespit edildi: schema analyzer, column classifier, rule engine, learning engine, scenarios, project model
- [x] **Faz 3.B Gün 1 uygulama** (2026-04-20):
  - 5 core modül `backend/app/domains/ai_synthetic_data/platform/`'a port edildi
  - 4 SQLAlchemy modeli (`tspm_synthetic_*` prefix'li, çakışma yok)
  - Alembic migration: `20260420_0001_synthetic_platform_tables.py`
  - 7 yeni endpoint `/synthetic-platform/*` (analyze, scenarios, projects CRUD, rules/infer, learning/analyze)
  - `router_registry.py`'a kayıt edildi
  - 26 unit test (21 pass + 5 pandas-optional skip)
- [ ] Faz 3.B Gün 2-3: kalan endpoint'ler (schemas CRUD, rules CRUD, generation/preview), frontend entegrasyonu, platform-v4 arşivi
- [ ] Faz 3.C: `backend/synthetic-data-v4` ve `backend/banking-data` symlink'leri kaldırılıp direct path'ler kullanılacak
- [ ] Faz 3.D: `synthetic-data/banking/frontend/` (335 MB) DVC/LFS adayı mı değerlendir

## İlgili

- [ADR-0004](0004-legacy-silme-politikasi.md)
- [legacy/README.md](../../legacy/README.md)
- [docs/history/MERGER_PLAN.md](../history/MERGER_PLAN.md) — tarihsel bağlam
