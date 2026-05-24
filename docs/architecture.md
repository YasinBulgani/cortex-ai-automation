# BGTS Test Dönüşüm — Mimari Dokümantasyon

## Genel Bakış

BGTS Test Dönüşüm, **test yönetimi**, **sentetik veri üretimi** ve **AI destekli test otomasyonu** yeteneklerini tek bir platformda birleştiren bir monorepo projesidir.

```
┌─────────────────────────────────────────────────────────────┐
│                        Kullanıcı                            │
│                    (Web Tarayıcı)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   apps/web (Next.js)    │  :3000
         │   React 18 + Tailwind   │
         │   App Router            │
         └──────┬───────────┬──────┘
                │           │
    ┌───────────▼──┐  ┌─────▼──────────┐
    │   backend/   │  │    engine/      │
    │   FastAPI    │  │    Flask        │
    │   :8000      │  │    :5001        │
    │              │  │                 │
    │ • TSPM       │  │ • AI Engine     │
    │ • Sentetik   │  │ • BDD Runner    │
    │   Veri       │  │ • Visual Test   │
    │ • Auth/JWT   │  │ • A11y Test     │
    │ • Katalog    │  │ • Recorder      │
    │ • İşler/RQ   │  │ • Reporter      │
    └──────┬───────┘  └────────────────┘
           │
    ┌──────▼───────┐  ┌────────────────┐
    │  PostgreSQL   │  │     Redis      │
    │  :5432        │  │     :6379      │
    └──────────────┘  └────────────────┘
```

## Servis Mimarisi

### 1. Frontend — `apps/web/`
- **Teknoloji**: Next.js 14, React 18, TypeScript, Tailwind CSS, React Flow
- **Port**: 3000
- **Görev**: Test senaryoları yönetimi, akış editörü, dashboard, kullanıcı arayüzü
- **API İletişimi**: 
  - `apiFetch()` → FastAPI backend (:8000)
  - `engineFetch()` → Flask engine (:5001)

### 2. Backend — `backend/`
- **Teknoloji**: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis/RQ
- **Port**: 8000
- **Domain Modülleri**:
  | Domain | Görev |
  |--------|-------|
  | `auth` | JWT tabanlı kimlik doğrulama |
  | `catalog` | Veri seti kataloğu |
  | `rules` | Kural yönetimi |
  | `jobs` | Arka plan iş kuyruğu (RQ) |
  | `artifacts` | Çıktı dosyaları yönetimi |
  | `tspm` | Test Senaryo ve Süreç Yönetimi |
  | `automation` | Engine proxy/entegrasyon |

### 3. Otomasyon Motoru — `engine/`
- **Teknoloji**: Flask, Playwright, OpenAI/Anthropic, pytest-bdd
- **Port**: 5001
- **Core Modüller**:
  | Modül | Görev |
  |-------|-------|
  | `ai_engine.py` | LLM ile test üretimi, aksiyon çalıştırma |
  | `browser.py` | Playwright tarayıcı yönetimi |
  | `page_inspector.py` | DOM analizi, element keşfi |
  | `test_recorder.py` | Aksiyon kaydı, kod üretimi (Playwright/Cucumber/POM) |
  | `visual_regression.py` | SSIM tabanlı görsel karşılaştırma |
  | `accessibility_tester.py` | WCAG 2.1 erişilebilirlik testi |
  | `enhanced_framework.py` | Paralel test çalıştırma, retry, raporlama |
  | `reporter.py` | HTML/JSON test raporu üretimi |
  | `context.py` | Adımlar arası veri paylaşımı |

- **API Blueprint'leri**:
  | Blueprint | Endpoint Prefix | Görev |
  |-----------|----------------|-------|
  | `auth` | `/api/auth/*` | Platform kullanıcı yönetimi |
  | `feature` | `/api/features/*` | Gherkin feature dosyaları CRUD |
  | `regression` | `/api/regression-sets/*` | Regresyon seti yönetimi |
  | `manual` | `/api/manual-tests/*` | Manuel test senaryoları |
  | `locators` | `/api/locators/*` | Object repository (XPath/CSS) |
  | `runner` | `/api/run/*` | Test çalıştırma + SSE stream |
  | `ai` | `/api/generate-feature/*` | AI ile test üretimi |
  | `visual` | `/api/visual/*` | Görsel regresyon testleri |
  | `a11y` | `/api/a11y/*` | Erişilebilirlik testleri |
  | `recorder` | `/api/recorder/*` | Test kaydedici |
  | `datasim` | `/api/datasim/*` | Veri simülasyonu |
  | `project` | `/api/projects/*` | Proje yönetimi |

### 4. Altyapı — `infra/`
- PostgreSQL 16, Redis 7, MinIO (object storage), n8n (workflow)
- Docker Compose ile orkestrasyon
- Alembic ile veritabanı migration'ları

## Dizin Yapısı

```
Cortex_Ai_Automation/
├── apps/
│   └── web/                    # Next.js 14 Frontend
│       ├── app/                # App Router sayfaları
│       ├── components/         # React bileşenleri
│       └── lib/                # API client, utils
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── domains/            # Domain-driven modüller
│   │   │   ├── auth/
│   │   │   ├── catalog/
│   │   │   ├── rules/
│   │   │   ├── jobs/
│   │   │   ├── artifacts/
│   │   │   ├── tspm/
│   │   │   └── automation/     # Engine proxy
│   │   ├── infra/              # DB, models
│   │   └── main.py
│   ├── alembic/                # DB migrations
│   └── Dockerfile
├── engine/                     # Test Otomasyon Motoru
│   ├── core/                   # Temel modüller
│   ├── config/                 # Ayarlar
│   ├── routes/                 # Flask blueprints
│   ├── pages/                  # Page Object Model
│   ├── steps/                  # BDD step definitions
│   ├── features/               # Gherkin senaryoları
│   ├── scripts/                # CLI araçları
│   ├── tests/                  # Unit/integration tests
│   ├── ui/                     # Flask web UI
│   ├── app.py                  # Flask entrypoint
│   ├── runner.py               # Allure test runner
│   └── Dockerfile
├── infra/                      # Altyapı konfigürasyonu
│   ├── docker-compose.yml
│   ├── docker-compose.syndata.yml
│   └── postgres-init/
├── e2e/                        # Playwright E2E testler
├── docs/                       # Dokümantasyon
├── docker-compose.yml          # Ana orkestrasyon
├── .env.example                # Ortam değişkenleri şablonu
└── playwright.config.ts        # E2E test ayarları
```

## Hızlı Başlangıç

```bash
# 1. Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasını düzenle (API anahtarları vb.)

# 2. Altyapıyı başlat
docker compose up -d postgres redis

# 3. Backend'i başlat
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 4. Otomasyon motorunu başlat
cd engine
pip install -r requirements.txt
playwright install chromium
python app.py

# 5. Frontend'i başlat
cd apps/web
npm install
npm run dev
```

## Servis İletişimi

```
Frontend (:3000) ──→ Backend (:8000)  /api/v1/*
                 ──→ Engine  (:5001)  /api/*
                 ──→ Backend (:8000)  /api/v1/automation/proxy/*  (engine proxy)

Backend  (:8000) ──→ PostgreSQL (:5432)
                 ──→ Redis (:6379)
                 ──→ Engine (:5001) via httpx proxy
```

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, React Flow |
| Backend API | FastAPI, Pydantic, SQLAlchemy 2, Alembic |
| Otomasyon | Flask, Playwright, pytest-bdd, Allure |
| AI/LLM | OpenAI GPT-4o, Anthropic Claude |
| Veritabanı | PostgreSQL 16, SQLite (engine local) |
| Kuyruk | Redis + RQ |
| Test | Playwright E2E, pytest, pytest-bdd |
| Altyapı | Docker Compose, GitHub Actions CI/CD |
| Raporlama | Allure, HTML (custom), JSON |
