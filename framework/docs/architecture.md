# Cortex Otomasyon — Architecture

```
                          ┌─────────────────────────────────────────┐
                          │           IntelliJ IDEA                  │
                          │  ┌─────────────────────────────────┐    │
                          │  │  .run/ Run Configurations:       │    │
                          │  │  • Recorder                      │    │
                          │  │  • Playwright Tests              │    │
                          │  │  • Playwright Parallel (4 / 8)   │    │
                          │  │  • Selenium Tests (legacy)       │    │
                          │  └────────────┬─────────────────────┘    │
                          └───────────────┼─────────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
        ▼                                 ▼                                 ▼
┌──────────────────┐         ┌──────────────────┐               ┌──────────────────┐
│   Recorder       │         │   Playwright     │               │   Selenium       │
│   (recording)    │         │   Runner         │               │   Runner         │
├──────────────────┤         ├──────────────────┤               ├──────────────────┤
│ RecorderMain     │         │ Playwright       │               │ TestRunner       │
│   ├ RecorderSrv  │         │ TestRunner /     │               │ (JUnit Platform) │
│   ├ Playwright   │         │ ParallelRunner   │               │                  │
│   │  Chromium    │         │ (JUnit Platform) │               │ DriverFactory    │
│   ├ recorder.js  │         │                  │               │ (ThreadLocal)    │
│   └ recorder.css │         │ PlaywrightFactory│               │  ├ Chrome        │
│                  │         │ (ThreadLocal)    │               │  ├ Firefox       │
│ Outputs:         │         │  ├ Browser       │               │  └ Edge          │
│ ├ *.feature      │         │  ├ Context       │               │                  │
│ └ locators/*.json│         │  └ Page          │               │ Step defs:       │
│                  │         │                  │               │ stepdefs.*       │
└────────┬─────────┘         │ Step defs:       │               │                  │
         │                   │ playwright.      │               │ Common config:   │
         │                   │   stepdefs.*     │               │ - locators/*.json│
         │                   └────────┬─────────┘               │ - .feature files │
         │                            │                         └────────┬─────────┘
         │                            │                                  │
         │                            └──────────┬───────────────────────┘
         │                                       │
         ▼                                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                      Shared resources                                │
│  src/main/resources/locators/*.json       (key/type/value)           │
│  src/test/resources/{cortex,playwright,features}/*.feature           │
│  src/main/resources/config.properties     (${ENV:VAR} placeholder)   │
│  .env                                     (secrets)                  │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 │ target/cucumber*.json
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Cortex Dashboard (Flask)                          │
│  http://localhost:5001                                               │
│                                                                       │
│  /api/health    /api/features    /api/results     /api/screenshots  │
│  /api/run       /api/run/<id>/stream (SSE)        /api/classify_error│
│                                                                       │
│  dashboard/static/  →  index.html + Chart.js                         │
└────────────────┬───────────────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                    ML Hata Analizi                                   │
│  python_server/final_model.pkl   (scikit-learn TF-IDF + LR)          │
│  python_server/suggestions.json  (kategori bazli oneriler)           │
└────────────────────────────────────────────────────────────────────┘


Windows dağıtım:
┌──────────────────────────────────────────────────────────────────┐
│  scripts/build-installer.bat                                       │
│    ↓ PyInstaller (launcher.spec)                                   │
│      → dist/CortexDashboard/CortexDashboard.exe                    │
│    ↓ Inno Setup (CortexSetup.iss)                                  │
│      → installer/out/CortexSetup-1.0.0.exe                         │
└──────────────────────────────────────────────────────────────────┘
```

## Veri akışı: test → dashboard

```
1. Kullanıcı IntelliJ'de "Playwright Parallel (4 thread)" çalıştırır
       ↓
2. JUnit Platform 4 thread başlatır
       ↓
3. Her thread:
   • PlaywrightFactory.openContextAndPage(scenarioName)
   • PwConfigSteps.loadLocators(...) — feature adı → JSON dosyası
   • Hooks @Before
   • Step def'ler çalışır → page.click/fill/...
   • Hooks @After: fail ise screenshot, context.close()
       ↓
4. Surefire target/cucumber-playwright-parallel.json üretir
       ↓
5. Dashboard:
   • /api/results → bu JSON'u parse eder
   • /api/screenshots → screenshots/playwright/ tarar
   • CucumberJsonAnalyzer → her failed step için /api/classify_error POST
   • ML model → predicted_label + suggestion döner
       ↓
6. Frontend Chart.js ile pasta + bar grafiği çizer
```

## Recorder akışı

```
1. IntelliJ Run > Recorder ▶
       ↓
2. RecorderMain:
   • RecorderConfig: -D > env > recorder.properties
   • RecorderServer açılır (127.0.0.1:7700)
   • Playwright Chromium başlar
   • addInitScript(recorder.js + recorder.css)
   • page.navigate(cortex.url)
       ↓
3. Kullanıcı tarayıcıda gezer:
   • Click → recorder.js → describe(el) → POST /action
   • Input → debounced fill → POST /action
   • Assertion modu → eleman seçimi → POST /action (assert_visible)
       ↓
4. Stop:
   • Toolbar "Durdur ve Kaydet" → POST /stop
   • VEYA IntelliJ Stop ▣ → JVM shutdown hook
       ↓
5. persist():
   • ActionTranslator → Gherkin satırları
   • LocatorBuilder → smart locator strategy
   • FeatureWriter → *.feature + locators/*.json
       ↓
6. Konsola dosya yolları yazılır → test çalıştırılabilir
```
