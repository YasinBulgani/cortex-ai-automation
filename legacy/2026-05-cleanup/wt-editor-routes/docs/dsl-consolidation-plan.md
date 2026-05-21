# DSL / Step Definition Konsolidasyon Planı

**Tarih:** 2026-04-17
**Durum:** 🟢 Faz 1 tamamlandı, Faz 2 başlıyor (REVIZE)
**Sorumlu:** Yasin
**Branch:** `feat/dsl-consolidation`

> **⚠️ REVİZYON (2026-04-17, ikinci iterasyon):** Fiziksel dosya taşıma (Faz 1.5-1.7) iptal edildi. Bunun yerine "katalog-first" yaklaşımı benimsendi: step dosyaları mevcut yerlerinde kalır, `packages/dsl/catalog/` **tek referans merkezi** olur ve YAML'de her step'in nerede tanımlı olduğu kaydedilir. Bu yaklaşım CI/config'i kırmadan hedefe ulaştırır.

---

## 1. Amaç

Projedeki tüm test DSL cümlecikleri (step definitions) şu anda **3 farklı dilde** ve **birden fazla konumda** dağılmış durumda. Bu planın hedefi:

1. Duplikatları temizlemek
2. Tüm step tanımlarını tek bir `packages/dsl/` çatısı altında toplamak
3. Diller arası paylaşılan **YAML tabanlı DSL katalogu** oluşturmak
4. Yönetim için CLI + UI araçları sağlamak

---

## 2. Mevcut Durum (Snapshot — 2026-04-17)

| Yer | Teknoloji | Step | Dil | Not |
|---|---|---|---|---|
| `engine/steps/*.py` | Python (pytest-bdd) | 249 | 173 TR + 76 EN | ✅ Tek kopya |
| `backend/tests/bdd/steps/*.py` | Python | (yukarıya dahil) | — | ✅ Tek kopya |
| `frameworks/selenium-cucumber-java/.../stepdefinitions/` | Java (Cucumber JVM) | 47 | 0 TR + 47 EN | ⭐ **Canonical kaynak** |
| `MaviYakaTestOtomasyon/.../stepdefinitions/` | Java | 47 | — | ❌ Birebir duplikat (MD5 eşit) |
| `docs/test-otomasyon/MaviYakaTestOtomasyon/.../stepdefinitions/` | Java | 47 | — | ❌ Birebir duplikat (MD5 eşit) |
| `frameworks/playwright-cucumber-ts/steps/*.ts` | TypeScript (Playwright) | 288 | 0 TR + 288 EN | ⚠️ `web-steps.ts` (8.2KB) ve `web.steps.ts` (11.5KB) farklı içerik |

**Toplam:** 678 step, 502 benzersiz kalıp, 93 `.feature` dosyası bunları kullanıyor.

---

## 3. Hedef Mimari

```
packages/dsl/                           ⭐ TEK MERKEZ
├── README.md                           # Kullanım kılavuzu
├── CATALOG.md                          # Tüm cümleciklerin tam listesi
├── catalog/                            # YAML sözlük (Faz 2)
│   ├── ui-actions.yaml
│   ├── api-actions.yaml
│   ├── assertions.yaml
│   └── bgts-domain.yaml
├── schema/
│   └── action.schema.json              # Katalog validation şeması
├── python/
│   ├── __init__.py
│   ├── conftest.py
│   ├── ui/
│   ├── api/
│   ├── bgts/
│   └── common/
├── java/
│   └── src/main/java/com/bgts/stepdefinitions/
└── typescript/
    ├── package.json
    ├── tsconfig.json
    └── steps/
```

---

## 4. Uygulama Fazları

### 🔹 FAZ 1 — Duplikat Temizliği (TAMAMLANDI)

| # | Adım | Risk | Durum |
|---|---|---|---|
| 1.1 | `feat/dsl-consolidation` branch'i | Sıfır | ✅ |
| 1.2 | Java stepdefinitions duplikatları sil (30 dosya) | Düşük | ✅ |
| 1.3-1.7 | ~~Fiziksel dosya taşıma~~ | — | ❌ İPTAL (Faz 2 katalog onu replace ediyor) |
| 1.8-1.10 | ~~Config güncelleme, sanity test, commit~~ | — | ❌ İPTAL |

### 🔹 FAZ 2 — Sözlük Katmanı (2-3 gün, orta risk)

YAML tabanlı cross-language catalog. Her step'in TR/EN alias'ları + her dildeki implementasyon referansı.

**Örnek YAML girişi:**
```yaml
# catalog/ui-actions.yaml
- id: click_button
  aliases:
    tr: ["{text} butonuna tıklar", "{text} düğmesine basar"]
    en: ["user clicks {text} button"]
  implementations:
    python: "click_steps.click_button"
    java:   "com.bgts.ClickSteps.clickButton"
    ts:     "webSteps.clickButton"
  tags: [ui, click]
  since: "2026-04-17"
```

| # | Adım |
|---|---|
| 2.1 | YAML şeması + JSON Schema validation |
| 2.2 | Otomatik ekstraktor script (mevcut 678 step → YAML) |
| 2.3 | Manuel rötuş (alias eşleştirme, duplikat birleştirme) |
| 2.4 | `catalog_loader.py` (Python) |
| 2.5 | `catalogLoader.ts` (TypeScript) |
| 2.6 | `CatalogLoader.java` (Java) |
| 2.7 | 5-10 step pilot migration |
| 2.8 | `README.md` — "cümlecik nasıl eklenir" |
| 2.9 | BGTEST Wizard UI'ını katalogla bağla |

### 🔹 FAZ 3 — Yönetim Araçları (1 gün, opsiyonel)

| # | Adım |
|---|---|
| 3.1 | CLI: `bgts dsl list` |
| 3.2 | CLI: `bgts dsl add --tr "..." --en "..."` |
| 3.3 | CLI: `bgts dsl validate` (ölü step tespiti) |
| 3.4 | Pre-commit hook — yeni `@given/@when/@then` eklendiğinde katalog uyarısı |
| 3.5 | UI: `/p/[projectId]/dsl-catalog` görsel sözlük sayfası |

---

## 5. Değişecek Kritik Yapılandırma Dosyaları

| Dosya | Güncelleme |
|---|---|
| `pytest.ini` (root) | `bdd_features_base_dir`, step paths |
| `engine/conftest.py` | step_def_paths |
| `backend/tests/bdd/conftest.py` | `packages.dsl.python.api` import |
| `frameworks/selenium-cucumber-java/pom.xml` | `<glue>com.bgts.stepdefinitions</glue>`, testSourceDirectory |
| `frameworks/playwright-cucumber-ts/cucumber.js` | `require: ['../../packages/dsl/typescript/steps/**/*.ts']` |

---

## 6. Riskler

| Risk | Etki | Hafifletme |
|---|---|---|
| Feature'lar step bulamaz | Yüksek | Her adımda sanity test, küçük commit'ler |
| `web-steps.ts` merge'te step kaybı | Orta | Diff alıp iki dosyayı yan yana incele |
| Java `pom.xml` glue path CI kırar | Orta | CI yeşil olmadan merge yok |
| Git history kaybı | Orta | `git mv` kullan, `cp+rm` asla |
| Feature dosyalarında file-path referansı | Yüksek | Taşıma öncesi grep et |

---

## 7. Dil Stratejisi Kararı

**Seçilen:** Çift dil destekli katalog — TR birincil tutulmaz, EN birincil tutulmaz; her ikisini de alias olarak destekleyecek şekilde YAML tasarlanır. Kullanım anında kullanıcı hangi dili tercih ederse kullanabilir.

---

## 8. Başarı Kriterleri

- [ ] `find . -name "*Steps.java" -not -path "*/packages/*"` sıfır sonuç döndürmeli (Java tek yerde)
- [ ] `find engine backend frameworks -name "*steps*.py" -o -name "*.steps.ts"` sıfır sonuç (her şey packages/dsl altında)
- [ ] 93 `.feature` dosyası eski gibi çalışmaya devam etmeli (sanity test)
- [ ] `packages/dsl/catalog/*.yaml` Faz 2 sonunda 502 benzersiz kalıbı içermeli
- [ ] CI her 3 framework'ü yeşil geçmeli

---

## 9. Takip

Bu plana karşılık gelen TODO listesi agent session'da tutuluyor. Faz ilerledikçe bu dosya güncellenir.
