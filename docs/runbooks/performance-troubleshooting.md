# Performance Troubleshooting Runbook

**Maintainer:** Platform Team  
**Last Updated:** 2026-05-27  
**Applies to:** Neurex QA Platform (backend, engine, database, frontend)

---

## 1. Quick Diagnostics

Run these checks first to get a baseline before diving into component-specific investigation.

### Health & Metrics Endpoints

```bash
# Backend health (includes db, redis, engine connectivity)
curl -s http://localhost:8000/api/health | jq .

# Backend metrics (Prometheus format)
curl -s http://localhost:8000/api/metrics

# Engine health
curl -s http://localhost:5001/health | jq .

# Prometheus metrics (if running)
curl -s http://localhost:9090/api/v1/query?query=up
```

### Container Resource Usage

```bash
# Live container CPU and memory
docker stats --no-stream

# Identify resource-hungry containers
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### System-Level Baseline

```bash
# Disk usage (full disk causes slowdowns and crashes)
df -h

# Available memory
free -h   # Linux
vm_stat   # macOS

# Load average (should stay below number of CPU cores)
uptime
```

### Prometheus Metrics to Check First

| Metric | Concern Threshold | What to Do |
|--------|------------------|------------|
| `http_request_duration_seconds_p99` | > 2s | Check slow endpoints (Section 2.1) |
| `process_resident_memory_bytes` (backend) | > 1 GB | Check in-memory stores (Section 2.2) |
| `process_cpu_seconds_total` rate | sustained > 80% | Check LLM calls (Section 2.3) |
| `postgresql_active_connections` | > 80% of `max_connections` | Check DB (Section 4) |
| `redis_connected_clients` | > 100 | Check Redis configuration |

---

## 2. Backend Performance

### 2.1 Slow API Endpoints

**Symptoms:** Response times > 1s for non-AI endpoints; users report UI sluggishness; Prometheus `http_request_duration_seconds_p99` is elevated.

**Identify the slowest endpoints:**
```bash
# Check access logs for slow requests (> 1000ms)
docker compose logs backend | grep -E '"[0-9.]+" [0-9]+ [0-9]{4,}' | tail -30

# Or via Prometheus query (if connected to Grafana):
# topk(10, rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]))
```

**Common cause — SQLAlchemy N+1 queries:**

N+1 occurs when a list endpoint issues one query per item instead of a single JOIN. Identify it by counting queries in logs:
```bash
# Enable SQLAlchemy query logging temporarily
# In backend/.env or docker-compose.yml:
# SQLALCHEMY_ECHO=true
docker compose up -d backend

# Then hit the slow endpoint and watch logs:
docker compose logs -f backend | grep "SELECT"
```

**Fix N+1 — add `selectinload` or `joinedload`:**
```python
# Before (N+1):
results = db.query(TestRun).all()
for r in results:
    print(r.project.name)  # triggers one query per row

# After (single query):
from sqlalchemy.orm import selectinload
results = db.query(TestRun).options(selectinload(TestRun.project)).all()
```

For bulk list endpoints, prefer `selectinload` (avoids cartesian product). For single-item detail pages, `joinedload` is fine.

**Add database indexes for frequently filtered columns:**
```python
# In SQLAlchemy model:
class TestRun(Base):
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    status = Column(String, index=True)
    created_at = Column(DateTime, index=True)
```

Generate and apply the migration:
```bash
docker compose exec backend alembic revision --autogenerate -m "add_index_test_runs_project_id"
docker compose exec backend alembic upgrade head
```

---

### 2.2 High Memory Usage

**Symptoms:** Backend container memory grows over time and does not stabilize; Docker stats shows > 1 GB; container is eventually OOM-killed.

**Identify memory sources:**
```bash
# Check current memory
docker stats --no-stream neurex-backend

# Check in-memory store sizes via debug endpoint (if available)
curl -s http://localhost:8000/api/debug/memory | jq .
```

**Common cause — unbounded in-memory stores:**

The knowledge base (KB), notification store, and similar in-memory collections can grow without bound if `maxlen` is not set.

```python
# Before (unbounded — memory leak risk):
_kb_store: list = []
_notifications: list = []

# After (bounded with deque):
from collections import deque
_kb_store: deque = deque(maxlen=10_000)
_notifications: deque = deque(maxlen=5_000)
```

Locations to check:
- `backend/app/services/knowledge_base.py` — KB in-memory store
- `backend/app/services/notification_service.py` — notification queue
- `backend/app/routers/ai_workflows.py` — workflow state cache
- Any service-level `dict` or `list` accumulating items without eviction

**Fix — set maxlen on deques, or switch to Redis-backed cache for large stores.**

After fixing, restart the backend and monitor memory for 30 minutes:
```bash
docker compose restart backend
watch -n 10 "docker stats --no-stream neurex-backend"
```

---

### 2.3 CPU Spikes

**Symptoms:** Backend CPU sustained > 80%; response times degrade; other containers are starved of CPU.

**Identify the hot path:**
```bash
# Check if LLM gateway calls are blocking the event loop
docker compose logs backend | grep -i "llm\|openai\|anthropic\|gateway" | tail -50

# Profile CPU (if py-spy is available in the container)
docker compose exec backend py-spy top --pid 1
```

**Common cause — synchronous LLM gateway calls blocking the async event loop:**

```python
# Before (blocking — starves other requests):
def generate_test(prompt: str) -> str:
    response = openai_client.chat.completions.create(...)  # synchronous
    return response.choices[0].message.content

# After (non-blocking — allows concurrent requests):
async def generate_test(prompt: str) -> str:
    response = await async_openai_client.chat.completions.create(...)
    return response.choices[0].message.content
```

Also check for CPU-intensive operations being done in the request path:
- Large JSON serialization (paginate or stream instead)
- Regex matching on large strings without caching
- Image/screenshot processing without offloading to a background task

**Fix — move heavy CPU work to background tasks (FastAPI `BackgroundTasks` or Celery):**
```python
from fastapi import BackgroundTasks

@router.post("/generate")
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    task_id = create_pending_task()
    background_tasks.add_task(run_generation, task_id, request)
    return {"task_id": task_id, "status": "pending"}
```

---

## 3. Engine Performance

### 3.1 Test Runs Are Slow

**Symptoms:** Playwright test execution takes significantly longer than expected; timeout errors in engine logs; test queue backs up.

**Diagnose:**
```bash
docker compose logs engine | grep -i "timeout\|slow\|duration" | tail -50
```

**Check Playwright timeout settings:**
```python
# engine/config.py or engine/playwright_runner.py
PLAYWRIGHT_TIMEOUT = 30_000          # Default: 30s per action
PLAYWRIGHT_NAVIGATION_TIMEOUT = 60_000  # Default: 60s for page loads

# If pages are legitimately slow, increase thoughtfully:
PLAYWRIGHT_TIMEOUT = 45_000
```

**Check parallel runner configuration:**
```python
# engine/parallel_runner.py
MAX_WORKERS = 4   # Number of concurrent Playwright browsers

# If system is resource-constrained:
MAX_WORKERS = 2
```

Verify engine container has enough resources:
```bash
# Check if engine is CPU or memory constrained
docker stats --no-stream neurex-engine
```

Increase engine container resources in `docker-compose.yml` if needed:
```yaml
engine:
  deploy:
    resources:
      limits:
        cpus: "2.0"
        memory: 2G
```

---

### 3.2 AI Generation Is Slow

**Symptoms:** AI test case or scenario generation takes > 30 seconds; users see loading spinners for a long time; engine logs show long waits for LLM responses.

**Check which model is being used:**
```bash
docker compose exec engine env | grep -i "model\|llm\|openai"
```

**Check the fallback chain configuration:**
```python
# engine/services/llm_gateway.py
LLM_PROVIDERS = [
    {"provider": "openai",    "model": "gpt-4o",       "timeout": 30},
    {"provider": "openai",    "model": "gpt-4o-mini",  "timeout": 20},  # faster fallback
    {"provider": "anthropic", "model": "claude-haiku-4-6", "timeout": 15},  # cheapest/fastest
]
```

**Common fixes:**
- Switch to a faster model for less complex generation tasks (e.g., `gpt-4o-mini` instead of `gpt-4o`)
- Add response streaming so users see partial output sooner
- Cache repeated generation results (same prompt → same output) with Redis:
  ```python
  cache_key = hashlib.md5(prompt.encode()).hexdigest()
  cached = redis_client.get(cache_key)
  if cached:
      return json.loads(cached)
  result = await llm_generate(prompt)
  redis_client.setex(cache_key, 3600, json.dumps(result))
  return result
  ```
- Reduce prompt size by trimming context that is not needed

---

## 4. Database Performance

### 4.1 Check Active Queries

```sql
-- Connect to postgres
docker compose exec postgres psql -U neurex -d neurex_db

-- Show currently active queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
ORDER BY duration DESC;

-- Show blocking queries
SELECT blocked_locks.pid     AS blocked_pid,
       blocked_activity.usename AS blocked_user,
       blocking_locks.pid    AS blocking_pid,
       blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.relation = blocked_locks.relation
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

### 4.2 Enable Slow Query Logging

Add to `docker-compose.yml` postgres command:
```yaml
postgres:
  command: >
    postgres
    -c log_min_duration_statement=1000
    -c log_statement=none
    -c log_destination=stderr
```

Then watch for slow queries:
```bash
docker compose logs -f postgres | grep "duration:"
```

### 4.3 Check Table Bloat and Vacuum

```sql
-- Tables with most dead tuples (need vacuum)
SELECT schemaname, tablename, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric/NULLIF(n_live_tup,0)*100, 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 20;

-- Manually vacuum if needed
VACUUM ANALYZE test_runs;
VACUUM ANALYZE llm_traces;
```

### 4.4 Connection Pool Exhaustion

**Symptom:** Requests hang; backend logs show `QueuePool limit of size X overflow Y reached`.

```bash
# Check current connection count
docker compose exec postgres psql -U neurex -c "SELECT count(*) FROM pg_stat_activity;"
```

**Fix — adjust pool settings in backend config:**
```python
# backend/app/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,        # Increase from default 5
    max_overflow=10,     # Overflow connections allowed
    pool_timeout=30,     # Wait up to 30s for a connection
    pool_pre_ping=True,  # Detect stale connections
)
```

---

## 5. Frontend Performance

### 5.1 React Re-render Profiling

**Symptoms:** UI feels sluggish; interactions cause noticeable lag; browser DevTools shows long tasks.

**Quick check in browser:**
1. Open Chrome DevTools → Performance tab
2. Record a 5-second interaction with the slow UI
3. Look for long tasks (> 50ms) in the flame chart

**Common causes and fixes:**

| Cause | Fix |
|-------|-----|
| Missing `key` prop in list renders | Add stable unique `key` to each list item |
| Expensive computation in render | Wrap with `useMemo` |
| Callback recreated on every render | Wrap with `useCallback` |
| Parent re-render cascades to all children | Wrap child with `React.memo` |
| Large state object causing full re-render | Split into smaller state atoms |

**Example — memoize expensive computation:**
```tsx
// Before (runs on every render):
const sortedTests = tests.sort((a, b) => b.createdAt - a.createdAt);

// After (only recomputes when `tests` changes):
const sortedTests = useMemo(
  () => [...tests].sort((a, b) => b.createdAt - a.createdAt),
  [tests]
);
```

### 5.2 Bundle Size

**Check current bundle size:**
```bash
cd apps/web
npx next build 2>&1 | grep -A 20 "Route (app)"
```

**Targets:**
- First load JS shared: < 200 KB
- Individual route chunks: < 100 KB
- Total initial load: < 500 KB

**Common fixes:**
- Use dynamic imports for heavy components:
  ```tsx
  const HeavyChart = dynamic(() => import('./HeavyChart'), { ssr: false });
  ```
- Audit large dependencies with `npx @next/bundle-analyzer`:
  ```bash
  ANALYZE=true npx next build
  ```
- Replace heavy libraries with lighter alternatives (e.g., `date-fns` instead of `moment`)

### 5.3 Lighthouse Scores

Run a Lighthouse audit for the main dashboard:
```bash
# Using Lighthouse CLI
npx lighthouse http://localhost:3000/p/test-project --output json --quiet \
  | jq '.categories | {performance: .performance.score, accessibility: .accessibility.score}'
```

**Minimum targets:**
| Category | Target |
|----------|--------|
| Performance | > 70 |
| Accessibility | > 90 |
| Best Practices | > 85 |
| SEO | > 80 |

**Common performance improvements:**
- Add `loading="lazy"` to below-the-fold images
- Preconnect to external APIs: `<link rel="preconnect" href="https://api.openai.com" />`
- Enable Next.js image optimization (`next/image` instead of `<img>`)
- Ensure critical CSS is inlined (Next.js does this by default with App Router)

---

## Quick Reference — Diagnostic Commands

```bash
# All-in-one status check
docker compose ps && curl -s http://localhost:8000/api/health | jq . && docker stats --no-stream

# Recent errors across all containers
docker compose logs --since 10m 2>&1 | grep -iE "error|critical|exception|fatal" | tail -30

# Postgres slow queries (last 10 minutes)
docker compose exec postgres psql -U neurex -d neurex_db \
  -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Redis memory usage
docker compose exec redis redis-cli info memory | grep used_memory_human

# Engine Playwright browser count
docker compose exec engine ps aux | grep chromium | wc -l
```
