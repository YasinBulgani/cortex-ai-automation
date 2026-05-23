# engine/features/ — Detay Envanteri

**Tarih:** 2026-05-23
**Hazırlayan:** PR 23 (qa/ migration)
**Durum:** Bilgi amaçlı, **read-only**. Bu dokümanın amacı engine/features/'taki 65 dosyanın migration ihtimallerini ortaya koymaktır; gerçek migration engineering team sahipliğindedir.

---

## Üst düzey rakamlar

| Konum | Dosya | Toplam satır | Step defs | Tahmini sahip |
|---|---:|---:|---:|---|
| `engine/features/Otomasyonlar/` | 8 | 211 | `engine/steps/` (40 dosya toplam, paylaşımlı) | Engine team |
| `engine/features/ai/` | 3 | 350 | Visual AI, recording, generation | AI team |
| `engine/features/ai_generated/` | 4 | 38 | AI üretti taslaklar (kısa) | AI team |
| `engine/features/api/` | 16 | 713 | API contract testleri | Backend team |
| `engine/features/e2e/` | 2 | 263 | Tam akış (data-driven, user journey) | E2E team |
| `engine/features/reporting/` | 1 | 219 | Raporlama akışları | Reporting team |
| `engine/features/testwright-ai/` | 10 | 1104 | TestWright AI motor testleri | AI team |
| `engine/features/web/` | 6 | 382 | Web UI testleri (Paribu trading dahil) | Web team |
| `engine/features/wizard/` | 14 | 103 | Wizard akış parçaları (kısa, üretilmiş) | Wizard team |
| **TOPLAM** | **65** | **3383** | **40 step defs** | **5 takım** |

## Anomaliler

| Dosya | Sorun |
|---|---|
| `engine/features/lks.featıres.feature` | Dosya adında typo (`featıres` → `features`). Test: `engine/tests/test_lks.featıres.py` aynı typo'yla referans veriyor. |
| `engine/features/wizard/20260420120748743689/*.feature` | Dosya isimleri timestamp + Türkçe slug + numara — otomatik üretilmiş, manuel okunabilirlik düşük. Auto-generated marker eksik. |
| `engine/features/ai_generated/` | Sadece 38 satır toplam (4 dosya) — boş veya placeholder olabilir, üretici verisinin truncate olduğu izlenimi. |

## Migration ihtimalleri

### 1. Tamamen siliniecekler (düşük risk)

| Kategori | Tahmin | Mantık |
|---|---|---|
| `wizard/20260420120748743689/` | 100% silinebilir | Auto-generated, tek seferlik wizard çıktısı. Test value belirsiz. |
| `ai_generated/` | 75% silinebilir | Placeholder muhtemel. AI ile yeniden üretilebilir. |
| `lks.featıres.feature` | %100 — sadece rename gerek | Typo fix; test paralel rename'lenmeli. |

### 2. `e2e/bdd/features/`'a taşınabilecekler

| Kategori | Hedef konum | Engel |
|---|---|---|
| `Otomasyonlar/login.feature` | `e2e/bdd/features/auth/login.feature` ile birleştir | Mevcut e2e zaten var; içerik karşılaştırma + merge gerek |
| `web/*.feature` (6) | `e2e/bdd/features/web/` | Yeni alt klasör. Step defs Python; Node Cucumber'a port |
| `ai/visual-ai-analysis.feature` | `e2e/bdd/features/ai/` | AI motor testleri için yeni dizin |

### 3. `backend/tests/bdd/features/`'a taşınabilecekler

| Kategori | Hedef konum | Engel |
|---|---|---|
| `api/*.feature` (16) | `backend/tests/bdd/features/api/` | Step defs zaten Python (pytest-bdd uyumlu) — taşıma kolay |
| `reporting/reporting.feature` | `backend/tests/bdd/features/reporting.feature` | Tek dosya |

### 4. Yeni runner gerektirenler

| Kategori | Engel |
|---|---|
| `testwright-ai/` (10, 1104 satır) | TestWright AI motor testleri. Mevcut Cucumber.mjs/pytest-bdd uygun olmayabilir; özel runner. |
| `e2e/data-driven-workflows.feature` | Data-driven design — Cucumber `Scenario Outline` + Examples ile portable |

## qa/cases/ ile potansiyel eşleşmeler

Aşağıdaki `engine/features/` dosyaları muhtemelen qa/cases/'teki TC'lerin eski otomasyon versiyonudur:

| engine/features/ | Olası qa/cases/ TC |
|---|---|
| `Otomasyonlar/login.feature` | TC-AUTH-001..002 (zaten e2e/bdd/'de tagged) |
| `Otomasyonlar/akislar.feature` | TC-FLW-001..002 |
| `api/bdd_generation.feature` | TC-SCN-005, TC-BDD-* |
| `api/members.feature` | TC-PRJ-005..006 (üye ekle/çıkar), TC-MEM-* |
| `api/regression.feature` | TC-REG-001..004 |
| `api/dashboard.feature` | TC-DASH-* (henüz TC yok) |
| `web/visual-regression.feature` | TC-VIS-001 |
| `reporting/reporting.feature` | TC-RPT-* (henüz TC yok) |
| `ai/test-recording.feature` | TC-REC-001 |

**Bu eşleşmeler doğrulanmamıştır** — içerik karşılaştırması gerekir.

## Tam migration roadmap (önerilen sıra)

| Aşama | İş | Risk | Sahip |
|---|---|---|---|
| 1 | `wizard/20260420120748743689/` + `ai_generated/` silinmesi | Düşük (placeholder veriler) | Engine team |
| 2 | `lks.featıres.feature` rename + test rename | Düşük | Engine team |
| 3 | `api/*.feature` → `backend/tests/bdd/features/api/` | Orta (step defs port) | Backend team |
| 4 | `Otomasyonlar/login.feature` → `e2e/bdd/features/auth/` ile merge | Orta (içerik karşılaştırma) | Auth + E2E |
| 5 | `web/*.feature` → `e2e/bdd/features/web/` | Orta (Python → Node port) | Web team |
| 6 | `ai/*.feature` + `testwright-ai/*` özel runner kararı | Yüksek | AI team |
| 7 | `engine/steps/` (40 dosya) refactor — kullanılmayan step defs sil, kalanları yeni konumlara taşı | Yüksek (40 dosya) | Engine team |
| 8 | `engine/pytest.ini` `bdd_features_base_dir` config kaldır | Düşük (config) | Engine team |
| 9 | `engine/features/` klasörü tamamen sil | — | Engine team |

**Tahmini toplam süre:** 2-3 sprint (4-6 hafta), her sprint'te 2-3 aşama.

## Ne yapılmadı (kapsam dışı)

- `engine/steps/` 40 dosyanın hangi feature'ları referans verdiğinin tam haritalama
- Her .feature dosyasının deprecated mi aktif mi olduğunun pytest run ile doğrulanması
- Step defs runtime hata kontrolü
- E2E testlerinin pytest-bdd → Cucumber.mjs port maliyeti tahmini

Bu QA migration kapsamı (qa/ klasörünün kurulması) için **gereksiz**. Engineering team kendi sprint'inde detay analizini yapacak.

## Referanslar

- `engine/features/DEPRECATED.md` — Resmi deprecation notu (PR 10'da güncellendi)
- `qa/strategy/migration.md` — qa/ migration tarihçesi (PR 1–22)
- `qa/CONVENTIONS.md` — Yeni TC ID şeması
