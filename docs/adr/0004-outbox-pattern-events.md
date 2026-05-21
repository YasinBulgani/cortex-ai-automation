# ADR 0004: Outbox Pattern for Reliable Domain Events

**Status**: Accepted
**Date**: 2026-05-14

## Context

Domain events drive cross-context communication. Without outbox:
- App writes to DB, then publishes event → if crash between, event is lost
- Loss = inconsistency (e.g., welcome email never sent for new users)

## Decision

Outbox pattern:
1. Aggregate emits domain events
2. Repository.save() writes aggregate **AND** events to `outbox` table in **same transaction**
3. Background `OutboxRelay` worker polls outbox, publishes to broker (Redis Streams)
4. Failed entries: exponential backoff up to N retries, then dead-letter queue

## Architecture

```
[Aggregate]──emits──>[Domain Event]
                          │
[Repository.save()]──tx──>[DB: aggregate + outbox row]
                          │
                          ▼
                    [OutboxRelay worker (Celery)]
                          │
                          ▼
                    [Redis Streams broker]
                          │
                          ▼
                    [Subscribers in other contexts]
```

## Schema

```sql
CREATE TABLE outbox (
    id              UUID PRIMARY KEY,
    event_type      TEXT NOT NULL,
    aggregate_id    UUID NOT NULL,
    payload         JSONB NOT NULL,
    metadata        JSONB NOT NULL,
    status          TEXT NOT NULL,  -- pending|processing|delivered|failed|dead
    attempt_count   INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_attempted_at TIMESTAMPTZ,
    error           TEXT
);

CREATE INDEX idx_outbox_pending ON outbox (status, created_at)
    WHERE status IN ('pending', 'failed');
```

## Alternatives Considered

- **2PC (XA transactions)** — Distributed tx fragile.
- **Event-first (publish then save)** — Worse: event without state.
- **Polling without outbox** — DB-only solution loses ordering, retries.

## Consequences

✅ Guaranteed at-least-once event delivery
✅ Atomic with state change
✅ Subscribers can be down — events backed up
⚠️ Eventual consistency (subscribers lag behind)
⚠️ Idempotent processors required (events may duplicate)

## Verification

```python
async def test_outbox_atomicity():
    async with begin_tx() as tx:
        user.register(...)
        await user_repo.save(user)
        # Outbox entry written in same tx — both commit or both rollback
    pending = await outbox.fetch_pending()
    assert len(pending) == 1
```
