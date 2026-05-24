# Cortex AI Automation

Test otomasyon platformu — Java framework + Next.js monorepo + Python dashboard.

[![Build Installers](https://img.shields.io/badge/installers-Mac%20%2B%20Windows-success)]()
[![Java](https://img.shields.io/badge/Java-17%2B-orange)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)]()
[![Next.js](https://img.shields.io/badge/Next.js-14-black)]()
[![Turbo](https://img.shields.io/badge/Turborepo-2-pink)]()

---

## Tek-tıklamayla başla

| Platform | İndir | Çalıştır |
|---|---|---|
| **macOS** | `Cortex_Ai_Automation-Setup-X.Y.Z-macOS.dmg` | DMG aç → `Cortex Setup.command` çift-tıkla |
| **Windows** | `CortexSetup-X.Y.Z-Windows.exe` | EXE çift-tıkla → sihirbazı takip et |

Installer **otomatik olarak**: Java 17 + Python 3.10+ + Maven + Playwright Chromium + Python venv + ML modeli kurar, masaüstüne kısayol açar, Flask dashboard'u başlatır.

İlk açılışta: **http://localhost:5001** (Flask dashboard, gömülü HTML UI)

**Modern Next.js dashboard** isterseniz (opsiyonel):
```bash
npm install     # node_modules ~1GB, sadece bir kere
npm run web:dev # → http://localhost:3000
```

---

## Proje yapısı (Monorepo)

```
Cortex_Ai_Automation/
├── README.md                      ← bu dosya
├── package.json                   ← Workspace root (npm workspaces + turbo)
├── turbo.json                     ← Turborepo build orchestration
├── tsconfig.base.json             ← TS base config
├── LICENSE.txt
├── .gitignore
│
├── frameworks/cortex-java/                     ← Java + Python (Cortex test framework)
│   ├── pom.xml, mvnw, mvnw.cmd
│   ├── .mvn/                      — Maven wrapper conf
│   ├── src/                       — Java source (Recorder, runner, steps, Playwright)
│   ├── python_server/             — Flask API + AI classifier
│   ├── dashboard/                 — Gömülü HTML dashboard (Flask serve)
│   ├── docs/                      — Markdown teknik dokümantasyon
│   ├── scripts/                   — CLI tools (cortex, launchers)
│   └── recorder.properties        — Recorder default config
│
├── apps/                          ← Next.js apps
│   ├── web/                       — Ana web uygulaması
│   │   ├── app/                   — App Router pages
│   │   │   └── (dashboard)/       — Dashboard alanı (intelligence, monkey, llm-agent, …)
│   │   ├── components/products/   — CortexScenarioAuthor + CortexAutomationPanel + …
│   │   ├── next.config.mjs        — Flask proxy + env
│   │   └── package.json
│   └── storybook/                 — Component playground
│
├── packages/                      ← Shared workspace libs (@neurex/* namespace)
│   ├── design-system/             — Tasarım sistemi (Radix + Tailwind)
│   ├── product-intelligence/      — Intelligence ürün modülü
│   ├── product-kit/               — Cross-product UI kit
│   ├── product-web/, product-data/, product-mobile/, product-service/, product-studio/, product-one/, product-code/
│   ├── contracts/                 — Type contracts
│   ├── ai-sdk/                    — AI provider abstraction
│   ├── banking-domain/            — Domain models
│   ├── dsl/                       — Test DSL
│   ├── config/                    — Shared configs
│   └── telemetry/                 — OpenTelemetry helpers
│
├── installer/                     ← Cross-platform packager
│   ├── README.md                  — Builder talimatları
│   ├── build-all.sh               — Master build (Mac-side)
│   ├── mac/                       — DMG / .app / install.sh
│   └── windows/                   — Inno Setup .iss + install-deps.ps1
│
└── .github/workflows/
    └── build-installers.yml       ← Tag push → Mac DMG + Windows EXE
```

---

## Hızlı başlangıç (Geliştirici)

### Gereksinimler
- **Java 17+** ([Adoptium Temurin](https://adoptium.net))
- **Python 3.10+** ([python.org](https://python.org))
- **Node.js 18+** ([nodejs.org](https://nodejs.org))
- **Maven** opsiyonel (`frameworks/cortex-java/mvnw` ile gelir)

### 1. Java framework + Flask dashboard
```bash
cd framework
./mvnw -DskipTests compile
python3 -m venv .venv && source .venv/bin/activate
pip install -r python_server/requirements.txt
cd python_server && python flask_api.py
# → http://localhost:5001
```

### 2. Next.js modern dashboard (opsiyonel)
```bash
# Repo kökünden
npm install                # turborepo + tüm workspace deps
npm run web:dev            # → http://localhost:3000

# Veya:
npm run dev                # turbo run dev (tüm app+package'lerde watch)
```

### 3. Recorder kullanımı
```bash
cd framework
./mvnw exec:java \
  -Dexec.mainClass="recorder.RecorderMain" \
  -Dexec.args="https://cortex-test.bgtsai.com/"
```

Veya dashboard'da: **+ Yeni Senaryo Yaz** → **Recorder** → **Başlat**

### 4. Test çalıştırma
```bash
cd framework
./mvnw test                                  # Tüm Cucumber + JUnit testleri
./mvnw test -Dcucumber.filter.tags="@smoke"  # Sadece smoke
./mvnw test -Pparallel                       # 4 paralel
```

---

## Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js Modern Dashboard (apps/web)         localhost:3000     │
│  • CortexScenarioAuthor (3 modlu senaryo yazma)                 │
│  • IntelligenceProductPage (live recorder + metrics)            │
│  • Monkey testing, LLM agent, ve diğer ürün sayfaları           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ rewrites: /api/cortex/* → :5001
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Flask API + HTML Dashboard (frameworks/cortex-java/python_server)           │
│                                              localhost:5001     │
│  • /api/cortex/recorder/* (start/stop/status/actions)           │
│  • /api/cortex/files/* (in-dashboard IDE)                       │
│  • /api/cortex/steps, /tags, /locator-* (scenario authoring)    │
│  • / (gömülü HTML dashboard, statik)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ subprocess: mvn exec:java RecorderMain
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Java Recorder (frameworks/cortex-java/src/recorder)      127.0.0.1:7700     │
│  • Playwright Chromium (CDP, exposeBinding __cortexSend)        │
│  • Triple-channel transport (binding + console + HTTP)          │
│  • Hibrit input/change/submit otomatik + click PICK             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ JSON over CDP message bus
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  recorder.js (browser-side, addInitScript)                      │
│  • React hydration-proof (heartbeat re-attach)                  │
│  • Page scan (XPath/CSS snapshot)                               │
│  • TDZ-safe (let hoisting), global error capture                │
│  • macOS app activation (osascript)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Özellikler

### Recorder
- 3 modlu senaryo yazma (Recorder / AI Üret / Manuel)
- Hibrit yakalama: input/change/submit otomatik + click PICK mode
- Triple-channel transport (CDP binding + console + HTTP fallback)
- Element scanner: tüm interaktif element'lerin XPath/CSS snapshot
- Live actions panel + STOP/UNDO/PAUSE in-browser toolbar
- React hydration'a karşı 400ms heartbeat
- macOS Chromium app activation (osascript)

### Runner
- Cucumber JVM + Playwright Java SDK
- 4'lü paralel koşum (`-Pparallel`)
- Tag suites: `@smoke`, `@regression`, `@critical`
- Retry on flaky + Allure raporlar
- axe-core a11y scan

### Dashboard
- **Flask (gömülü HTML)**: live test sonuçları, screenshots, AI fail-pattern, IDE (file tree + CodeMirror)
- **Next.js (modern)**: tüm Flask özellikleri + modern UI/UX, scenario authoring modal, 30s no-event diagnostic

### Monorepo (Turborepo)
- 2 app (`web`, `storybook`) + 16 paylaşılan package
- Workspace-level `npm install` (tek tek değil)
- `npm run dev` → tüm app'lerde paralel watch
- `npm run build` → incremental build cache

---

## Installer'ı sıfırdan derle

Detay: [installer/README.md](installer/README.md)

```bash
# Mac DMG (Mac üzerinde)
bash installer/mac/build-dmg.sh 1.0.0
# → installer/out/Cortex_Ai_Automation-Setup-1.0.0-macOS.dmg

# Windows EXE (Windows üzerinde, Inno Setup 6+ ile)
installer\windows\build.bat 1.0.0
# → installer\out\CortexSetup-1.0.0-Windows.exe

# CI ile her ikisi otomatik
git tag v1.0.0 && git push --tags
# → GitHub Actions hem .dmg hem .exe üretir + Release'e ekler
```

**Önemli**: Installer şu an SADECE Java framework + Python Flask'ı yüklüyor. Next.js Web/Storybook için son kullanıcı `npm install` + `npm run web:dev` yapmalı (heavy node_modules). Bunu da otomatize etmek istenirse `installer/windows/install-deps.ps1` ve `installer/mac/install.sh` içine `npm install` adımı eklenebilir.

---

## Lisans

[MIT](LICENSE.txt) · © Bilge Adam

---

## Destek

- **Hedef site**: <https://cortex-test.bgtsai.com/>
- **Sürüm**: 1.0.0
- **Workspace namespace**: `@neurex/*` (legacy — fonksiyonel, ileride `@cortex/*`'a rename edilebilir)
