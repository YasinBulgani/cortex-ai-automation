# ADR-0012: Frontend Backend-First Data Loading Pattern

## Status

Accepted

## Date

2026-05-27

## Context

Frontend hooks in the Neurex QA platform were originally implemented as localStorage-only solutions. This caused a critical data consistency problem: after backend updates (e.g., knowledge base entries saved via API, custom dashboard configurations updated server-side), the frontend continued displaying stale cached data from localStorage. Users had to manually clear browser storage or do hard reloads to see fresh data, which was unacceptable for a QA platform where data accuracy is paramount.

The core tension:
- **Instant perceived load**: localStorage gives zero-latency initial render, avoiding loading spinners on every navigation
- **Data freshness**: backend is the authoritative source; local cache can become stale after any server-side mutation

## Decision

All data hooks follow a **backend-first pattern** with a two-phase load:

1. **Phase 1 — Instant display**: On mount, read from localStorage immediately and render. This gives the user instant feedback with no spinner.
2. **Phase 2 — Async authoritative fetch**: Concurrently fire an async request to the backend API. If the backend responds successfully, overwrite the localStorage cache with the authoritative data and re-render.

If the backend is unavailable or returns an error, the locally cached data remains visible (graceful degradation). If the backend returns fresh data, it silently replaces the stale cache.

```typescript
// Canonical pattern
function useBackendFirstHook<T>(localKey: string, apiEndpoint: string) {
  const [data, setData] = useState<T | null>(() => {
    // Phase 1: instant local read
    try {
      const raw = localStorage.getItem(localKey);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    // Phase 2: async backend fetch
    let cancelled = false;
    fetch(apiEndpoint)
      .then((res) => res.ok ? res.json() : Promise.reject(res.status))
      .then((fresh: T) => {
        if (cancelled) return;
        localStorage.setItem(localKey, JSON.stringify(fresh));
        setData(fresh);
      })
      .catch(() => { /* backend unavailable — keep local data */ });
    return () => { cancelled = true; };
  }, []);

  return data;
}
```

## Reference Implementations

- `apps/web/hooks/useKnowledgeBase.ts` — knowledge base entries backend-first hook
- `apps/web/hooks/useCustomDashboard.ts` — custom dashboard configuration backend-first hook

## Consequences

### Positive

- **Instant perceived load**: Users see data immediately on navigation without loading spinners.
- **Data freshness**: Backend always wins; stale localStorage data is corrected silently within milliseconds of a successful fetch.
- **Graceful offline degradation**: If backend is unreachable, the last known good data is still displayed.
- **No user action required**: No manual cache clearing or hard reloads needed after server-side updates.

### Negative / Trade-offs

- **Requires backend endpoints**: Each domain that adopts this pattern must have a corresponding `GET /api/v1/{domain}` endpoint that returns the full current state for the authenticated user.
- **Potential flicker**: In rare cases where locally cached data differs significantly from backend data, users may see a brief content swap. Mitigated by optimistic rendering and stable data schemas.
- **Duplicate state**: Data exists in both localStorage and backend DB, requiring sync discipline (always write to backend first, then update local cache on success).

### Neutral

- Pattern is additive — existing localStorage-only hooks can be migrated incrementally.
- Each hook is independently testable: Phase 1 (sync init) and Phase 2 (async fetch) can be tested separately.
