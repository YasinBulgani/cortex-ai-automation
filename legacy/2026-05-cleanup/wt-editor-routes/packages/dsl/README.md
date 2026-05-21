# TestwrightAI DSL — Test Cümlecikleri Merkezi Sözlüğü

> Projedeki tüm test DSL'i (Gherkin step definitions + yardımcı cümlecikler) için **tek kaynaklı (single source of truth) referans merkezi**.

## 📌 Amaç

TestwrightAI projesi 3 farklı test framework'ü kullanıyor:
- 🐍 **Python** — pytest-bdd / behave (`engine/steps/`, `backend/tests/bdd/steps/`)
- ☕ **Java** — Cucumber JVM + Selenium (`frameworks/selenium-cucumber-java/`)
- 📘 **TypeScript** — Playwright + Cucumber (`frameworks/playwright-cucumber-ts/steps/`)

Her biri kendi step tanımlarını ayrı yerlerde tutuyor. Bu da:
- Aynı eylemin her dilde ayrı ayrı tanımlanmasına
- "Çift tıklanır", "sağ tıklar" gibi eksik aksiyonların fark edilememesine
- TR/EN DSL tutarsızlıklarına
- Otomasyon yazarken "hangi cümleciği kullanabilirim" sorusunun cevapsız kalmasına

neden oluyordu.

**Bu klasör bunu çözer.** Step dosyaları yerlerinde kalıyor; bu klasördeki **YAML katalog** onlara işaret ediyor. Böylece:

✅ Tek sözlük (TR + EN alias, implementation path, tags)
✅ CI/runner kırılmadan geçiş  
✅ AI/UI (BGTEST Wizard) kataloğu okuyup öneri sunabiliyor  
✅ Yeni cümlecik eklemek = YAML'e bir satır  
✅ "Hangi eylemler var?" sorusuna tek sayfalık cevap

## 🗂️ Klasör Yapısı

```
packages/dsl/
├── README.md                           # (bu dosya)
├── catalog/                            # ⭐ ANA KATALOG (YAML sözlükler)
│   ├── ui-actions.yaml                 # click, type, select, hover, scroll vb.
│   ├── api-actions.yaml                # HTTP request/response cümlecikleri
│   ├── assertions.yaml                 # should/olmalı/görünür vb.
│   └── bgts-domain.yaml                # Domain-specific (onay, proje, senaryo)
├── schema/
│   └── action.schema.json              # YAML katalog validation (JSON Schema)
├── scripts/
│   ├── extract_steps.py                # Mevcut step'lerden YAML üret
│   ├── validate_catalog.py             # Katalog tutarlılık kontrolü
│   └── generate_cheatsheet.py          # Markdown cheatsheet üretir
└── loaders/                            # Her framework için katalog okuyucular
    ├── python/
    │   └── catalog_loader.py           # pytest-bdd için @given/@when/@then kaydet
    ├── typescript/
    │   └── catalogLoader.ts            # cucumber-js için
    └── java/
        └── CatalogLoader.java          # Cucumber JVM için
```

## 📝 YAML Katalog Formatı

Her cümlecik şu formatla tanımlanır:

```yaml
- id: click_button                      # benzersiz ID (snake_case)
  category: ui.click                    # kategori hiyerarşisi
  description: "Bir butona tıklar"
  aliases:
    tr:
      - "{text} butonuna tıklar"
      - "{text} butonuna tıklanır"
      - "{text} düğmesine basar"
    en:
      - "user clicks {text} button"
      - "the user clicks on {text} button"
  parameters:
    - name: text
      type: string
      description: "Buton üzerindeki metin"
      required: true
  implementations:
    python:
      module: "engine.steps.click_steps"
      function: "click_on_button"
      source_file: "engine/steps/click_steps.py"
    java:
      class: "stepdefinitions.ClickSteps"
      method: "clickOnButton"
      source_file: "frameworks/selenium-cucumber-java/src/test/java/stepdefinitions/ClickSteps.java"
    typescript:
      module: "web-steps"
      function: "clickButton"
      source_file: "frameworks/playwright-cucumber-ts/steps/web-steps.ts"
  tags: [ui, click, basic]
  since: "2026-04-17"
  examples:
    - |
      Given kullanıcı giriş sayfasında
      When "Login" butonuna tıklar
      Then ana sayfa açılmalıdır
```

## 🚀 Hızlı Kullanım

### Mevcut cümlecikleri listele
```bash
python3 packages/dsl/scripts/extract_steps.py --list
```

### Yeni cümlecik ekle (manuel)
1. İlgili `catalog/*.yaml` dosyasını aç
2. Yukarıdaki formatla yeni girdi ekle
3. `python3 packages/dsl/scripts/validate_catalog.py` ile kontrol et
4. Step implementation'ını mevcut step dosyasına ekle
5. `implementations.<lang>.source_file` alanını gerçek yolu göster

### Katalog'u feature yazarken kullanma
BGTEST Wizard UI'da `/p/[projectId]/dsl-catalog` sayfasına gelin, aramak istediğiniz eylemi yazın, alias'ları kopyalayın.

## 📊 İstatistikler (2026-04-17)

| Kategori | Cümlecik Adedi |
|---|---|
| Toplam step (3 framework) | 678 |
| Benzersiz kalıp | ~502 |
| Türkçe alias'lı step | 173 |
| İngilizce alias'lı step | 505 |
| Feature dosyası (step kullanan) | 93 |

## ⚠️ Önemli Notlar

- **Bu klasör step'i ÇALIŞTIRMAZ.** Sadece onları indeksler. Step'ler yine kendi framework klasörlerinde kalır ve orada çalışır.
- **YAML'de olan ama kodda olmayan** step = eksik implementasyon (validation script uyarır)
- **Kodda olan ama YAML'de olmayan** step = henüz kataloga eklenmemiş (extract_steps ile yakalanır)
- Yeni bir step eklediğinizde **hem kodu hem YAML'i güncelleyin** (pre-commit hook ileride zorunlu kılacak)

## 🤖 AI Destekli Arama (Ollama + bge-m3)

DSL Sözlüğü sayfasında **"AI" modu** açılınca, kullanıcının doğal dilde
yazdığı istek (TR veya EN) anlamsal olarak aranır ve en yakın cümlecikleri
skorla listeler. Motor:

```
UI (AI toggle)
  └─ POST /api/v1/dsl/suggest { description, mode: "auto" }
       └─ backend: hybrid_search (lexical×0.35 + semantic×0.65)
            └─ POST /ai/embed  →  Ollama /api/embeddings (bge-m3)

UI (👍 / 👎 butonu)
  └─ POST /api/v1/dsl/feedback  →  sd_dsl_feedback tablosu
       └─ sonraki aramalar: aynı query için ±0.15 skor bonusu
```

Hızlı kurulum:

```bash
make dsl-ai-warm                     # ollama pull bge-m3 + ısıtma
cd backend && alembic upgrade head   # feedback + proposal tabloları
# admin token al
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r .access_token)
make dsl-ai-rebuild DSL_AI_TOKEN=$TOKEN
# /dsl-catalog aç, arama modunu 🤖 AI'ya al
```

Arama modları (`POST /api/v1/dsl/suggest`):

- `auto` — index varsa hybrid, yoksa lexical'e düşer
- `lexical` — token bazlı (AI gereksiz)
- `hybrid` — lexical + semantic ağırlıklı birleşim
- `semantic` — yalnızca embedding cosine

## ✏️ UI'dan Düzenleme + Git Entegrasyonu

`/dsl-catalog/editor/new` ve `/dsl-catalog/editor/<id>` sayfaları katalog
cümleciklerini tarayıcıdan oluşturur/günceller/siler/deprecate eder.
Değişiklikler doğrudan `packages/dsl/catalog/*.yaml`'a yazılır — `ruamel.yaml`
ile round-trip olduğu için yorumlar ve anahtar sırası korunur.

Üç kaydetme modu:

| Mod | Açıklama | Kime uygun |
|---|---|---|
| `direct_commit` | Aktif branch'e commit (+ opsiyonel push) | Küçük takım, trunk-based |
| `pr`            | `dsl/edit-<slug>` branch'i + GitHub/Gitea PR | Review süreci olan takımlar |
| `review`        | YAML yazılmaz, **pending proposal** oluşur — admin `/dsl-catalog/review`'da onaylar | AI aday önerileri, dış katkı |

Yetki:

- `dsl.edit` permission'lı kullanıcı: create/update/delete/deprecate.
- `dsl.approve` permission'lı kullanıcı: pending proposal'ı approve/reject.
- Admin rolü `admin.*` ile her iki yetkiye de sahiptir.

Tüm değişiklikler `sd_dsl_edit_proposals` tablosuna, başarılı merge'ler
`sd_dsl_catalog_audit` tablosuna düşer — forensics & rollback için kalıcı
kayıt.

Örnek config (`.env`):

```bash
DSL_GIT_ENABLED=true
DSL_GIT_MODE=pr                 # pull request akışı
DSL_GIT_PROVIDER=github
DSL_GIT_GITHUB_REPO=YasinBulgani/BGTS-Test-Donusum
GITHUB_TOKEN=ghp_xxx            # contents:write + pull_requests:write
DSL_GIT_REVIEWERS=yasin_bulgan  # virgülle ayrılmış GitHub kullanıcı adları
```

Hızlı komutlar:

```bash
make dsl-editor-config DSL_AI_TOKEN=$TOKEN   # aktif git/mode/provider yazdır
make dsl-proposals DSL_AI_TOKEN=$TOKEN       # pending önerileri listele
```

## 🔄 İlerleme Takibi

Detaylı plan ve ilerleme: [`docs/dsl-consolidation-plan.md`](../../docs/dsl-consolidation-plan.md)
