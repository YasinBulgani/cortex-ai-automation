# ADR 0003: DDD Bounded Contexts in Backend

**Status**: Accepted
**Date**: 2026-05-14

## Context

Backend has 40+ flat `domains/` folders. Cross-domain coupling unclear, no consistency around persistence/business logic separation.

## Decision

Reorganize into **bounded contexts** with **layered architecture**:

```
backend/app/contexts/
├─ _shared/               — kernel, events, outbox (cross-context)
├─ identity/              — User, Auth, RBAC
│  ├─ domain/             — pure logic (no DB, no FastAPI)
│  ├─ application/        — use cases (commands, handlers)
│  ├─ infrastructure/     — SQLAlchemy, Redis, JWT
│  └─ api/                — FastAPI routes
├─ projects/              — Project lifecycle
├─ scenarios/             — Test scenarios + DSL
├─ execution/             — Test runners + jobs
├─ ai/                    — AI agents + LLM
├─ data/                  — Synthetic data + privacy
└─ reporting/             — Analytics + dashboards
```

### Cross-context communication
**ONLY via domain events** (no direct imports). Identity emits `UserRegistered` → Notifications subscribes.

### Layered rules
- Domain: zero external deps (no SQLAlchemy, no FastAPI)
- Application: depends on domain only (orchestrates via Protocols)
- Infrastructure: implements Protocols, knows about DB/Redis
- API: HTTP/CLI adapter, depends on application

## Migration Strategy

1. **Phase 1**: Build skeleton + identity context as pattern (✅ done)
2. **Phase 2**: Migrate auth from `domains/auth/` → `contexts/identity/`
3. **Phase 3**: One context per sprint (projects, scenarios, ...)
4. **Phase 4**: Delete legacy `domains/` folder

## Alternatives Considered

- **Hexagonal architecture only** — Less prescriptive about events.
- **Microservices** — Premature; deployment overhead.
- **Keep flat domains** — Existing pain continues.

## Consequences

✅ Clear ownership per context
✅ Testable domain (mock Protocols)
✅ Cross-context decoupled via events
✅ Can split into microservices later if needed
⚠️ Larger upfront learning curve
⚠️ More boilerplate for simple CRUD

## Verification

```bash
cd backend && ./.venv/bin/python -m pytest app/contexts/identity/tests/
# → 14 passed
```
