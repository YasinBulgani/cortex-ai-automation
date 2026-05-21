# Changelog

Tüm önemli değişiklikler bu dosyada belgelenir.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · [SemVer](https://semver.org/lang/tr/).

## [Unreleased]

### Neurex_QA entegrasyonu
- Cortex Otomasyon `Neurex_QA/frameworks/cortex-java/` altına kopyalandı
- IntelliJ workspace: 23 run config (9 Cortex + 3 compound + 11 Neurex/diğer)
- Makefile entegrasyonu: `make cortex-{smoke,regression,parallel,debug,record,lint,dashboard,rerun,clean}`
- HTTP Client koleksiyonu (`api-tests/http/`): health, cortex, ai-gateway, web-routes
- IntelliJ Bookmarks (4 grup, 20+ link) + Live Templates + File Templates
- `apps/web/.env.local` `NEXT_PUBLIC_AUTH_MIDDLEWARE_ENABLED=false` (dev'de auth bypass)

### Accessibility (axe-core)
- `playwright.methods.PwAccessibilityMethods` — Deque axe-core 4.10.0 entegrasyonu
- 3 yeni step phrase: WCAG 2.1 AA, no-critical, custom impact level
- `login-accessibility.feature`'a 2 axe senaryosu eklendi

### CI iyileştirme
- GitHub Actions workflow'a Slack notification job'u eklendi (SLACK_WEBHOOK_URL secret)
- Pipeline durumu: build/lint/smoke/regression/dashboard sonrası özet bildirim

### Setup tooling
- `scripts/setup-env.sh`: AES key generator + .env bootstrap (cross-platform)
- `scratch/setup-password.feature`: ilk kurulumda şifreli alias kaydı için one-shot feature
- `docs/recorder-workflow.md`: adım adım Cortex selektör yakalama rehberi

### Hijyen
- `MaviYakaTestOtomasyon/` boş klasörü `legacy/2026-05-cleanup/` altına taşındı
- `password.properties` (yerel) silindi — `setup-env.sh + setup-password feature` ile yeniden üretilir
- LocatorLinter son WARN düzeltildi (`passwordVisibilityToggle` xpath following-sibling → CSS sibling)
- LocatorLinter durumu: **0 ERROR / 0 WARN / 32 INFO**

## [v2.0.0] - 2026-05-20

### Büyük temizlik — Cortex-only + Playwright tek engine
- **HCM-era dead code tamamen silindi**: `src/main/java/{methods,api,drivers}/`, `src/test/java/{stepdefs,runners,api}/`, `utils/{DriverUtil, ScreenshotUtil, ShadowLocator, VariableUtil, HtmlReportAnalyzer, JsonReader, MultiBy, SmartWait}` (Selenium engine emekliye ayrıldı)
- **DbMethods → playwright/methods/PwDbMethods.java**: ThreadLocal-safe DB connection
- **pom.xml v2.0.0**: artifactId `cortex-otomasyon`, Selenium dependency'leri kaldırıldı (Playwright tek engine), Allure dependency eklendi
- **27 file silindi**, proje ~%50 küçüldü

### Profesyonel runner yapısı
- **`runners/CortexRunner.java`**: tek master runner, tag/parallel/raport ayarları `junit-platform.properties`'ten
- **`listeners/RetryListener.java`**: failed.txt rerun hint'i
- **Maven profilleri** (`smoke`, `regression`, `parallel`, `headless`, `debug`, `recorder`)
- **`scripts/cortex` CLI**: tek-komut wrapper (`./scripts/cortex smoke`, `regression`, `parallel`, `tag`, `feature`, `rerun`, `debug`, `record`, `lint`, `report`, `install`, `dashboard`, `clean`)
- **9 IntelliJ Run config**: Smoke, Regression, Parallel (4), Parallel Headless, Debug, Rerun Failed, Recorder (x2), Locator Linter
- **Allure entegrasyonu**: `target/allure-results/` + `mvn allure:serve` ile interactive report
- **Cucumber rerun plugin**: `target/failed.txt` otomatik üretilir

### Eksik dosyalar tamamlandı
- `shared/locators/common.json` (generic locator'lar)
- 6 feature için locator JSON stub'ları (`login-validation.json`, vb.)
- CI workflow'a `CORTEX_USERNAME` + `CORTEX_PASSWORD` env eklendi
- `recorder.properties` İngilizce yorumlara çevrildi
- CONTRIBUTING.md'ye **dil politikası** (Kod EN, Docs TR, Test data TR) eklendi

### Dil politikası
- **Kod İngilizce, dokümantasyon Türkçe, test verisi Türkçe** olarak standardize edildi
- Tüm aktif Java modülleri (recorder/, playwright/, utils/, config/, crypto/, drivers/) — yorumlar, log mesajları ve exception text İngilizce
- Python kod (`flask_api.py`, `launcher.py`, `train_model.py`) İngilizce
- README, CHANGELOG, docs/ Türkçe kalır (takım için)
- Cortex UI string'leri (feature dosyalarında, locator XPath'lerinde) Türkçe kalır (gerçek UI ile eşleşmesi için)

### Eklendi
- **Cortex login senaryoları**: 7 feature dosyası, 39 senaryo (login + validation + security + a11y + forgot-password + session + edge cases)
- **`projects/cortex/locators/common.json`**: ortak locator'lar (cookie banner, header, toast, modal)
- **`projects/cortex/locators/login.json`**: 30+ login locator (multi-fallback)

### Kaldırıldı
- `projects/hcm/`, `projects/trendyol/`, `projects/linkedin/`, `projects/api/` klasörleri — Cortex'e odaklanmak için
- `shared/locators/aa.json`, `shared/locators/test.json` (HCM/LinkedIn'e ait)
- `src/test/resources/scratch/` (HCM scratch features)
- `sqlQueries/sql.json` HCM SQL'leri — Cortex placeholder ile değiştirildi
- config.properties'ten HCM, Trendyol, hilem URL'leri

### Değiştirildi
- **JsonReader + PwLocatorReader**: Sadeleştirildi, sadece `shared/`, `projects/*/locators/`, `recordings/` taranır. Eski sabit common files listesi kaldırıldı. `common.json` deseni eklendi.
- **TestRunner + PlaywrightTestRunner**: `cucumber.filter.tags` ile @selenium-only / @pw / @skip filtreleme
- README cortex-only odaklı yeniden yazıldı

### Eklendi
- **Multi-locator fallback**: aynı `key` için birden fazla entry → `MultiBy` (Selenium) ve `Locator.or()` (Playwright) ile sırayla denenir
- **`utils.LocatorLinter`** + `.run/LocatorLinter.run.xml`: JSON locator'larda anti-pattern detector (absolute XPath, index-based, dinamik class, auto-generated id, 150+ char)
- **`docs/locator-policy.md`**: locator önceliklendirme zinciri (data-testid → id → name → aria → CSS → text → xpath)

### Değiştirildi (yapısal)
- Test resources **projects/** yapısına geçti:
  ```
  src/test/resources/
  ├── projects/{cortex,hcm,linkedin,trendyol,api}/{features,locators}/
  ├── shared/locators/    (eski element.json, aa.json, shadow-locators.json)
  ├── recordings/         (recorder çıktısı)
  └── scratch/            (dev scratch)
  ```
- Eski klasörler (`fazlaeksik/`, `features/`, `Zt/`, `cortex/`, `playwright/`) kaldırıldı
- Eski `src/main/resources/locators/` boşaltıldı → tüm locator'lar `src/test/resources/projects/<X>/locators/`'a taşındı
- `JsonReader` ve `PwLocatorReader` yeni `projects/<X>/locators/` + `shared/locators/` + `recordings/locators/` dizinlerini tarar
- Runner annotation'ları `@SelectClasspathResource("projects")` + `shared` + `recordings`'e geçti

## [1.1.0] - 2026-05-20

### Eklendi
- **IntelliJ-driven Recorder**: `src/main/java/recorder/` — Playwright Chromium ile kayıt, recorder.js overlay toolbar, otomatik `*.feature` + `locators/*.json` üretimi
- **Playwright paralel runner**: ThreadLocal factory, BrowserContext izolasyonu, `mvn -Pplaywright,parallel test` ile N-thread
- **Cortex Dashboard (Flask)**: `/api/health`, `/api/results`, `/api/screenshots`, `/api/run` (SSE log), `/api/classify_error`
- **Windows installer**: PyInstaller `launcher.spec` + Inno Setup `CortexSetup.iss`
- **GitHub Actions CI**: Java build, Playwright paralel, Python dashboard smoke
- **Maven Wrapper**: `mvnw` / `mvnw.cmd`
- **57+ yeni Playwright step phrase**: DB, shadow, drag, key combo, variables, file upload/download
- **`.env` desteği**: ConfigManager 4-katlı çözüm sırası (-D > env > .env > config.properties)
- **SmartWait utility**: Thread.sleep yerine WebDriverWait + ExpectedConditions

### Değiştirildi
- DriverFactory artık **ThreadLocal** — paralel Selenium uyumlu
- `clearDriverCache()` kaldırıldı (her testte ~10sn tasarruf)
- AES anahtarı zorunlu env (`CORTEX_AES_KEY`), default `MySecretKey12345` kaldırıldı
- `cortex_login.json` smart fallback chain (placeholder/aria/data-test)
- Plugin sürümleri bump: compiler 3.13.0, surefire 3.2.5, selenium-devtools v131
- sklearn 1.4.2 → 1.6.1 (model uyumlu hale geldi)
- Dockerfile artık çalışan multi-stage (önceden tek kelime "test"ti)

### Güvenlik
- `password.properties` git'ten kaldırıldı (`.gitignore`'a alındı, untracked)
- `final_model.pkl` git'ten kaldırıldı (yerel eğitim ile üret)
- DB host artık `${ENV:DB1_HOST}` ile env'den okunur
- `scripts/scrub-git-history.sh` ile git history temizlik scripti

### Düzeltildi
- `LoggerUtil.logError(String, Throwable)` overload eksikti
- `PwCommonMethods.switchToNewTab` artık PAGE ThreadLocal'ı güncelliyor
- Fragile XPath'ler (tooltipster, pulseWarning, [3] index'ler) düzeltildi
- `element.json` absolute XPath → relative attribute-based
- Hardcoded `http://localhost:5001` → `ConfigManager.getProperty("ai.service.url")`

## [1.0.0] - önceki

İlk Java/Cucumber/Selenium/Karate framework + Python ML hata sınıflandırma.
