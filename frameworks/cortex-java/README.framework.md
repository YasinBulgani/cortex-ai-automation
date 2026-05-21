# Cortex Otomasyon

Cortex test ortamı için Cucumber + Selenium + Playwright tabanlı test framework + IntelliJ-driven recorder + dashboard.

**Hedef sistem:** [https://cortex-test.bgtsai.com/](https://cortex-test.bgtsai.com/)

```
       ┌─────────────────────────────────────────┐
       │       IntelliJ IDEA / Maven CLI          │
       └────────────┬────────────────────────────┘
                    │
        ┌───────────┼────────────┬─────────────┐
        ▼           ▼            ▼             ▼
   Recorder    Playwright    Selenium     Dashboard
              (paralel       (legacy       (Flask +
               N-thread)     sequential)    Chart.js)
        │           │            │             │
        └───────────┼────────────┘             │
                    ▼                          │
            Cortex test ortami                 │
            (cortex-test.bgtsai.com)           │
                    │                          │
                    ▼                          │
            target/cucumber*.json  ───────────▶│
            screenshots/*                       │
                                                ▼
                                        AI hata analizi
                                        (scikit-learn)
```

## Hızlı başlangıç

```bash
# 1. Env hazırla
cp .env.example .env
# .env'de: CORTEX_AES_KEY=<tam 16 karakter>
# CORTEX_USERNAME=<test kullanıcı email>

# 2. Sifreli parolayı framework içinde kaydet (bir kez):
mvn test -Dcucumber.features=path/to/setup.feature
# (veya recorder ile login akışı kaydet → otomatik şifre prompt'u)

# 3. Test koşumu
./mvnw test                              # Selenium runner
./mvnw -Pplaywright test                 # Playwright sequential
./mvnw -Pplaywright,parallel test        # Playwright paralel (4 thread default)
./mvnw -Pplaywright,parallel test -Dparallel.threads=8

# 4. Dashboard
./scripts/start-dashboard.sh             # macOS/Linux
scripts\start-dashboard.bat              # Windows
```

## Komutlar

### `scripts/cortex` CLI (önerilen)

```bash
./scripts/cortex smoke              # @smoke suite
./scripts/cortex regression         # full @cortex regression
./scripts/cortex parallel 8         # 8-thread parallel
./scripts/cortex tag "@security"    # tag expression filter
./scripts/cortex feature path/to/login.feature
./scripts/cortex rerun              # failure rerun (target/failed.txt)
./scripts/cortex debug path         # trace + video + slow-mo
./scripts/cortex headless           # parallel + headless (CI mode)
./scripts/cortex record https://...
./scripts/cortex lint               # LocatorLinter
./scripts/cortex report             # Allure UI
./scripts/cortex install            # download Playwright browsers
./scripts/cortex dashboard          # start Flask dashboard
./scripts/cortex clean              # mvn clean + nuke target/
```

### IntelliJ Run Configurations (`.run/` hazır)

| Config | Karşılığı |
|---|---|
| **Cortex - Smoke** | `mvn -Psmoke test` |
| **Cortex - Regression** | `mvn -Pregression test` |
| **Cortex - Parallel (4 threads)** | `mvn -Pregression,parallel test` |
| **Cortex - Parallel Headless (CI)** | `mvn -Pregression,parallel,headless test` |
| **Cortex - Debug (trace + video)** | `mvn -Psmoke,debug test` |
| **Cortex - Re-run Failed** | `mvn test -Dcucumber.features=@target/failed.txt` |
| **Recorder** | IntelliJ-driven recorder |
| **Recorder (custom URL)** | Recorder w/ explicit VM options |
| **Locator Linter** | `utils.LocatorLinter` standalone |

### Maven profil matrisi

| Profil | Etki |
|---|---|
| `smoke` | `cucumber.filter.tags=@smoke` |
| `regression` | `cucumber.filter.tags=@cortex and not @manual and not @skip` |
| `parallel` | 4 thread (override: `-Dparallel.threads=8`) |
| `headless` | `playwright.headless=true` |
| `debug` | `trace=true, video=true, slow.mo=200` |
| `recorder` | exec:java RecorderMain |

## Klasör yapısı

```
cortex-otomasyon/
├── .github/workflows/             CI (Java + Playwright paralel + Dashboard smoke)
├── .run/                          IntelliJ Run configs
├── docs/                          locator-policy, step-reference, architecture
├── installer/                     Windows installer (.iss, PyInstaller spec)
├── scripts/                       Bash/batch scripts
│
├── src/main/java/
│   ├── api, config, crypto, db, drivers, methods, utils   ← Selenium + core
│   ├── playwright/                                          ← Playwright engine
│   └── recorder/                                            ← IntelliJ-driven recorder
│
├── src/main/resources/
│   ├── config.properties                                    ← Cortex URL'leri + ${ENV:...}
│   ├── log4j2.xml                                           ← rolling 10MB/7 gün
│   ├── recorder/{recorder.js, recorder.css}                 ← enjekte edilen overlay
│   └── sqlQueries/                                          ← DB testleri için
│
├── src/test/java/
│   ├── runners/TestRunner.java                              ← Selenium suite
│   ├── stepdefs/                                            ← Selenium step defs
│   └── playwright/
│       ├── runners/{PlaywrightTestRunner, PlaywrightParallelRunner}
│       └── stepdefs/{PwHooks, PwCommonSteps, PwExtraSteps, PwConfigSteps}
│
├── src/test/resources/
│   ├── projects/cortex/                                     ★ AKTİF PROJE
│   │   ├── features/
│   │   │   ├── login.feature                                happy path + smoke
│   │   │   ├── login-validation.feature                     form validation
│   │   │   ├── login-security.feature                       SQLi, XSS, brute-force
│   │   │   ├── login-accessibility.feature                  keyboard, ARIA
│   │   │   ├── login-forgot-password.feature                reset akışı
│   │   │   ├── login-session.feature                        logout, redirect
│   │   │   ├── login-edge-cases.feature                     long inputs, special chars
│   │   │   └── junit-platform.properties                    parallel config
│   │   └── locators/
│   │       ├── common.json                                  ortak (cookie, header, modal)
│   │       └── login.json                                   30+ locator multi-fallback
│   ├── shared/locators/shadow-locators.json                 shadow DOM locator'lar
│   └── recordings/                                          recorder çıktısı
│
├── python_server/                Flask dashboard backend + ML model
├── dashboard/static/             HTML + Chart.js frontend
├── runtime/  (logs/, screenshots/)  runtime artefactlar (.gitignored)
└── target/                       Maven build çıktısı
```

## Cortex login senaryoları

| Feature | Senaryo | Detay |
|---|---|---|
| **login.feature** | 5 | Sayfa yükleme, başarılı giriş, Enter ile gönderim, "Beni hatırla", kullanıcı menüsü |
| **login-validation.feature** | 8 | Boş alan, hatalı şifre, yok kullanıcı, geçersiz email, retry, password mask |
| **login-security.feature** | 4 | SQL injection (6 payload), XSS (5 payload), brute-force, CSRF |
| **login-accessibility.feature** | 5 | TAB navigation, label binding, keyboard reach to forgot-password |
| **login-forgot-password.feature** | 6 | Link görünür, form yüklenir, geçerli/geçersiz email |
| **login-session.feature** | 4 | Logout, dashboard redirect, already-logged-in |
| **login-edge-cases.feature** | 7 | Uzun input, özel karakter, trim, case-sensitivity, slow connection, double-submit |
| **TOPLAM** | **39 senaryo** | + Scenario Outline ile **50+ varyasyon** |

Tüm senaryolar **hem Selenium hem Playwright runner**'da çalışır (aynı step phrase'leri).
Paralel modda her senaryo izole `BrowserContext` alır.

## Locator stratejisi

XPath son çare, başlangıç değil. Detay: [docs/locator-policy.md](docs/locator-policy.md).

**Öncelik:** `data-testid` → `id` → `name` → `aria-label` → CSS → text → xpath

**Multi-fallback** (geriye uyumlu) — aynı key birden fazla entry ile tanımlanır:
```json
[
  { "key": "loginButton", "type": "css",   "value": "[data-testid='login-submit']" },
  { "key": "loginButton", "type": "id",    "value": "btnLogin" },
  { "key": "loginButton", "type": "xpath", "value": "//button[normalize-space()='Giriş Yap']" }
]
```
Selenium `MultiBy` ve Playwright `Locator.or()` bu zinciri otomatik dener.

**Linter** anti-pattern detect:
```bash
./mvnw exec:java -Dexec.mainClass=utils.LocatorLinter
```

## Dashboard

```bash
./scripts/start-dashboard.sh
# → http://localhost:5001
```

| Sekme | İçerik |
|---|---|
| Genel Bakış | KPI kartları, pasta + bar grafiği |
| Test Koşumu | Feature seç → Maven canlı log (SSE) |
| Sonuçlar | Feature/senaryo ağacı, hata detayı |
| Ekran Görüntüleri | Selenium + Playwright birleşik galeri |
| AI Hata Analizi | Hata mesajı → ML kategorisi + öneri |
| Konfigürasyon | Maskelenmiş config.properties |

## Recorder (IntelliJ Run > Recorder)

1. Run ▶ → Chromium açılır, cortex-test.bgtsai.com'a gider
2. Sağ-alt toolbar: Duraklat / Doğrulama / Bekleme / Geri Al / Durdur
3. Cortex'i gez → her aksiyon `POST /action` ile yakalanır
4. **Durdur ve Kaydet** → `src/test/resources/recordings/`'e feature + locator JSON yazılır

Detay: [src/main/java/recorder/README.md](src/main/java/recorder/README.md).

## Dağıtım

| Hedef | Yöntem |
|---|---|
| **Linux/macOS** | `docker build -t cortex-otomasyon .` |
| **Windows** | `scripts\build-installer.bat` → `CortexSetup-1.0.0.exe` |
| **CI** | GitHub Actions `.github/workflows/ci.yml` (Java + Playwright + Dashboard) |

## Daha fazla doc

- [docs/locator-policy.md](docs/locator-policy.md) — XPath öncelik zinciri, anti-pattern'ler, naming
- [docs/step-reference.md](docs/step-reference.md) — Selenium + Playwright phrase tablosu
- [docs/architecture.md](docs/architecture.md) — ASCII mimari diyagram
- [docs/env-setup.md](docs/env-setup.md) — `.env`, AES anahtarı, sifreli parolalar
- [CONTRIBUTING.md](CONTRIBUTING.md) — branch + commit + locator naming
- [CHANGELOG.md](CHANGELOG.md) — sürüm geçmişi
