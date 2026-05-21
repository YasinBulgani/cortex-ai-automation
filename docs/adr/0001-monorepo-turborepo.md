# ADR 0001: Monorepo with Turborepo

**Status**: Accepted
**Date**: 2026-05-14
**Deciders**: Engineering Team

## Context

Repository was a hybrid: `apps/web` Next.js + standalone `backend/`, `engine/`, `ai-gateway/` Python services. Frontend shared no packages. Each piece had its own build, no incremental cache.

## Decision

Adopt **Turborepo** monorepo with `packages/*` workspace. All shared TS code becomes a published package.

```
apps/        — Next.js, Storybook
packages/    — design-system, contracts, ai-sdk
services/    — Python services (future consolidation)
```

## Alternatives Considered

- **Nx** — More complex, less mature with Next.js integrations.
- **Lerna** — Maintenance mode.
- **Polyrepo** — Cross-package atomic changes painful.

## Consequences

✅ Atomic cross-package changes
✅ Incremental builds (Turbo cache)
✅ Shared packages enforce contracts
⚠️ Migration effort for existing apps to use packages
⚠️ Learning curve for Turbo task config

## Verification

- `npx turbo run type-check test --filter='@neurex/*'`
- Cache hit observed: 5/6 cached, 675ms total
