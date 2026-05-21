# ADR-0002: Engine (Flask) ve Backend (FastAPI) ayrı kalıyor

**Durum:** Kabul edildi
**Tarih:** 2026-04-19
**Karar verenler:** @yasin_bulgan

## Bağlam

Repo'da iki ayrı Python web servisi var:

### `backend/` (FastAPI, port 8000)
- 25+ domain (tspm, ai, auth, mobile, coverup, evals, jobs, audit, notifications, vs.)
- Modern domain-driven yapı (`backend/app/domains/<domain>/`)
- Alembic migration'ları
- JWT auth, async DB (asyncpg), Redis cache
- ~60 router.py dosyası, ~400+ endpoint
- Sentetik veri, AI generation, TSPM için ana public API

### `engine/` (Flask, port 5001)
- 37 blueprint dosyası (`engine/routes/*.py`)
- Flask session auth (cookie-based)
- Kendi HTML UI (`engine/ui/templates/index.html`)
- Playwright, pytest-bdd, Cucumber orchestration
- Allure rapor üretimi, screenshot/video capture
- Feature file management, locator registry, recorder

İki servis arasındaki ilişki:
- **Kod seviyesinde bağımsız** — ne engine `backend`'den, ne backend `engine`'den import yapıyor
- **HTTP seviyesinde bağlı** — `X-Internal-Key` header ile iç iletişim
- Bazı overlap var: `engine/ai_synthetic_data/` ↔ `backend/app/domains/ai_synthetic_data/`, `engine/evals/` ↔ `backend/app/domains/evals/`, `engine/services/llm_gateway.py` ↔ `backend/app/domains/ai/gateway_client.py`

Soru: İkisini birleştirelim mi?

## Karar

**Hayır, ayrı kalıyorlar.** Ancak rol ayrımı netleştirilecek ve overlap'ler tek sahipli hâle getirilecek.

Final rol dağılımı:
- **Engine:** Test runtime. Playwright, pytest-bdd, feature file, locator, screenshot, Allure.
- **Backend:** Business logic. TSPM, AI orchestration, synthetic data, auth, audit, evals.
- **AI Gateway:** LLM fallback zinciri (ayrı servis, `ai-gateway/`).

Overlap'ler backend'e taşınacak. Engine AI çağrılarını backend'e proxy'leyecek. Detay: `docs/architecture/engine-backend-contract.md`.

## Alternatifler

### A. Engine'i FastAPI'ye port et, tek servis yap
**Red sebepleri:**
- Tahmin: 2 haftalık iş (37 blueprint + session auth + HTML UI)
- Yüksek regresyon riski: test runner bozulursa tüm otomasyon durur
- Session auth → JWT geçişi kullanıcı deneyimini etkiler
- Kazanç (tek proses, daha az port) değişiklik maliyetine değmez

### B. Backend'i Flask'a port et
**Red sebebi:**
- Çok daha kötü. FastAPI'den Flask'a gitmek → modern ekosistemden feragat (async, pydantic, OpenAPI)

### C. Engine'i backend'in Celery worker'ı yap
**Red sebebi:**
- Playwright zaten eventloop yönetiyor, Celery ile iki executor çakışır
- Engine'in HTML UI'ı bir Flask feature'ı, Celery'e sığmaz
- Ayrı port vermek daha temiz

### D. Ayrı kalsınlar, mevcut şekilde hiçbir şey yapma
**Red sebebi:**
- Overlap kodu (AI gateway, evals, synthetic data) iki yerde evrim geçirir → bug kaynağı
- Engine'in public port (5001) dışa açık olmamalı — güvenlik

## Sonuçlar

### Olumlu
- Büyük refactor yok, düşük risk
- Engine'in olgun test runtime kodu dokunulmadan kalır
- Rol netleştirmesi ile overlap azalır
- İki servis sınırı, ileride mikroservis ayrımına hazır

### Olumsuz / takas
- İki Python runtime (iki venv, iki container, iki deploy)
- Ops karmaşası: iki log stream, iki health endpoint, iki update cycle
- Kod sahipliği sınırı net olmazsa "bu backend'de mi engine'de mi?" karmaşası
- İki farklı auth mekanizması (JWT vs session) karıştırılmamalı

### Takip işleri
- [x] Kontrat dokümanı: `docs/architecture/engine-backend-contract.md`
- [x] Engine port 5001'i docker-compose'da `127.0.0.1` bind'a çevir (Faz 4.B, 2026-04-19)
- [x] Engine healthcheck + backend `depends_on: service_healthy` (Faz 4.B)
- [x] `engine/services/llm_gateway.py` proxy mode + feature flag + testler (Faz 4.C, 2026-04-19)
- [x] Deprecated endpoint'lere `Sunset: 2026-06-01` header eklendi (Faz 4.B)
- [ ] Staging'de `ENGINE_LLM_USE_GATEWAY=1` aç, 1 hafta gözlem
- [ ] Prod'da proxy mode aktif, direct mode kodu (OpenAI/Anthropic SDK) emekli edilir
- [ ] Engine'i tamamen `expose`-only yap (frontend backend proxy'sini bitirdikten sonra)
- [ ] `engine/ai_synthetic_data/`, `engine/evals/` backend'e merge et
- [ ] 2026-06-01 sonrası deprecated endpoint'leri sil

## İlgili

- [ADR-0001](0001-monorepo-yapisi.md)
- [docs/architecture/engine-backend-contract.md](../architecture/engine-backend-contract.md)
