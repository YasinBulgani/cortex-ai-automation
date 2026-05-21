# Engine ↔ Backend Contract

Bu doküman `engine/` (Flask, port 5001) ve `backend/` (FastAPI, port 8000) servislerinin ilişkisini tanımlar.

## Karar: İki servis ayrı kalıyor

**ADR-0002** (bkz. `docs/adr/0002-engine-vs-backend-ayirimi.md`) ile iki servisi birleştirmemeye karar verildi. Ana sebepler:

- Engine'in **Flask session auth** + **37 blueprint** + **kendi HTML UI**'ı var
- FastAPI'ye port etme tahmini: 2 hafta, yüksek regresyon riski
- Servisler zaten gevşek bağlı: yalnızca `X-Internal-Key` header ile HTTP üzerinden konuşuyorlar, direkt Python import'u yok

## Rol ayrımı (hedef)

| Sorumluluk | Engine | Backend | Not |
|---|---|---|---|
| Test runtime (Playwright, pytest-bdd) | ✅ | ❌ | Engine tek sahip |
| Allure/rapor üretimi | ✅ | ❌ | Engine tek sahip |
| BDD feature yönetimi | ✅ | ❌ | Engine tek sahip |
| Screenshot/video capture | ✅ | ❌ | Engine tek sahip |
| TSPM (test süreç yönetimi) | ❌ | ✅ | Backend tek sahip |
| Auth (JWT, kullanıcı yönetimi) | ❌ | ✅ | Backend tek sahip |
| AI Gateway/LLM routing | ❌ | ✅ | Backend tek sahip (hedef durum — bkz. "Emekli edilenler") |
| Sentetik veri üretimi | ❌ | ✅ | Backend tek sahip |
| Audit, evals, notifications | ❌ | ✅ | Backend tek sahip |
| CI/CD, n8n orchestration | ❌ | ✅ | Backend tek sahip |

## İletişim kontratı

### 1. Backend → Engine çağrıları

Backend, engine'in test runtime endpoint'lerini `X-Internal-Key` header'ı ile çağırır.

```python
# backend/app/domains/automation/engine_client.py (önerilen yol)
headers = {"X-Internal-Key": settings.ENGINE_INTERNAL_KEY}
response = await httpx.post(
    f"{settings.ENGINE_BASE_URL}/api/runner/execute",
    json=payload,
    headers=headers,
    timeout=30.0,
)
```

**Kullanılan endpoint'ler:**
- `POST /api/runner/execute` — tek test çalıştır
- `POST /api/runner/batch` — paralel batch
- `GET /api/runner/runs/{id}` — run detayı
- `POST /api/pipeline/manual-to-automation` — manuel test → Gherkin pipeline
- `POST /api/scheduler/*` — zamanlanmış run'lar
- `POST /api/mobile/run` — mobil test run
- `GET /api/feature/*` — feature/locator CRUD

### 2. Engine → AI Gateway çağrıları (Faz 4.C — feature flag ile hazır)

Engine'in `LLMGateway` artık iki moda sahiptir:

**Direct mode** (varsayılan): OpenAI/Anthropic SDK'sı ile doğrudan.

**Proxy mode** (env `ENGINE_LLM_USE_GATEWAY=1` ile açılır): `POST /ai/complete`
çağrısı AI Gateway'e yönlenir.

```python
# engine/services/llm_gateway.py — proxy mode
httpx.post(
    f"{AI_GATEWAY_BASE_URL}/ai/complete",
    headers={"X-Internal-Key": GATEWAY_INTERNAL_KEY},
    json={"task_type": "...", "messages": [...], "temperature": 0.2, ...},
)
```

Bu mod tek merkezli provider fallback (Groq → Gemini → Ollama → g4f) sağlar;
PII sanitization engine tarafında ayrıca yapılır (defense-in-depth).

Aktivasyon planı:
1. ✅ Feature flag + adapter eklendi (default kapalı)
2. ✅ Unit testler eklendi (`test_llm_gateway_proxy.py`)
3. ⏳ Staging'de açılacak, 1 hafta gözlem (smoke + evals)
4. ⏳ Prod'da açılacak, 1 hafta gözlem
5. ⏳ Direct mode kodu (OpenAI/Anthropic SDK çağrıları) emekli edilecek

### 3. Kimlik doğrulama

| Yön | Mekanizma | Değer |
|---|---|---|
| Backend → Engine | HTTP header `X-Internal-Key` | `ENGINE_INTERNAL_KEY` (env) |
| Engine → Backend | HTTP header `X-Internal-Key` | `BACKEND_INTERNAL_KEY` (env, ileride) |
| Frontend → Backend | JWT Bearer | OAuth flow |
| Frontend → Engine | **YASAK** — backend'den proxy'lenecek | — |

### 4. Ağ topolojisi (hedef)

```
┌────────────┐        ┌──────────────┐        ┌──────────────┐
│  Frontend  │───────▶│   Backend    │───────▶│    Engine    │
│ :3000 pub  │  JWT   │  :8000 pub   │  IKey  │ :5001 INT    │
└────────────┘        └──────────────┘        └──────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  AI Gateway  │
                      │  :8080 int   │
                      └──────────────┘
```

**Not:** Engine'in `:5001` portu şu an dışa açık. Hedef: sadece internal docker ağından erişilebilir. `docker-compose.yml`'de `ports:` yerine `expose:` kullanılacak.

## Emekli edilen engine endpoint'leri

Şu route'lar backend tarafındaki FastAPI router'larıyla çakışıyor. Engine'den çıkarılacak (Faz 4.C):

| Engine endpoint | Backend alternatifi | Sunset tarihi |
|---|---|---|
| `engine/routes/banking_routes.py` | `backend/app/domains/ai_synthetic_data/` | 2026-06-01 |
| `engine/routes/datasim_routes.py` | `backend/app/domains/ai_synthetic_data/` | 2026-06-01 |
| `engine/routes/datasim_banking_routes.py` | `backend/app/domains/ai_synthetic_data/` | 2026-06-01 |
| `engine/routes/analytics_routes.py` | `backend/app/domains/tspm/` | 2026-07-01 |
| `engine/services/llm_gateway.py` | `backend/app/domains/ai/gateway_client.py` | 2026-06-01 |
| `engine/evals/` | `backend/app/domains/evals/` | 2026-07-01 |
| `engine/ai_synthetic_data/` | `backend/app/domains/ai_synthetic_data/` | 2026-07-01 |

Sunset header'ı ile önce deprecated işaretlenir:

```python
# engine/app.py
DEPRECATED_ROUTES = {"/api/banking", "/api/datasim", "/api/ai/generate"}

@app.after_request
def mark_deprecation(response):
    if any(request.path.startswith(p) for p in DEPRECATED_ROUTES):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Wed, 01 Jun 2026 00:00:00 GMT"
        response.headers["Link"] = '</docs/architecture/engine-backend-contract.md>; rel="deprecation"'
    return response
```

## Hata taksonomisi

Hem engine hem backend şu hata yanıt şemasını döner:

```json
{
  "error": {
    "code": "ENGINE.RUNNER.TIMEOUT",
    "message": "Test execution exceeded 300s timeout",
    "request_id": "req_abc123",
    "retryable": true
  }
}
```

Kod prefix'leri:
- `ENGINE.*` — engine-side (runner, feature, mobile, recorder)
- `BACKEND.*` — backend-side (auth, tspm, ai, synthetic-data)
- `GATEWAY.*` — ai-gateway (provider fallback, rate limit)

## Health/Readiness

| Servis | Endpoint | Dönüş |
|---|---|---|
| Engine | `GET /health` | `{"status": "ok", "version": "...", "uptime_s": N}` |
| Backend | `GET /health` | `{"status": "ok", "db": "up", "redis": "up"}` |
| AI Gateway | `GET /health` | `{"status": "ok", "providers": {...}}` |

`docker-compose.yml`'de `healthcheck` tanımlı — `depends_on.condition: service_healthy`.

## Timeout ve retry

Backend → Engine:

| Endpoint türü | Timeout | Retry |
|---|---|---|
| Sync CRUD (feature, locator) | 10 s | 2× exponential |
| Test execution (runner) | 300 s | **0** — idempotent değil |
| Streaming (SSE) | 600 s | 0 |
| Health | 2 s | 1 |

## Gözlemlenebilirlik

Her internal HTTP çağrısında:
- `X-Request-Id` header'ı (ulaşan her iki tarafta log'lanır)
- `X-Forwarded-User-Id` (backend'den engine'e kullanıcı kontextini geçirmek için)
- OpenTelemetry trace propagation (`traceparent` header)

## Test stratejisi (bu kontrat için)

- **Contract tests**: `api-tests/contracts/engine_backend/` — her public endpoint için schema doğrulaması
- **Integration tests**: `backend/tests/integration/test_engine_proxy.py` — mock engine ile backend davranışı
- **E2E**: `e2e/flows/` — frontend → backend → engine tam akış

## Uygulama fazları

| Faz | İş | Tahmini efor |
|---|---|---|
| 4.A | Bu kontrat dokümanı + ADR-0002 | ✅ Tamam |
| 4.B | Engine'i internal ağa taşı (docker-compose port → expose) | 2 saat |
| 4.C | Engine LLM çağrıları → backend proxy'ye yönlendir | 1 gün |
| 4.D | Çakışan endpoint'lere `Sunset` header ekle | 2 saat |
| 4.E | 6 ay sonra (2026-10) emekli endpoint'leri sil | — |

## İlgili dokümanlar

- [ADR-0001: Monorepo yapısı](../adr/0001-monorepo-yapisi.md)
- [ADR-0002: Engine/Backend ayrımı](../adr/0002-engine-vs-backend-ayirimi.md)
- [ADR-0003: Synthetic-data konsolidasyonu](../adr/0003-synthetic-data-konsolidasyonu.md)
