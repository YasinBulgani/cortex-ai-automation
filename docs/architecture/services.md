# Cortex AI Automation — Service Map

> Canonical reference for the 4 Python service boundaries.
> Updated: 2026-05-23

## Services

| Service | Directory | Port | Tech | Status |
|---------|-----------|------|------|--------|
| **Backend** | `backend/` | 8000 | FastAPI + Postgres | Canonical API server |
| **Engine** | `engine/` | 8010 | Python (CLI + worker) | AI test generation engine |
| **AI Gateway** | `ai-gateway/` | 8020 | FastAPI | LLM routing + caching |
| **Cortex Dashboard** | `frameworks/cortex-java/python_server/` | 5001 | Flask | Local dev only — Java recorder + Playwright runner |

---

## Ownership Rules

### Backend (`backend/`)
- Authentication, authorization, multi-tenancy (Postgres RLS)
- Project / scenario / execution CRUD
- Real-time events (WebSocket or SSE)
- REST API for the frontend (`apps/web`)
- **Consumer:** `apps/web` exclusively

### Engine (`engine/`)
- Stateless AI test generation pipeline
- Receives a spec (URL / user story / OpenAPI) → returns `.feature` file
- Called by Backend as a job worker (Celery or direct subprocess)
- No HTTP server in production — runs as a worker process
- **Consumer:** Backend only

### AI Gateway (`ai-gateway/`)
- Single ingress for all LLM calls (Ollama, OpenAI, custom)
- Prompt caching, rate limiting, model selection
- **Consumer:** Backend, Engine (never called directly from frontend)

### Cortex Dashboard (Flask)
- **Local dev only** — runs on developer machine
- Proxies Playwright recorder, serves screenshots, proxies Ollama
- Port 5001; not deployed to production
- **Consumer:** `apps/web` NEXT_PUBLIC_CORTEX_DASHBOARD_URL (localhost)

---

## Migration Path

| Phase | Goal | Target |
|-------|------|--------|
| Q3 2026 | Consolidate Engine into Backend workers | Remove `engine/` as standalone |
| Q3 2026 | AI Gateway → Backend middleware | Remove `ai-gateway/` |
| Q4 2026 | Flask dashboard → packaged Electron helper | Remove from monorepo |

---

## Decision Log

- `docs/adr/0002-engine-vs-backend-ayirimi.md` — why engine is separate today
- `docs/ADR-001-backend-engine-separation.md` — initial separation rationale

---

## Port Map (local dev)

```
3000  apps/web (Next.js)
5001  Cortex Dashboard (Flask)
8000  Backend (FastAPI)
8010  Engine (worker — no HTTP)
8020  AI Gateway (FastAPI)
5432  Postgres
6379  Redis
11434 Ollama
```
