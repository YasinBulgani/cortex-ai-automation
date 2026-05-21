# BGTS_Test_Donusum — Kapsamlı Birleştirme Mimari Planı
> Mimar Ajan Analizi — 2026-04-06

## ÖZET: Gerçek Durum

Tüm projeler derinlemesine diff analizi ile incelendi. Sonuç:

> **Paribu, NexusQATestOtomasyon ve Aday Degerlendirme projelerinin büyük çoğunluğu ZATEN BGTS içine taşınmış durumda.**

Gerçekte kalan iş, büyük bir birleştirme değil — **ince fark giderme ve konsolidasyondur.**

---

## 1. Diff Analizi Sonuçları

### Paribu → frameworks/playwright-cucumber-ts/

| Dosya | Durum |
|-------|-------|
| `BasePage.ts` | BGTS'de AYNI |
| `MarketsPage.ts` | BGTS'de AYNI |
| `ParibuHomePage.ts` | BGTS'de AYNI |
| `CryptocurrencyDetailPage.ts` | BGTS'de AYNI |
| `LoginPage.ts` | BGTS'de AYNI |
| `web.steps.ts` | BGTS'de AYNI (iki kopyası var — `web.steps.ts` ve `web-steps.ts`) |
| `api.steps.ts` | BGTS'de AYNI |
| `hooks.ts` | BGTS'de AYNI |
| `LLMClient.ts` | BGTS'de AYNI (ama iki yerde kopyalanmış — duplikasyon borcu var) |
| `TestGeneratorAI.ts` | BGTS'de AYNI |
| `aday_analizi/` | `tools/aday-analizi/` ile AYNI |
| `ApiClient.ts` | **BGTS'de YOK → Eklenecek** |
| `CustomErrors.ts` | **BGTS'de YOK → Eklenecek** |
| `DummyJsonApi.ts` | **BGTS'de YOK → Eklenecek** |
| `Logger.ts` | **BGTS'de YOK → Eklenecek** |
| `test-data/api-credentials.json` | **BGTS'de YOK → Eklenecek (.gitignore'a)** |
| `test-data/api-endpoints.json` | **BGTS'de YOK → Eklenecek** |
| `test-data/web-selectors.json` | **BGTS'de YOK → Eklenecek** |

### NexusQATestOtomasyon → frameworks/selenium-cucumber-java/

| Dosya | Durum |
|-------|-------|
| 13 `methods/*.java` | BGTS'de AYNI |
| 15 `stepdefinitions/*.java` | BGTS'de AYNI |
| 15 `utilities/*.java` | BGTS'de AYNI |
| `TestRunner.java` | BGTS'de AYNI |
| `MultiDomainCucumberRunner.java` | **BGTS DAHA İYİ** (`ConfigReader.getDefaultDomain()` vs hardcoded `"girit"`) |
| `pom.xml` | **BGTS DAHA GELİŞMİŞ** |
| `absence.feature` | **BGTS DAHA KAPSAMLI** (290 vs 231 satır) |
| `advance.feature` | **BGTS DAHA KAPSAMLI** (99 vs 82 satır) |
| 7 ek `.feature` dosyası | Sadece BGTS'de (approval, dashboard, document, expense, login, profile, security) |
| `locators/*.json` (3 dosya) | **BGTS'de YOK → Eklenecek** |
| `allure-report-*/` (6 klasör) | **BGTS'de YOK → reports/allure/nexusqa/ altına (opsiyonel)** |

### Aday Degerlendirme → tools/aday-degerlendirme/

| Dosya | Durum |
|-------|-------|
| 7 Java kaynak dosyası | `tools/aday-degerlendirme/src/` ile AYNI |
| `data/` klasörü | BGTS'de MEVCUT |
| `*.class` derleme çıktıları | **Git'e eklenmiş → .gitignore'a alınacak** |
| Maven/Gradle build dosyası | **YOK → Oluşturulacak** |

---

## 2. Nihai Klasör Mimarisi

```
BGTS_Test_Donusum/
│
├── frameworks/
│   ├── playwright-cucumber-ts/                    [TAMAMLANMIŞ]
│   │   ├── config/
│   │   │   ├── config.ts                          [MEVCUT]
│   │   │   ├── constants.ts                       [MEVCUT + Paribu sabitleri eklenecek]
│   │   │   └── index.ts                           [MEVCUT]
│   │   ├── pages/                                 [TÜM SAYFALAR MEVCUT]
│   │   ├── features/                              [MEVCUT]
│   │   ├── steps/
│   │   │   ├── (tüm mevcut steps)                 [MEVCUT]
│   │   │   └── web.steps.ts                       [SİLİNECEK — web-steps.ts ile aynı]
│   │   ├── utils/
│   │   │   ├── (tüm mevcut utils)                 [MEVCUT]
│   │   │   ├── ApiClient.ts                       [← Paribu'dan eklenecek]
│   │   │   ├── CustomErrors.ts                    [← Paribu'dan eklenecek]
│   │   │   ├── DummyJsonApi.ts                    [← Paribu'dan eklenecek]
│   │   │   ├── Logger.ts                          [← Paribu'dan eklenecek]
│   │   │   └── LLMClient.ts                       [SİLİNECEK — ai-engine'e taşınacak]
│   │   └── test-data/
│   │       ├── api-credentials.json               [← Paribu'dan (.gitignore'a)]
│   │       ├── api-endpoints.json                 [← Paribu'dan]
│   │       └── web-selectors.json                 [← Paribu'dan]
│   │
│   └── selenium-cucumber-java/                    [NEREDEYSE TAMAMLANMIŞ]
│       └── src/
│           ├── main/java/                         [MEVCUT]
│           └── test/
│               ├── java/                          [MEVCUT]
│               └── resources/
│                   ├── features/                  [BGTS versiyonu daha kapsamlı — KORUNUR]
│                   ├── locators/
│                   │   ├── (mevcut locators)      [MEVCUT]
│                   │   ├── absence.json           [← NexusQA'dan eklenecek]
│                   │   ├── advance.json           [← NexusQA'dan eklenecek]
│                   │   └── login.json             [← NexusQA'dan eklenecek]
│                   └── testFile/                  [KONTROL GEREKLI]
│
├── ai-engine/
│   └── src/shared/utils/
│       └── LLMClient.ts                           [TEK KANONİK KAYNAK — burası kalır]
│
├── tools/
│   ├── aday-analizi/                              [MEVCUT — Paribu ile aynı]
│   └── aday-degerlendirme/
│       ├── src/                                   [MEVCUT — IdeaProjects ile aynı]
│       ├── data/                                  [MEVCUT — .class'lar gitignore'a]
│       └── pom.xml                                [← OLUŞTURULACAK]
│
└── reports/
    └── allure/
        └── nexusqa/                              [← NexusQA raporları (opsiyonel, git dışı)]
            ├── ark/
            ├── ghz/
            ├── girit/
            ├── hrnexusqa/
            ├── pex/
            └── plus/
```

---

## 3. Kritik Karar Noktaları

### Karar 1: LLMClient Canonical Kaynak

**Problem:** `LLMClient.ts` hem `frameworks/playwright-cucumber-ts/utils/` hem de `ai-engine/src/shared/utils/` altında birebir aynı içerikle kopyalanmış. Teknik borç oluşturuyor.

**Karar:** `ai-engine/src/shared/utils/LLMClient.ts` **TEK KAYNAK** olur.
`frameworks/playwright-cucumber-ts/utils/LLMClient.ts` kaldırılır, import path güncellenir.

```json
// frameworks/playwright-cucumber-ts/package.json
"dependencies": {
  "ai-engine": "file:../../ai-engine"
}
```

### Karar 2: NexusQA Locator Yolu

**Problem:** NexusQA locators `src/main/resources/locators/` yolunu kullanıyor, BGTS `src/test/resources/locators/` kullanıyor.

**Karar:** BGTS'nin mevcut yolunu (`src/test/resources/locators/`) koru. `LocatorManager.java`'yı buna göre kontrol et.

### Karar 3: NexusQA Allure Raporları

**Karar:** `.gitignore`'a al, sadece CI/CD artifact olarak sakla. Repo boyutu gereksiz şişmesin.

---

## 4. Migration Planı (Öncelikli Sıra)

### FAZ 0 — Branch & Doğrulama (0.5 gün) [ÖNCE YAPILMALI]

```bash
git checkout -b feature/final-merge
```

- NexusQA locator dosyalarının BGTS'de olmadığını doğrula
- `tools/aday-degerlendirme/src/` içindeki `.class` dosyalarını `.gitignore`'a ekle
- Mevcut `web.steps.ts` / `web-steps.ts` duplikasyonunu belgele

### FAZ 1 — TypeScript Konsolidasyonu (1 gün)

**Adım 1.1** — LLMClient duplikasyonu gider:
```bash
# frameworks/playwright-cucumber-ts/utils/LLMClient.ts kaldır
# import path'leri ai-engine'e güncelle
```

**Adım 1.2** — Paribu'dan eksik utils ekle:
```bash
cp ~/Paribu/utils/ApiClient.ts frameworks/playwright-cucumber-ts/utils/
cp ~/Paribu/utils/CustomErrors.ts frameworks/playwright-cucumber-ts/utils/
cp ~/Paribu/utils/DummyJsonApi.ts frameworks/playwright-cucumber-ts/utils/
cp ~/Paribu/utils/Logger.ts frameworks/playwright-cucumber-ts/utils/
```

**Adım 1.3** — test-data ekle:
```bash
cp ~/Paribu/test-data/api-endpoints.json frameworks/playwright-cucumber-ts/test-data/
cp ~/Paribu/test-data/web-selectors.json frameworks/playwright-cucumber-ts/test-data/
# api-credentials.json → .gitignore'a ekle, boş şablon kopyala
```

**Adım 1.4** — web.steps.ts duplikasyonunu gider:
```bash
# cucumber.js'i kontrol et, tek referans bırak
rm frameworks/playwright-cucumber-ts/steps/web.steps.ts  # veya web-steps.ts
```

### FAZ 2 — Java Framework Tamamlama (0.5 gün)

**Adım 2.1** — NexusQA locator JSON'larını ekle:
```bash
cp ~/Downloads/NexusQATestOtomasyon/src/main/resources/locators/absence.json \
   frameworks/selenium-cucumber-java/src/test/resources/locators/
cp ~/Downloads/NexusQATestOtomasyon/src/main/resources/locators/advance.json \
   frameworks/selenium-cucumber-java/src/test/resources/locators/
cp ~/Downloads/NexusQATestOtomasyon/src/main/resources/locators/login.json \
   frameworks/selenium-cucumber-java/src/test/resources/locators/
```

**Adım 2.2** — Build doğrula:
```bash
cd frameworks/selenium-cucumber-java && mvn test -Ddomains=girit
```

### FAZ 3 — Aday Degerlendirme Build Yapılandırması (0.5 gün)

**Adım 3.1** — Maven pom.xml oluştur (`tools/aday-degerlendirme/`):
- Main class: `Main`
- Java version: 17
- ffmpeg sistem bağımlılığı dokümante et

**Adım 3.2** — .gitignore güncelle:
```
tools/aday-degerlendirme/src/**/*.class
tools/aday-degerlendirme/data/**/audio/
reports/allure/nexusqa/
```

### FAZ 4 — Entegrasyon Testi (1 gün)

```bash
# TypeScript
cd frameworks/playwright-cucumber-ts && npm test

# Java
cd frameworks/selenium-cucumber-java && mvn test -Ddomains=girit

# ai-engine build
cd ai-engine && npx tsc --noEmit

# Full smoke
make test-smoke
```

---

## 5. Risk Matrisi

| Risk | Seviye | Önlem |
|------|--------|-------|
| `LLMClient.ts` çift kaynak versiyonu sapması | YÜKSEK | FAZ 1 Adım 1.1 ilk yapılacak iş |
| Java locator yolu uyumsuzluğu | YÜKSEK | `LocatorManager.java` yol referansını kontrol et |
| `web.steps.ts` / `web-steps.ts` Cucumber çift kayıt | YÜKSEK | `cucumber.js` glue path kontrol et |
| `constants.ts` BASE_URL çakışması | ORTA | Additive merge, mevcut sabitleri koruyarak ekle |
| `*.class` dosyaları git'te | ORTA | `.gitignore` güncelle, `git rm --cached` |
| Allure raporları repo boyutu şişirmesi | DÜŞÜK | `.gitignore`'a al |
| `api-credentials.json` git'e yüklenmesi | KRİTİK | FAZ 1 Adım 1.3 öncesi `.gitignore` güncelle |

---

## 6. Makefile Eklenecek Komutlar

```makefile
# ─── Framework Testleri ───────────────────────────────────────────────────────
test-paribu:
	cd frameworks/playwright-cucumber-ts && npx cucumber-js --tags @paribu

test-nexusqa:
	cd frameworks/selenium-cucumber-java && mvn test

test-nexusqa-domain:
	cd frameworks/selenium-cucumber-java && mvn test -Ddomains=$(DOMAIN)

# Kullanım: make test-nexusqa-domain DOMAIN=girit

# ─── Araçlar ─────────────────────────────────────────────────────────────────
run-aday-analizi:
	cd tools/aday-analizi && python main.py

run-aday-degerlendirme:
	cd tools/aday-degerlendirme && mvn exec:java -Dexec.mainClass="Main"
```

---

## 7. Tahmini Süre

| Faz | Süre | Notlar |
|-----|------|--------|
| FAZ 0 — Doğrulama | 0.5 gün | Önkoşul |
| FAZ 1 — TypeScript Konsolidasyonu | 1 gün | En kritik faz |
| FAZ 2 — Java Tamamlama | 0.5 gün | Az iş kaldı |
| FAZ 3 — Aday Degerlendirme Build | 0.5 gün | pom.xml yazımı |
| FAZ 4 — Entegrasyon Testi | 1 gün | |
| **TOPLAM** | **~3.5 iş günü** | |

---

*Mimar Ajan çıktısı — BGTS_Test_Donusum proje mimarisi*
