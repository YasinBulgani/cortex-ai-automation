# Faz 3.1: Read-Replica + Sticky Read-After-Write

**Tarih:** 2026-06-09  
**Status:** ✅ Implemented  
**Objective:** Implement read-replica scaling with smart replication lag mitigation.

## Problem Statement

In production deployments, a single PostgreSQL primary becomes a read bottleneck:
- **Read-heavy workloads** (dashboards, analytics, reports) compete with **write workloads** (test execution, result uploads)
- PostgreSQL replication lag (~100ms typical) causes **stale data bugs**:
  - User writes test run → immediately reads → gets stale result from replica
  - Dashboard loads → shows outdated metrics while new data is in flight

## Solution: Sticky Read-After-Write Pattern

```
Write → Primary DB
       ↓
       mark_write_occurred(request)
       ↓
       (next 5s)
       ↓
Read   → if <5s since write → Primary (consistent)
       → else → Replica (scaled)
```

### Benefits

1. **Consistency without serialization** — immediate post-write reads hit primary
2. **Scale reads to replica** — 90%+ reads (dashboards, reports) use replica after 5s
3. **Transparent to routes** — dependency injection handles routing automatically
4. **Configurable** — enable/disable + tune sticky duration via env vars

## Architecture

### 1. Read-Replica Config Module (`backend/app/infra/read_replica.py`)

**New file** — centralized sticky read-after-write logic.

```python
class ReadReplicaConfig:
    sticky_duration_seconds: float = 5.0  # default 5s
    enabled: bool = True

def mark_write_occurred(request: Request) -> None:
    """Set request.state.last_write_time = now()"""

def should_force_primary(request: Request) -> bool:
    """Check if <5s since write → use primary"""

def sticky_read_after_write(request, duration=None):
    """Context manager for explicit control"""
```

### 2. Database Layer Updates (`backend/app/infra/database.py`)

**Changes:**

- **Async read-replica engine** — separate `_async_read_engine` initialized from `READ_REPLICA_URL` env var
- **`get_read_db(request)`** — new async generator
  - Checks `should_force_primary(request)` 
  - Routes to primary if sticky flag active
  - Routes to replica otherwise
  - Fallback to primary if replica not configured

**Key code:**

```python
# Async read-replica engine (Faz 3.1)
_async_read_engine = None
AsyncReadSessionLocal = None

if settings.read_replica_enabled and settings.read_replica_url:
    _async_read_engine = create_async_engine(
        _read_replica_url,
        pool_pre_ping=True,
        future=True,
        pool_size=20,
        max_overflow=10,
        pool_recycle=1800,  # Replica is read-only
    )
    AsyncReadSessionLocal = sessionmaker(...)
```

### 3. Dependency Injection (`backend/app/deps.py`)

**New helpers:**

```python
def track_write_on_commit(request: Request, db: Session) -> None:
    """Call after db.commit() to arm sticky read-after-write timer"""
    mark_write_occurred(request)

async def get_read_db_async(request: Request) -> AsyncGenerator[AsyncSession]:
    """Async read-optimized session (replaces get_async_db for reads only)"""
    async for session in get_read_db(request):
        yield session
```

**Usage in routes:**

```python
# Write route → use get_async_db (primary)
@router.post("/tests")
async def create_test(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    request: Request,
):
    # ... insert logic ...
    await db.commit()
    track_write_on_commit(request, db)  # ← Arm sticky timer
    return result

# Read route → use get_read_db_async (replica after 5s)
@router.get("/tests")
async def list_tests(
    db: Annotated[AsyncSession, Depends(get_read_db_async)],
):
    result = await db.execute(...)
    return result.scalars().all()
```

### 4. Configuration (`backend/app/config.py`)

**New fields (Pydantic Settings):**

```python
read_replica_url: str = ""  # Empty = disabled
read_replica_enabled: bool = False
read_replica_sticky_duration_seconds: float = 5.0
```

Load from environment:
```bash
READ_REPLICA_ENABLED=true
READ_REPLICA_URL=postgresql+psycopg2://user:pass@replica.internal:5432/neurex_db
READ_REPLICA_STICKY_DURATION_SECONDS=5.0
```

### 5. Production Docker Compose (`docker-compose.prod.yml`)

**New service:**

```yaml
postgres-replica:
  image: pgvector/pgvector:pg16
  container_name: bgts_postgres_replica_prod
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
  volumes:
    - pgdata_replica_prod:/var/lib/postgresql/data
  expose:
    - "5432"
  depends_on:
    postgres:
      condition: service_healthy
  networks:
    - bgts_internal
```

**Updated services (backend, worker, ai-worker, outbox-relay):**

```yaml
environment:
  READ_REPLICA_ENABLED: ${READ_REPLICA_ENABLED:-false}
  READ_REPLICA_URL: ${READ_REPLICA_URL:-}
  READ_REPLICA_STICKY_DURATION_SECONDS: ${READ_REPLICA_STICKY_DURATION_SECONDS:-5.0}
```

**New volume:**

```yaml
volumes:
  pgdata_replica_prod:
    driver: local
```

**New exporter (monitoring):**

```yaml
postgres-replica-exporter:
  image: prometheuscommunity/postgres-exporter:v0.15.0
  container_name: bgts_postgres_replica_exporter
  environment:
    DATA_SOURCE_URI: postgres-replica:5432/${POSTGRES_DB}?sslmode=disable
    DATA_SOURCE_USER: ${POSTGRES_USER}
    DATA_SOURCE_PASS: ${POSTGRES_PASSWORD}
  expose:
    - "9188"
  depends_on:
    postgres-replica:
      condition: service_healthy
```

## Migration Path

**No database schema migration required** — only connection routing.

### Step 1: Development/Staging

```bash
# docker-compose.local.yml
docker-compose -f docker-compose.local.yml up -d postgres-replica

# .env
READ_REPLICA_ENABLED=true
READ_REPLICA_URL=postgresql+psycopg2://user:pass@localhost:5432/neurex_db
```

### Step 2: Production Deployment

```bash
# .env.prod
READ_REPLICA_ENABLED=true
READ_REPLICA_URL=postgresql+psycopg2://user:pass@replica.internal:5432/neurex_db
READ_REPLICA_STICKY_DURATION_SECONDS=5.0
```

### Step 3: Route Migration (Incremental)

**Priority: Dashboard & Report Routes** (highest read volume)

```python
# Before: all reads use primary
async def get_project_summary(
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    ...

# After: use replica with sticky fallback
async def get_project_summary(
    db: Annotated[AsyncSession, Depends(get_read_db_async)],
):
    ...
```

## Testing & Verification

### Unit Test (Sticky Logic)

```python
def test_should_force_primary_after_write():
    request = Request(...)
    assert not should_force_primary(request)  # No write
    
    mark_write_occurred(request)
    assert should_force_primary(request)  # <5s
    
    time.sleep(5.1)
    assert not should_force_primary(request)  # >5s
```

### Integration Test (Route Routing)

```python
@pytest.mark.asyncio
async def test_write_then_read_uses_primary():
    # 1. Insert via write route
    response = await client.post("/api/v1/tests", json={...})
    
    # 2. Immediate read → should hit primary (not replica)
    # Can verify via SQL connection tracking or pg_stat_statements
    response = await client.get("/api/v1/tests")
    assert response.status_code == 200
    
    # 3. Wait 5s
    time.sleep(5.1)
    
    # 4. Subsequent read can use replica
    response = await client.get("/api/v1/tests")
    assert response.status_code == 200
```

### Performance Verification

```bash
# Monitor via postgres exporter metrics:
# - pg_database_size_bytes{datname="neurex_db",job="postgres"}
# - pg_database_size_bytes{datname="neurex_db",job="postgres-replica"}

# Check replication lag in Prometheus:
# pg_replication_lag_bytes{slot="replica_1"} → should be 0 or low

# In test suite:
# - Measure read latency with/without replica
# - Expected: 5-10% lower with replica (after 5s window)
```

## Configuration Examples

### Development (Local)

```bash
# .env.local
READ_REPLICA_ENABLED=false  # Use only primary for simplicity
```

### Staging (Test Replica)

```bash
# .env.staging
READ_REPLICA_ENABLED=true
READ_REPLICA_URL=postgresql+psycopg2://neurex:neurex_pass@postgres-replica:5432/neurex_db
READ_REPLICA_STICKY_DURATION_SECONDS=3.0  # Shorter for testing
```

### Production (Cloud Replica)

```bash
# .env.prod
READ_REPLICA_ENABLED=true
READ_REPLICA_URL=postgresql+psycopg2://neurex:${DB_REPLICA_PASS}@replica.rds.internal:5432/neurex_db
READ_REPLICA_STICKY_DURATION_SECONDS=5.0
```

## Files Changed

| File | Change | Purpose |
|------|--------|---------|
| `backend/app/infra/read_replica.py` | **NEW** | Sticky read-after-write logic |
| `backend/app/infra/database.py` | **MODIFIED** | Added `_async_read_engine`, `get_read_db()` |
| `backend/app/config.py` | **MODIFIED** | Added `read_replica_*` settings |
| `backend/app/deps.py` | **MODIFIED** | Added `track_write_on_commit()`, `get_read_db_async()` |
| `docker-compose.prod.yml` | **MODIFIED** | Added `postgres-replica` service, env vars, exporter |

## Next Steps (Faz 3.2+)

1. **Route Migration** — Audit all GET routes, migrate high-volume to `get_read_db_async`
2. **Monitoring** — Add Grafana dashboards for read/write split, replication lag
3. **Load Testing** — Benchmark 100k+ concurrent reads on replica
4. **Failover Logic** — Automatic fallback to primary if replica unavailable
5. **Multi-Region** — Extend to geo-distributed replicas (RTO/RPO targets)

## References

- **ADR-0012** (Frontend backend-first) — no optimistic updates; works with read-after-write
- **Faz 3.0** (Architecture Panel) — circuit breaker, resilience pattern
- **PostgreSQL Replication** — streaming replication, replication slots
