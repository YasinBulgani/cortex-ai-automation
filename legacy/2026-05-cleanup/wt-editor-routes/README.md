# TestwrightAI — Birleşik Monorepo

> **TestwrightAI** — AI destekli test otomasyonu, sentetik bankacılık verisi üretimi ve
> test süreç yönetimini tek platformda sunar. (Eski kod adı: _BGTS Test Dönüşüm_)

---

## İçindekiler

- [Proje Amacı](#proje-amacı)
- [Mimari](#mimari)
- [Modül Haritası](#modül-haritası)
- [Port Haritası](#port-haritası)
- [Depo birleştirme planı](#depo-birleştirme-ve-sadeleştirme)
- [Quick Start](#quick-start)
- [Geliştirme](#geliştirme)
- [Test Komutları](#test-komutları)
- [Ortam Değişkenleri](#ortam-değişkenleri)
- [Operasyon standardı ve sürüm yönetişimi](#operasyon-standardı-ve-sürüm-yönetişimi)

---

## Proje Amacı

TestwrightAI, Türk bankacılık sektörü için üç temel sorunu çözer:

| Sorun | Çözüm |
|-------|-------|
| Manuel test yazımı yavaş ve hatalı | **AI Test Generation** — doküman → test case → Playwright kodu |
| Gerçek müşteri verisiyle test riski | **Sentetik Veri Platformu** — şema analizi + AI zenginleştirme |
| Test senaryoları dağınık yönetilir | **TSPM** — merkezi senaryo + zamanlama + raporlama |

---

## Mimari

```
┌─────────────────────────────────────────────────────────────────┐
│                    TestwrightAI Monorepo                        │
│                                                                 │
│  ┌──────────────┐     ┌──────────────────────────────────────┐  │
│  │  apps/web    │────▶│           backend (FastAPI)           │  │
│  │  Next.js 14  │     │  ┌────────┐ ┌──────┐ ┌───────────┐  │  │
│  │  port: 3000  │     │  │  TSPM  │ │  AI  │ │ Sentetik  │  │  │
│  └──────────────┘     │  │        │ │ Svc  │ │   Veri    │  │  │
│                        │  └────────┘ └──────┘ └───────────┘  │  │
│  ┌──────────────┐     │           port: 8000                 │  │
│  │   engine     │     └──────────────────────────────────────┘  │
│  │ Flask + BDD  │                      │                         │
│  │  port: 5001  │               ┌──────▼──────┐                 │
│  └──────────────┘               │  PostgreSQL  │                 │
│                                 │  port: 5432  │                 │
│  ┌──────────────┐               └─────────────┘                 │
│  │ frameworks/  │                      │                         │
│  │ playwright-  │               ┌──────▼──────┐                 │
│  │ cucumber-ts  │               │    Redis     │                 │
│  └──────────────┘               │  port: 6379  │                 │
│                                 └─────────────┘                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                synthetic-data platform                    │   │
│  │   banking/ · platform-v4/ · mostlyai-datasets/           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Modül Haritası

### Aktif / Üretim Modülleri

| Dizin | Teknoloji | Durum | Açıklama |
|-------|-----------|-------|----------|
| `apps/web/` | Next.js 14, React 18, TypeScript | ✅ Aktif | Ana frontend dashboard |
| `backend/` | FastAPI, SQLAlchemy, PostgreSQL | ✅ Aktif | REST API — TSPM, AI, sentetik veri |
| `engine/` | Flask, Playwright, pytest-bdd | ✅ Aktif | Test otomasyon motoru |
| `ai-gateway/` | FastAPI, Provider clients | ✅ Aktif | AI modeli yönlendirme ve health |
| `frameworks/playwright-cucumber-ts/` | Playwright, Cucumber.js, TS | ⛔ Referans | Yeni sürümde `e2e/` altına taşındı, değişiklik hedefi değil |
| `e2e/` | Playwright | ✅ Aktif | End-to-end test senaryoları |
| `api-tests/` | pytest, requests | ✅ Aktif | API entegrasyon testleri |

### Araç / Destek Modülleri

| Dizin | Teknoloji | Açıklama |
|-------|-----------|----------|
| `infra/` | Docker, PostgreSQL, n8n | Altyapı konfigürasyonu |
| `collections/` | Postman, HTTP | API koleksiyonları |
| `scripts/` | Bash, Python | Yardımcı scriptler |
| `ai-engine/` | TypeScript | Opsiyonel CLI yardımcıları (kanonik runtime değil) |
| `tools/aday-analizi/` | Python, OpenAI | İşe alım değerlendirme aracı |
| `tools/aday-degerlendirme/` | Java, Maven | Mülakat değerlendirme aracı |
| `docs/` | Markdown | Teknik dokümantasyon |
| `synthetic-data/platform-v4/` | FastAPI, OpenAI/Claude | Referans / geçmiş karşılaştırma |

### Geçiş / Arşiv Modülleri (Silinmeye Aday)

| Dizin | Açıklama |
|-------|----------|
| `ai-test-pipeline/` | Yalnızca `__pycache__` — kaynak kod yok |
| `ai-test-automation/` | Eski AI otomasyon — çakışıyor |
| `test-automation-workspace/` | Eski workspace duplikatı |
| `backend/synthetic-data-v2/` | Eski versiyon |
| `backend/synthetic-data-v3/` | Eski versiyon |
| `backend/synthetic-data-bgtsflow/` | Eski BGTSFlow versiyonu |
| `frameworks/Test_Template/` | Boilerplate — `playwright-cucumber-ts` var |
| `frameworks/selenium-cucumber-java/` | Java Selenium — aktif kullanım yok |

Kanonik modül sınırı için tek referans: [`docs/repository-inventory.md`](docs/repository-inventory.md).

---

## Depo birleştirme ve sadeleştirme

Kanonik kod dizinleri, tekrarların temizlenmesi, kök arşiv ve isteğe bağlı npm workspaces için **ayrıntılı faz planı**:

| Belge | Açıklama |
|-------|----------|
| [`docs/repository-inventory.md`](docs/repository-inventory.md) | Kanonik modül listesi ve `coreOnly` kapsam kilidinin tek karar dosyası |
| [`docs/REPO_CONSOLIDATION_PLAN.md`](docs/REPO_CONSOLIDATION_PLAN.md) | Faz 0–5, riskler, test matrisi, kontrol listeleri |
| [`docs/MASTER.md`](docs/MASTER.md) | Tüm dokümantasyon haritası |
| [`docs/ADR-001-backend-engine-separation.md`](docs/ADR-001-backend-engine-separation.md) | FastAPI / Flask ayrımı (varsayılan karar) |
| [`archive/README.md`](archive/README.md) | Kökten taşınan sunum / analiz / geçici dosyalar |

Kökten `npm install` çalıştırıldığında **workspaces** (`apps/web`, `ai-engine`) birlikte kurulur.

---

## Port Haritası

| Servis | Port | Teknoloji | URL |
|--------|------|-----------|-----|
| **Frontend** | `3000` | Next.js 14 | http://localhost:3000 |
| **Backend API** | `8000` | FastAPI | http://localhost:8000/docs |
| **Engine** | `5001` | Flask | http://localhost:5001 |
| **AI Gateway** | `8080` | FastAPI | http://localhost:8080/ping |
| **Test Executor** | `5002` | Python HTTP | http://localhost:5002 |
| **PostgreSQL** | `5432` | Postgres 16 | localhost:5432/twai_db |
| **Redis** | `6379` | Redis 7 | localhost:6379 |

CI Playwright koşuları için izole port sözleşmesi: `APP_PORT=3417`, `API_PORT=8875`, `ENGINE_PORT=5001`.

---

## Quick Start

### Ön Koşullar

- Docker + Docker Compose v2
- Node.js 20+ (frontend geliştirme için)
- Python 3.12+ (local geliştirme için)

### 1. Ortam Değişkenleri

```bash
cp .env.example .env
# .env dosyasını düzenle: OPENAI_API_KEY, ANTHROPIC_API_KEY ekle
```

### 2. Tüm Servisleri Başlat

```bash
# Tek komut — tüm altyapı + backend + engine
./start-all.sh

# Ya da Docker Compose ile
docker compose up -d

# Frontend (ayrı terminal)
cd apps/web && npm install && npm run dev
```

### 3. Servisleri Doğrula

```bash
curl http://localhost:8000/health      # Backend
curl http://localhost:5001/health      # Engine
open http://localhost:3000             # Frontend
open http://localhost:8000/docs        # API Swagger
```

---

## Geliştirme

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # Migration'ları uygula
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm install
npm run dev    # http://localhost:3000
```

Yerel giriş (API + `NEXT_PUBLIC_API_BASE` + seed) için adım adım plan: **[docs/local-login-setup.md](docs/local-login-setup.md)**.

### Engine

```bash
cd engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:5001
```

### Sentetik Veri Servisi

```bash
cd synthetic-data/platform-v4
pip install -r requirements.txt
python app/main.py  # Backend üzerinden erişilir
```

---

## Production Deployment

Production ve staging dagitimi Kubernetes degil, SSH + Docker Compose modeliyle yapilir.

Temel dosyalar:

- `.github/workflows/deploy.yml`
- `docker-compose.prod.yml`
- `DEPLOYMENT_OPS_GUIDE.md`

Temel akıs:

```bash
# Sunucuda
docker compose -f docker-compose.prod.yml up -d postgres redis
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG=<git-sha> docker compose -f docker-compose.prod.yml pull backend worker engine web ai-gateway
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG=<git-sha> docker compose -f docker-compose.prod.yml run --rm -e SKIP_APP_BOOTSTRAP=1 backend alembic upgrade head
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG=<git-sha> docker compose -f docker-compose.prod.yml run --rm -e SKIP_APP_BOOTSTRAP=1 backend python -c 'from app.config import settings; assert settings.is_production_like'
GITHUB_REPOSITORY=<owner/repo> IMAGE_TAG=<git-sha> docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

Onemli notlar:

- Browser tarafinda engine erisimi icin `NEXT_PUBLIC_ENGINE_BASE=/api/v1/automation/proxy` kullanilir.
- Prod compose, GHCR uzerindeki ayri image'lari bekler: `-backend`, `-engine`, `-web`, `-ai-gateway`.
- Prometheus scrape ettigi servislerde `/metrics` endpoint'i bulunur.
- Production ortaminda backend `docs/openapi` endpoint'leri varsayilan olarak kapali kabul edilir.

---

## Operasyon standardı ve sürüm yönetişimi

Tek bir operasyonal referans seti kullanın:

- Çalıştırma ve geliştirme başlangıcı: `README.md`
- Dağıtım/rollback ve production adımları: `DEPLOYMENT_OPS_GUIDE.md`
- Runtime güvenlik kontratları: `docs/runtime-hardening-checklist.md`
- Dependency/versiyon politikası: `docs/dependency-governance.md`

Temel sözleşmeler:

- Python runtime parity: `3.12`
- Node.js runtime: `20.x`
- Dependency güncellemeleri: haftalık otomatik PR (Dependabot) + merge öncesi test/doğrulama zorunluluğu

---

## Test Komutları

```bash
make test-smoke        # Hızlı doğrulama (~2 dk)
make test-regression   # Mevcut özellikler (~10 dk)
make test-full         # Tüm testler (~20 dk)
make test-service      # Sadece API testleri (~3 dk)
make test-backend      # Backend pytest
make test-engine       # Engine pytest
make test-e2e          # Playwright E2E

# Framework testleri
cd frameworks/playwright-cucumber-ts
npm install && npx cucumber-js
```

---

## Ortam Değişkenleri

| Değişken | Açıklama | Örnek |
|----------|----------|-------|
| `DATABASE_URL` | PostgreSQL bağlantısı | `postgresql+psycopg2://user:pass@localhost:5432/twai_db` |
| `REDIS_URL` | Redis bağlantısı | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API anahtarı | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API anahtarı | `sk-ant-...` |
| `JWT_SECRET` | JWT imzalama anahtarı | `openssl rand -base64 64` çıktısı |
| `NEXT_PUBLIC_ENGINE_BASE` | Browser → engine backend proxy yolu | `/api/v1/automation/proxy` |
| `BASE_URL` | Test hedef URL | `https://your-app.com` |
| `BROWSER` | Test tarayıcısı | `chromium` / `firefox` / `webkit` |
| `HEADLESS` | Headless mod | `true` / `false` |

`.env.example` dosyasındaki placeholder değerleri gerçek secret/credential ile değiştirin; dosyayı doğrudan production değeri sanmayın.

---

*TestwrightAI — Bankacılık sektörü için AI destekli test dönüşüm platformu*
