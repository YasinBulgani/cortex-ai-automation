# Cortex AI Automation — Claude Code Rehberi

## Proje Nedir

AI destekli test otomasyon platformu. Marka adı: **Neurex**. Tam yığın SaaS — test yazımından çalıştırmaya, BDD üretimine, raporlamaya kadar QA süreçlerini otomatize eder.

---

## Servis Mimarisi

```
Next.js (3000) → FastAPI Backend (8000) → PostgreSQL (5432)
                                        → Redis (6379)
                                        → Engine (5001, internal)
                                        → AI Gateway (8080)
```

**AI Gateway fallback chain:** vLLM → Groq → Gemini → Ollama

---

## Hızlı Başlangıç

```bash
make demo                    # Full stack + seed → localhost:3000 (admin@example.com / admin123)
make docker-up               # Sadece postgres + redis
make test-smoke              # 2dk smoke testi
make test-regression         # ~10dk full regression
```

---

## Backend (backend/)

- **FastAPI** — `backend/app/main.py` giriş noktası
- **53 domain** — `backend/app/domains/<domain>/`: router.py, service.py, schemas.py, models.py
- **Router kaydı:** Yeni domain → `backend/app/core/router_registry.py`'a ekle (ZORUNLU)
- **Migrations:** `alembic upgrade head` veya `make migrate`
- **Tests:** `cd backend && pytest` | Unit: `pytest tests/unit/` (DB/Redis gerektirmez)

### Kritik Dosyalar
| Dosya | Amaç |
|-------|------|
| `app/main.py` | Entry point (create_app factory) |
| `app/config.py` | Tüm env var'lar (Pydantic Settings) |
| `app/deps.py` | get_current_user, require_permission |
| `app/core/router_registry.py` | Domain router merkezi kaydı |
| `app/infra/database.py` | DB pool + tenant RLS context |
| `app/infra/models.py` | Core SQLAlchemy modeller (User, Org, Team...) |

---

## Frontend (apps/web/)

- **Next.js 14** App Router, TypeScript strict
- **API proxy:** `/api/v1/*` → backend, `/api/engine/*` → engine, `/api/ai/*` → ai-gateway
- **Dev server:** `npm run dev` (port 3000)

### Kritik Dosyalar
| Dosya | Amaç |
|-------|------|
| `lib/api-client.ts` | API iletişimi + token refresh |
| `lib/useProject.tsx` | Aktif proje context (localStorage) |
| `lib/hooks/use-management.ts` | Management domain hook'ları (70KB) |
| `lib/query-keys.ts` | TanStack Query key factory |
| `components/AppShell.tsx` | Ana layout container |
| `next.config.mjs` | Build config + proxies |

### Backend-First Pattern (ADR-0012 — ZORUNLU)
```typescript
// localStorage'dan anında render → async backend fetch → güncelle
const [data, setData] = useState(() => JSON.parse(localStorage.getItem(key) || 'null'));
useEffect(() => {
  apiClient.get(endpoint).then(fresh => {
    localStorage.setItem(key, JSON.stringify(fresh));
    setData(fresh);
  }).catch(() => {});
}, []);
// YASAK: Optimistic update
```

### Bileşen Kuralı
- Büyük page.tsx → `_components/` alt bileşenlerine ayır
- Alt bileşenler saf sunum (presentational): state/effect YASAK
- Tüm state → parent page.tsx'te

---

## Engine (engine/)

- **Flask** servisi, port 5001 (internal — dışarıdan erişilemez)
- **Auth:** tüm `/api/*` istekleri `X-Internal-Key: <ENGINE_INTERNAL_KEY>` header'ı gerektirir
- **Yeni özellik:** `core/<feature>.py` + `routes/<feature>_routes.py` + `app.py`'ye blueprint kaydı
- **LLM:** `from services import get_llm_gateway; gw.complete(...)` — direkt provider çağırma YASAK
- **Volume mount yok** — kod değişimi için rebuild veya `docker cp + restart`

---

## AI Gateway (ai-gateway/)

- **FastAPI** servisi, port 8080
- Provider fallback: Ollama (local) → vLLM → Groq → Gemini
- Task-specific model routing: ANALYST=qwen2.5:14b, FAST=llama3.1:8b, CODER=qwen2.5-coder:7b
- **Auth:** `GATEWAY_INTERNAL_KEY` header'ı

---

## Test Yazma Kuralları

### Backend Unit Test
```python
# DB/Redis/HTTP bağımlılığı YOK — pure helper test
def test_something():
    result = my_pure_function(input)
    assert result == expected
```

### Yeni TC (QA paketi)
```bash
node qa/tools/new-tc.mjs --domain AUTH   # Yeni test case
node qa/tools/validate.mjs               # Doğrula
node qa/tools/health-check.mjs          # Health score
```

---

## ADR Listesi

| ADR | Karar |
|-----|-------|
| ADR-0012 | Frontend backend-first data loading (optimistic update YASAK) |
| ADR-0013 | Engine test izolasyonu (paylaşımlı fixture YASAK) |
| ADR-0008 | i18n TR/EN desteği |

Yeni ADR: `docs/adr/ADR-NNNN-<başlık>.md`, sıradaki: ADR-0014+

---

## Lint & Type Check

```bash
make lint             # ruff (backend) + eslint (frontend)
cd apps/web && npx tsc --noEmit    # TypeScript type check
```

---

## Önemli Notlar

- **Marka:** Neurex (eski: TestwrightAI, Visium, NexusQA — 2026-06-03 rebrand)
- **Multi-tenancy:** PostgreSQL RLS — tüm sorgular tenant_id ile izole
- **Güvenlik:** Sensitive değerler Sentry'e `[Filtered]` gider
- **i18n:** `useT` hook — TR varsayılan, EN alternatif
- **Gap analiz raporları:** `docs/BACKEND_ISLEVSEL_EKSIKLIK_RAPORU_2026-06-05.md` ve `docs/FRONTEND_ISLEVSEL_EKSIKLIK_RAPORU_2026-06-05.md`
