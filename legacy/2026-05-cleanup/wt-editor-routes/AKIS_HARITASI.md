# Manuel Test → Otomasyon Akış Haritası

> Tarih: 2026-04-09 | Durum: Analiz + Köprü endpoint'leri eklendi

---

## Hedef Akış

```
Analist      UI            Engine (Flask:5001)       AI Engine            Sonuç
  │           │                  │                       │                  │
  │  Manuel   │                  │                       │                  │
  │  Test Yaz │                  │                       │                  │
  ├──────────▶│  POST /api/      │                       │                  │
  │           │  manual-tests    │                       │                  │
  │           ├─────────────────▶│ DB'ye kaydeder        │                  │
  │           │                  │                       │                  │
  │  Adım     │                  │                       │                  │
  │  Ekle     │  POST /api/      │                       │                  │
  ├──────────▶│  manual-tests    │                       │                  │
  │           │  /{id}/steps     │                       │                  │
  │           ├─────────────────▶│ Adımları kaydeder     │                  │
  │           │                  │                       │                  │
  │  "Otomasyona                 │                       │                  │
  │  Çevir"   │  POST /api/      │                       │                  │
  ├──────────▶│  pipeline/       │                       │                  │
  │           │  manual-to-      │                       │                  │
  │           │  automation      │                       │                  │
  │           ├─────────────────▶│                       │                  │
  │           │                  │ 1. Adımları DB'den    │                  │
  │           │                  │    çeker              │                  │
  │           │                  ├──────────────────────▶│                  │
  │           │                  │ 2. generate_gherkin() │                  │
  │           │                  │◀──────────────────────│ Gherkin döner    │
  │           │                  ├──────────────────────▶│                  │
  │           │                  │ 3. generate_test_file()│                 │
  │           │                  │◀──────────────────────│ Playwright döner │
  │           │                  │                       │                  │
  │           │                  │ 4. .feature dosyasına │                  │
  │           │                  │    kaydeder           │                  │
  │           │                  │                       │                  │
  │           │◀─────────────────│ {gherkin, code,       │                  │
  │           │                  │  feature_path,        │                  │
  │           │                  │  locators}            │                  │
  │           │                  │                       │                  │
  │  Sonuç    │                  │                       │                  │
  │  Görüntüle│                  │                       │                  │
  │◀──────────│ Gherkin + Kodu   │                       │                  │
  │           │ gösterir         │                       │                  │
  │           │                  │                       │                  │
  │  "Çalıştır│                  │                       │                  │
  ├──────────▶│  POST /api/      │                       │                  │
  │           │  runner/run      │                       │                  │
  │           ├─────────────────▶│ pytest çalıştırır     │                  │
  │           │◀─────────────────│ Allure raporu döner   │                  │
```

---

## Adım Adım: Girdi → Çıktı → Bağlantı

### Adım 1 — Manuel Test Oluşturma

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/manual-tests` |
| **Route Dosyası** | `engine/routes/manual_routes.py:14` |
| **Girdi** | `{ "title": "Login testi" }` |
| **Çıktı** | `{ "ok": true }` — DB'ye `manual_tests` tablosuna yazar |
| **Sonraki adıma bağlı?** | ❌ Hayır — otomatik tetik yok |

### Adım 2 — Adım Ekleme

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/manual-tests/{id}/steps` |
| **Route Dosyası** | `engine/routes/manual_routes.py:34` |
| **Girdi** | `{ "action": "Kullanıcı login butonuna tıklar", "expected": "Anasayfa görünür" }` |
| **Çıktı** | `{ "ok": true }` — `manual_test_steps` tablosuna yazar |
| **Sonraki adıma bağlı?** | ❌ Hayır |

### Adım 3 — AI → Gherkin Çevirisi

| Alan | Değer |
|------|-------|
| **Endpoint (yeni)** | `POST /api/pipeline/manual-to-automation` |
| **Route Dosyası** | `engine/routes/pipeline_routes.py` ← **YENİ YAZILDI** |
| **Eskisi** | `POST /api/ai/generate-bdd` (`ai_generation_routes.py:59`) — bağımsız, test_id almıyor |
| **Girdi** | `{ "test_id": 1, "target_url": "https://...", "framework": "playwright" }` |
| **Çıktı** | `{ "gherkin": "...", "playwright_code": "...", "feature_path": "..." }` |
| **Sonraki adıma bağlı?** | ✅ Evet — tek request zinciri |

### Adım 4 — Locator Tespiti (Opsiyonel, url verilirse)

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/wizard/discover-selectors` |
| **Route Dosyası** | `engine/routes/wizard_routes.py` |
| **Girdi** | `{ "url": "https://...", "project_name": "test" }` |
| **Çıktı** | CSS/XPath selector listesi |
| **Pipeline içinde?** | ✅ `pipeline_routes.py` target_url verilirse çağırır |

### Adım 5 — Playwright Kodu Üretimi

| Alan | Değer |
|------|-------|
| **Fonksiyon** | `AIEngine.generate_test_file()` |
| **Kaynak** | `engine/core/ai_engine.py:133` |
| **Pipeline içinde?** | ✅ `pipeline_routes.py` içinde zincire dahil |

### Adım 6 — Çalıştırma

| Alan | Değer |
|------|-------|
| **Endpoint** | `POST /api/runner/run-feature` (mevcut runner_routes.py) |
| **Girdi** | `{ "feature_path": "...", "project_id": "..." }` |
| **Çıktı** | Test sonuçları + Allure raporu |
| **Sonraki adıma bağlı?** | ✅ Frontend "Çalıştır" butonu tetikler |

---

## Kopuk Noktalar (Analiz Sonucu)

### ❌ KOPUKlar — Bu commit'te kapatıldı:

1. **Manuel test → BDD otomatik geçiş yoktu**
   - Eskisi: `POST /api/manual-tests` kaydeder, durur. Gherkin için ayrı istek gerekiyordu.
   - Şimdi: `POST /api/pipeline/manual-to-automation` tek request ile zinciri çalıştırıyor.

2. **`generate-bdd` endpoint'i `test_id` almıyordu**
   - Eskisi: `POST /api/ai/generate-bdd` doğal dil alıyor, DB'ye bağlı değil.
   - Şimdi: pipeline endpoint `test_id` ile DB'den adımları çekiyor.

3. **Frontend'de dedicated sayfa yoktu**
   - `wizard/page.tsx` var ama project-scoped, 7 adımlı, karmaşık.
   - Şimdi: `/p/[projectId]/manual-to-automation/page.tsx` eklendi — sade form + sonuç.

### ⚠️ HÂLÂ MANUEL olanlar:

1. **Target URL gerektirir** — URL verilmezse locator tespiti atlanır, sadece metin bazlı Gherkin üretilir.
2. **Playwright çalıştırma** — Kod üretildikten sonra "Çalıştır" butonuna kullanıcı tıklamalı (otomatik çalışmıyor).
3. **Allure raporu görüntüleme** — Çalışma sonrası Allure raporu ayrı sayfada açılıyor.
4. **Step definition eksikler** — Gherkin yeni adımlar içeriyorsa manuel step definition yazılması gerekebilir.

---

## Mevcut Dosya Haritası

```
engine/
├── routes/
│   ├── manual_routes.py         ← Manuel test CRUD
│   ├── ai_generation_routes.py  ← /api/ai/generate-bdd (bağımsız)
│   ├── wizard_routes.py         ← Tam wizard pipeline (URL bazlı)
│   ├── runner_routes.py         ← Test çalıştırma
│   ├── pipeline_routes.py       ← ✨ YENİ — orchestration zinciri
│   └── ...
├── core/
│   ├── ai_engine.py             ← generate_gherkin(), generate_test_file()
│   ├── ai_bdd/scenario_generator.py ← BDD üretimi
│   └── ...
└── app.py                       ← pipeline_bp register edildi

apps/web/app/(dashboard)/p/[projectId]/
├── manual-to-automation/
│   └── page.tsx                 ← ✨ YENİ — dedike UI sayfası
└── wizard/page.tsx              ← Mevcut (7 adımlı wizard)
```

---

## Yeni Endpoint Özeti

### `POST /api/pipeline/manual-to-automation`

**İstek:**
```json
{
  "test_id": 1,           // manuel_tests tablosundaki ID (zorunlu)
  "target_url": "https://example.com",  // opsiyonel — locator tespiti için
  "framework": "playwright"  // playwright (default) | selenium
}
```

**Yanıt:**
```json
{
  "ok": true,
  "test_title": "Login Testi",
  "steps_count": 3,
  "gherkin": "Feature: Login Testi\n  Scenario: ...",
  "playwright_code": "import pytest\nfrom playwright...",
  "feature_path": "engine/features/generated/login_testi_20260409.feature",
  "locators": {...},   // target_url verilmişse
  "model": "gpt-4"
}
```
