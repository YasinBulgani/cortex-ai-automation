# BGTS Test Dönüşüm — Tüm Projeleri Birleştirme Planı & Analizi

**Tarih:** 2026-04-06
**Kapsam:** Paribu, NexusQATestOtomasyon, Aday Degerlendirme → Cortex_Ai_Automation

---

## 1. MEVCUT PROJE ENVANTERİ

### 1.1 Birleştirilecek Projeler

| Proje | Konum | Dil | Framework | Test Türü | Durum |
|-------|-------|-----|-----------|-----------|-------|
| **Paribu** | `~/Paribu/` | TypeScript | Playwright + Cucumber | Web + API | Aktif |
| **NexusQATestOtomasyon** | `~/Downloads/` | Java | Selenium + Cucumber | Web UI | Aktif |
| **Aday Degerlendirme** | `~/IdeaProjects/` | Java | Custom | Ses Kaydı + LLM | Aktif |
| ~~Case_Paribu~~ | `~/Case_Paribu/` | — | — | — | Boş (skip) |
| ~~Ai Testing~~ | `~/IdeaProjects/` | Java | — | — | Boş (skip) |
| ~~otomasyon-ekibi~~ | `~/otomasyon-ekibi/` | Python | — | — | Boş (skip) |
| ~~test-automation~~ | `~/test-automation/` | — | — | — | Boş (skip) |

### 1.2 BGTS'de Zaten Var Olanlar

| Mevcut Klasör | İçerik | Durum |
|---------------|--------|-------|
| `frameworks/playwright-cucumber-ts/` | TypeScript Cucumber altyapısı | Var, genişletilecek |
| `frameworks/selenium-cucumber-java/` | Java Selenium altyapısı | Var, genişletilecek |
| `tools/aday-analizi/` | Python aday analiz aracı | Var |
| `tools/aday-degerlendirme/` | Aday değerlendirme | Var, Java versiyonu eklenecek |
| `engine/features/` | BDD Gherkin senaryoları | Var, Paribu feature'ları eklenecek |
| `engine/pages/` | Python Page Objects | Var, TypeScript POM ayrı kalacak |

---

## 2. DETAYLI PROJE ANALİZİ

### 2.1 Paribu Projesi

**Teknoloji Stack:**
- TypeScript 5.3.3 / Node.js 18+
- Playwright 1.40.0 + Cucumber 10.0.0
- OpenAI 4.20.0 entegrasyonu
- Cucumber HTML Reporter

**İçerik Envanteri:**

| Klasör/Dosya | İçerik | BGTS'deki Hedef |
|---|---|---|
| `pages/ParibuHomePage.ts` | Paribu ana sayfa POM | `frameworks/playwright-cucumber-ts/pages/` |
| `pages/MarketsPage.ts` | Markets POM | `frameworks/playwright-cucumber-ts/pages/` |
| `pages/CryptocurrencyDetailPage.ts` | Kripto detay POM | `frameworks/playwright-cucumber-ts/pages/` |
| `pages/LoginPage.ts` | Login POM | `frameworks/playwright-cucumber-ts/pages/` |
| `pages/BasePage.ts` | Base POM | `frameworks/playwright-cucumber-ts/pages/` (merge) |
| `features/web_tests.feature` | Web test senaryoları | `frameworks/playwright-cucumber-ts/features/` |
| `features/api_tests.feature` | API test senaryoları | `frameworks/playwright-cucumber-ts/features/` |
| `steps/web.steps.ts` | Web step definitions | `frameworks/playwright-cucumber-ts/steps/` |
| `steps/api.steps.ts` | API step definitions | `frameworks/playwright-cucumber-ts/steps/` |
| `steps/hooks.ts` | Before/After hooks | `frameworks/playwright-cucumber-ts/steps/` (merge) |
| `utils/LLMClient.ts` | OpenAI entegrasyonu | `ai-engine/src/` veya `frameworks/playwright-cucumber-ts/utils/` |
| `utils/TestGeneratorAI.ts` | AI test generator | `ai-engine/src/generation/` |
| `utils/ApiClient.ts` | HTTP client | `frameworks/playwright-cucumber-ts/utils/` |
| `utils/Logger.ts` | Logging | `frameworks/playwright-cucumber-ts/utils/` |
| `utils/TestDataLoader.ts` | Veri yükleyici | `frameworks/playwright-cucumber-ts/utils/` |
| `config/config.ts` | Ortam config | `frameworks/playwright-cucumber-ts/config/` (merge) |
| `config/constants.ts` | Sabitler | `frameworks/playwright-cucumber-ts/config/` |
| `test-data/*.json` | Test verileri | `frameworks/playwright-cucumber-ts/test-data/` |
| `aday_analizi/` | Python modülü | `tools/aday-analizi/` (zaten var, birleştir) |

**Çakışma Analizi:**

| Dosya | BGTS'deki Mevcut | Çözüm |
|-------|-----------------|-------|
| `BasePage.ts` | `frameworks/playwright-cucumber-ts/pages/BasePage.ts` | İki dosyayı karşılaştır, en kapsamlısını koru |
| `hooks.ts` | `frameworks/playwright-cucumber-ts/steps/hooks.ts` | Merge, Paribu hook'larını ekle |
| `config/config.ts` | `frameworks/playwright-cucumber-ts/config/index.ts` | Paribu ortam değişkenlerini ekle |
| `LLMClient.ts` | `ai-engine/src/` içinde benzeri var | `ai-engine/src/shared/` altında birleştir |

---

### 2.2 NexusQATestOtomasyon Projesi

**Teknoloji Stack:**
- Java JDK 21
- Maven build tool
- Selenium WebDriver 4.41.0 + Cucumber 7.15.0
- Allure Reports 2.27.0 + JUnit 4.13.2
- Apache POI (Excel), Log4j2, WebDriverManager

**6 Domain Konfigürasyonu:**

| Domain | Allure Rapor | Muhtemel Uygulama |
|--------|-------------|------------------|
| ark | `allure-report-ark/` | Ark platformu |
| ghz | `allure-report-ghz/` | GHZ platformu |
| girit | `allure-report-girit/` | Girit platformu |
| hrnexusqa | `allure-report-hrnexusqa/` | HR/Mavi Yaka HR |
| pex | `allure-report-pex/` | PEX platformu |
| plus | `allure-report-plus/` | Plus platformu |

**İçerik Envanteri:**

| Klasör/Dosya | İçerik | BGTS'deki Hedef |
|---|---|---|
| `src/test/java/stepdefinitions/` (15 dosya) | Step definitions | `frameworks/selenium-cucumber-java/src/test/java/stepdefinitions/` |
| `src/test/java/runners/` (2 dosya) | Test runners | `frameworks/selenium-cucumber-java/src/test/java/runners/` |
| `src/test/java/utilities/` | Utils | `frameworks/selenium-cucumber-java/src/test/java/utilities/` |
| `src/test/resources/features/` | Feature dosyaları | `frameworks/selenium-cucumber-java/src/test/resources/features/` |
| `allure-report-*/` (6 klasör) | Allure raporları | `reports/allure/nexusqa/` |
| `screenshot/` | Ekran görüntüleri | `reports/screenshots/nexusqa/` |
| `pom.xml` | Maven config | `frameworks/selenium-cucumber-java/pom.xml` (merge) |

**Step Definition Envanteri (15 dosya):**

| Step Dosyası | İşlev |
|---|---|
| ClickSteps | Tıklama aksiyonları |
| CheckboxSteps | Checkbox işlemleri |
| RadioSteps | Radio button işlemleri |
| SelectSteps | Dropdown seçimi |
| ScreenshotSteps | Ekran görüntüsü |
| Hooks | Before/After hooks |
| ScenarioContextSteps | Senaryo context |
| InputSteps | Metin girişi |
| DragDropSteps | Drag & drop |
| AssertionSteps | Doğrulama |
| HoverSteps | Hover aksiyonları |
| WaitSteps | Bekleme |
| NavigationSteps | Sayfa navigasyonu |
| KeyboardSteps | Klavye aksiyonları |
| ScrollSteps | Scroll işlemleri |

**Çakışma Analizi:**

| Bileşen | BGTS'deki Mevcut | Çözüm |
|---------|-----------------|-------|
| `pom.xml` | `frameworks/selenium-cucumber-java/pom.xml` | Dependency'leri merge et |
| Hooks.java | BGTS'de yoksa ekle | Doğrudan kopyala |
| AssertionSteps | BGTS'de benzeri olabilir | Karşılaştır, extend et |

---

### 2.3 Aday Degerlendirme Projesi

**Teknoloji Stack:**
- Java JDK 17+
- ffmpeg (ses kaydı için sistem bağımlılığı)
- OpenAI API (opsiyonel, LlmClient üzerinden)

**İçerik Envanteri (7 Java sınıfı):**

| Sınıf | İşlev | BGTS'deki Hedef |
|-------|-------|-----------------|
| `Main.java` | Giriş noktası | `tools/aday-degerlendirme/java/src/Main.java` |
| `Session.java` | Oturum modeli | `tools/aday-degerlendirme/java/src/Session.java` |
| `SessionManager.java` | Oturum yönetimi | `tools/aday-degerlendirme/java/src/SessionManager.java` |
| `AudioRecording.java` | Ses kaydı modeli | `tools/aday-degerlendirme/java/src/AudioRecording.java` |
| `Recorder.java` | Kayıt interface | `tools/aday-degerlendirme/java/src/Recorder.java` |
| `FfmpegRecorder.java` | ffmpeg implementasyonu | `tools/aday-degerlendirme/java/src/FfmpegRecorder.java` |
| `LlmClient.java` | OpenAI istemcisi | `tools/aday-degerlendirme/java/src/LlmClient.java` |

**Not:** `tools/aday-analizi/` altında zaten Python versiyonu var. Java versiyonu `tools/aday-degerlendirme/java/` altına eklenecek.

---

## 3. HEDEF BGTS PROJE YAPISI (Birleşme Sonrası)

```
Cortex_Ai_Automation/
│
├── frameworks/
│   ├── playwright-cucumber-ts/          # TypeScript BDD Framework
│   │   ├── config/
│   │   │   ├── index.ts                 # MEVCUT + Paribu ortam değişkenleri EKLENECEk
│   │   │   └── constants.ts             # ← Paribu'dan eklenecek
│   │   ├── pages/
│   │   │   ├── BasePage.ts              # MEVCUT (Paribu'dan genişletilecek)
│   │   │   ├── HomePage.ts              # MEVCUT
│   │   │   ├── MarketPage.ts            # MEVCUT
│   │   │   ├── ProfilePage.ts           # MEVCUT
│   │   │   ├── SearchPage.ts            # MEVCUT
│   │   │   ├── ParibuHomePage.ts        # ← Paribu'dan eklenecek
│   │   │   ├── MarketsPage.ts           # ← Paribu'dan eklenecek (MarketPage ile çakışma kontrol)
│   │   │   ├── CryptocurrencyDetailPage.ts  # ← Paribu'dan eklenecek
│   │   │   └── LoginPage.ts             # ← Paribu'dan eklenecek
│   │   ├── features/
│   │   │   ├── (mevcut .feature dosyaları)
│   │   │   ├── paribu_web_tests.feature # ← Paribu'dan eklenecek
│   │   │   └── paribu_api_tests.feature # ← Paribu'dan eklenecek
│   │   ├── steps/
│   │   │   ├── ai-steps.ts              # MEVCUT
│   │   │   ├── common-steps.ts          # MEVCUT
│   │   │   ├── data-steps.ts            # MEVCUT
│   │   │   ├── e2e-steps.ts             # MEVCUT
│   │   │   ├── paribu-steps.ts          # MEVCUT (web + api birleşik)
│   │   │   ├── web-steps.ts             # MEVCUT + Paribu web.steps.ts EKLENECEk
│   │   │   └── hooks.ts                 # MEVCUT + Paribu hooks EKLENECEk
│   │   ├── utils/
│   │   │   ├── A11yTester.ts            # MEVCUT
│   │   │   ├── PerformanceTester.ts     # MEVCUT
│   │   │   ├── TestDataManager.ts       # MEVCUT
│   │   │   ├── TestRecorder.ts          # MEVCUT
│   │   │   ├── VisualRegressionTester.ts # MEVCUT
│   │   │   ├── errors.ts               # MEVCUT
│   │   │   ├── ApiClient.ts             # ← Paribu'dan eklenecek
│   │   │   ├── Logger.ts               # ← Paribu'dan eklenecek
│   │   │   └── TestDataLoader.ts        # ← Paribu'dan eklenecek
│   │   └── test-data/
│   │       ├── api-credentials.json     # ← Paribu'dan (.gitignore'a ekle)
│   │       ├── api-endpoints.json       # ← Paribu'dan
│   │       └── web-selectors.json       # ← Paribu'dan
│   │
│   └── selenium-cucumber-java/          # Java BDD Framework
│       └── src/test/java/
│           ├── stepdefinitions/         # ← NexusQA 15 step dosyası eklenecek
│           │   ├── ClickSteps.java
│           │   ├── CheckboxSteps.java
│           │   ├── RadioSteps.java
│           │   ├── SelectSteps.java
│           │   ├── ScreenshotSteps.java
│           │   ├── ScenarioContextSteps.java
│           │   ├── InputSteps.java
│           │   ├── DragDropSteps.java
│           │   ├── AssertionSteps.java
│           │   ├── HoverSteps.java
│           │   ├── WaitSteps.java
│           │   ├── NavigationSteps.java
│           │   ├── KeyboardSteps.java
│           │   └── ScrollSteps.java
│           ├── runners/                 # ← NexusQA runners eklenecek
│           ├── utilities/               # ← NexusQA utilities eklenecek
│           └── resources/
│               └── features/           # ← NexusQA features eklenecek
│                   ├── advance.feature
│                   └── absence.feature
│
├── ai-engine/
│   └── src/
│       └── shared/
│           ├── LLMClient.ts             # ← Paribu'dan genişletilecek
│           └── TestGeneratorAI.ts       # ← Paribu'dan eklenecek (zaten var mı kontrol)
│
├── tools/
│   ├── aday-analizi/                    # MEVCUT (Python versiyonu)
│   └── aday-degerlendirme/
│       ├── python/                      # MEVCUT
│       └── java/                        # ← YENİ (Aday Degerlendirme Java projesi)
│           └── src/
│               ├── Main.java
│               ├── Session.java
│               ├── SessionManager.java
│               ├── AudioRecording.java
│               ├── Recorder.java
│               ├── FfmpegRecorder.java
│               └── LlmClient.java
│
└── reports/
    └── allure/
        └── nexusqa/                    # ← NexusQATestOtomasyon Allure raporları
            ├── ark/
            ├── ghz/
            ├── girit/
            ├── hrnexusqa/
            ├── pex/
            └── plus/
```

---

## 4. MİGRASYON PLANI (Adım Adım)

### Faz 1 — Hazırlık (1-2 gün)

| # | Görev | Sorumlu | Notlar |
|---|-------|---------|--------|
| 1.1 | Tüm projeleri git'e al (yedek) | DevOps | `git archive` ile zip alınabilir |
| 1.2 | BGTS'de `feature/merge-all` branch aç | Dev | `git checkout -b feature/merge-all` |
| 1.3 | Dependency çakışmalarını belgele | Dev | package.json + pom.xml versiyonları |
| 1.4 | Test ortamını doğrula | QA | Docker up, tüm servisler çalışıyor mu |

### Faz 2 — Paribu Birleştirmesi (2-3 gün)

| # | Görev | Öncelik | Risk |
|---|-------|---------|------|
| 2.1 | `pages/` dosyalarını kopyala | Yüksek | BasePage çakışması |
| 2.2 | `features/` dosyalarını kopyala | Yüksek | Namespace çakışması |
| 2.3 | `steps/web.steps.ts` merge et | Yüksek | Duplicate step tanımları |
| 2.4 | `steps/api.steps.ts` ekle | Orta | — |
| 2.5 | `utils/` dosyalarını ekle | Orta | LLMClient versiyonu |
| 2.6 | `config/constants.ts` ekle | Orta | BASE_URL değişkeni çakışabilir |
| 2.7 | `test-data/` JSON'ları ekle | Düşük | credentials .gitignore'a |
| 2.8 | `aday_analizi/` Python'u merge et | Düşük | tools/aday-analizi ile karşılaştır |
| 2.9 | Paribu testlerini BGTS'de çalıştır | Yüksek | Smoke test |

### Faz 3 — NexusQATestOtomasyon Birleştirmesi (2-3 gün)

| # | Görev | Öncelik | Risk |
|---|-------|---------|------|
| 3.1 | `pom.xml` dependency'lerini merge et | Yüksek | Versiyon çakışması |
| 3.2 | `stepdefinitions/` (15 dosya) kopyala | Yüksek | BGTS'deki mevcut steps ile çakışma |
| 3.3 | `runners/` kopyala | Orta | Test runner config |
| 3.4 | `utilities/` kopyala | Orta | Utility isimleri |
| 3.5 | `features/` dosyalarını ekle | Yüksek | Feature klasör yapısı |
| 3.6 | 6 domain config (ark, ghz, vb.) ekle | Orta | Ayrı config dosyaları oluştur |
| 3.7 | Allure raporlarını `reports/allure/nexusqa/` altına taşı | Düşük | Sadece arşiv |
| 3.8 | Maven build testini çalıştır | Yüksek | `mvn test` başarılı mı |

### Faz 4 — Aday Degerlendirme Birleştirmesi (0.5 gün)

| # | Görev | Öncelik | Risk |
|---|-------|---------|------|
| 4.1 | Java kaynaklarını `tools/aday-degerlendirme/java/src/` altına kopyala | Orta | — |
| 4.2 | README.md oluştur (Java versiyonu için) | Düşük | — |
| 4.3 | ffmpeg bağımlılığını dokümante et | Orta | Sistem bağımlılığı |

### Faz 5 — Entegrasyon & Doğrulama (1-2 gün)

| # | Görev | Öncelik | Risk |
|---|-------|---------|------|
| 5.1 | Tüm framework testlerini çalıştır | Kritik | — |
| 5.2 | Makefile'a yeni test komutları ekle | Orta | — |
| 5.3 | docker-compose'a gerekli servisler ekle (gerekirse) | Orta | Port çakışması |
| 5.4 | README.md güncelle (tüm framework'leri belgele) | Düşük | — |
| 5.5 | PR oluştur, code review | Orta | — |

---

## 5. BAĞIMLILIK & ÇAKIŞMA ANALİZİ

### 5.1 TypeScript / Node.js Çakışmaları

| Paket | Paribu Versiyonu | BGTS Versiyonu | Çözüm |
|-------|-----------------|----------------|-------|
| `@playwright/test` | ^1.40.0 | ^1.49.0 | BGTS (daha yeni) kullan |
| `@cucumber/cucumber` | ^10.0.0 | (kontrol et) | En yüksek minor versiyon |
| `typescript` | ^5.3.3 | ~5.x | Uyumlu |
| `openai` | ^4.20.0 | (ai-engine'de var) | Merkezi LLMClient kullan |

### 5.2 Java / Maven Çakışmaları

| Paket | NexusQA Versiyonu | BGTS Versiyonu | Çözüm |
|-------|--------------------|--------------------|-------|
| `selenium-java` | 4.41.0 | (kontrol et) | En son stable |
| `cucumber-java` | 7.15.0 | (kontrol et) | Senkronize tut |
| `allure-cucumber7-jvm` | 2.27.0 | (kontrol et) | Uyumlu allure versiyonu |
| `junit` | 4.13.2 | (kontrol et) | JUnit 4 veya 5 kararı ver |

### 5.3 Namespace Çakışmaları

| Durum | Dosya | Risk | Çözüm |
|-------|-------|------|-------|
| BasePage.ts çift tanım | Paribu + BGTS | **Yüksek** | BGTS'dekini genişlet, Paribu methodlarını ekle |
| MarketPage vs MarketsPage | İsim farklı | Orta | Paribu'yu `ParibuMarketsPage.ts` olarak ekle |
| config.ts çakışması | Paribu + BGTS config | Orta | BGTS config'ini extend et, Paribu değerlerini ekle |
| LLMClient çift implementasyon | Paribu TS + ai-engine TS | Orta | `ai-engine/src/shared/` altında birleştir |
| hooks.ts | Paribu + BGTS hooks | **Yüksek** | Merge et, çift kayıt olmasın |

---

## 6. RİSK ANALİZİ

### 6.1 Yüksek Riskler

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| Duplicate step tanımları (Cucumber) | Yüksek | Kritik | Tüm step'leri merge öncesi listele, unique isimler ver |
| BasePage metodlarının üzerine yazılması | Orta | Yüksek | Merge öncesi diff al, en kapsamlı versiyonu koru |
| Maven dependency versiyonu çakışması | Orta | Yüksek | `mvn dependency:tree` ile analiz et |
| `api-credentials.json` git'e commit edilmesi | Düşük | Kritik | `.gitignore`'a ekle, secret'ları .env'e taşı |

### 6.2 Orta Riskler

| Risk | Olasılık | Etki | Azaltma |
|------|----------|------|---------|
| Node.js versiyonu uyumsuzluğu | Düşük | Orta | `.nvmrc` dosyası ile sabitle |
| Java JDK versiyonu farklılığı (17 vs 21) | Orta | Orta | Maven compiler plugin ile hedef versiyonu sabitle |
| Allure raporlarının büyük boyutu | Düşük | Düşük | `reports/allure/nexusqa/` altında, git'e commit etme |
| ffmpeg sistem bağımlılığı | Düşük | Orta | Dockerfile'a ekle, dokümante et |

---

## 7. MAKEFİLE GÜNCELLEMELERİ

Birleşme sonrası `Makefile`'a eklenecek komutlar:

```makefile
# ─── Paribu Framework ────────────────────────────────────────────────────────
test-paribu:
    cd frameworks/playwright-cucumber-ts && npx cucumber-js --tags @paribu

test-paribu-web:
    cd frameworks/playwright-cucumber-ts && npx cucumber-js --tags @paribu-web

test-paribu-api:
    cd frameworks/playwright-cucumber-ts && npx cucumber-js --tags @paribu-api

# ─── NexusQA Framework ──────────────────────────────────────────────────────
test-nexusqa:
    cd frameworks/selenium-cucumber-java && mvn test

test-nexusqa-ark:
    cd frameworks/selenium-cucumber-java && mvn test -Dsuite=ark

test-nexusqa-hrnexusqa:
    cd frameworks/selenium-cucumber-java && mvn test -Dsuite=hrnexusqa

# ─── Aday Araçları ───────────────────────────────────────────────────────────
run-aday-analizi:
    cd tools/aday-analizi && python main.py

run-aday-degerlendirme-java:
    cd tools/aday-degerlendirme/java && mvn exec:java -Dexec.mainClass="Main"
```

---

## 8. TAHMINI SÜRE & KAYNAK

| Faz | Süre | Gereksinim |
|-----|------|------------|
| Faz 1 — Hazırlık | 1-2 gün | 1 developer |
| Faz 2 — Paribu | 2-3 gün | 1 developer + 1 QA |
| Faz 3 — NexusQA | 2-3 gün | 1 developer (Java) |
| Faz 4 — Aday Degerlendirme | 0.5 gün | 1 developer |
| Faz 5 — Entegrasyon & Doğrulama | 1-2 gün | Tüm ekip |
| **TOPLAM** | **~7-10 iş günü** | 2-3 kişi |

---

## 9. BAŞARI KRİTERLERİ

- [ ] Tüm Paribu testleri BGTS içinde yeşil çalışıyor
- [ ] NexusQA Maven build başarılı (`BUILD SUCCESS`)
- [ ] Tüm 6 domain (ark, ghz, girit, hrnexusqa, pex, plus) çalışıyor
- [ ] Aday Degerlendirme Java uygulaması BGTS içinde ayağa kalkıyor
- [ ] `make test-smoke` tüm katmanlar için yeşil
- [ ] Hiç duplicate Cucumber step tanımı yok
- [ ] `api-credentials.json` git'te yok, `.gitignore`'da
- [ ] Allure raporları `reports/allure/` altında görünüyor
- [ ] README.md tüm framework'leri belgeliyor

---

## 10. SONRAKI ADIMLAR

1. **Hemen yapılabilir:**
   - Paribu `pages/` klasörünü BGTS'ye kopyala (en az çakışma)
   - NexusQA `allure-report-*/` klasörlerini `reports/allure/nexusqa/` altına taşı
   - Aday Degerlendirme Java kaynaklarını `tools/aday-degerlendirme/java/` altına kopyala

2. **Dikkat gerektiren:**
   - `BasePage.ts` merge (önce diff al)
   - `hooks.ts` merge (duplicate step riski)
   - `pom.xml` dependency merge (Maven tree analizi)

3. **Mimar ajandan beklenenler:**
   - Nihai klasör mimarisi onayı
   - ai-engine entegrasyon noktaları
   - Uzun vadeli ölçeklenebilirlik kararları

---

*Bu döküman, BGTS mimar ajanı tarafından da incelenmekte ve güncellenmektedir.*
