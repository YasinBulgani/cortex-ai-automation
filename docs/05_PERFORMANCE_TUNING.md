# Neurex Performance Tuning Guide

**Last Updated:** 2026-06-09  
**Target:** Sub-200ms API response times  
**Load Baseline:** 100 concurrent users, 10,000 test cases  
**Status:** Comprehensive tuning playbook

---

## Table of Contents

1. [Performance Baseline](#performance-baseline)
2. [Database Optimization](#database-optimization)
3. [Redis Caching Strategy](#redis-caching-strategy)
4. [API Response Optimization](#api-response-optimization)
5. [Frontend Performance](#frontend-performance)
6. [Monitoring & Profiling](#monitoring--profiling)
7. [Load Testing](#load-testing)
8. [Optimization Checklist](#optimization-checklist)

---

## Performance Baseline

### Current Performance Targets

```
API Latency (p95):      < 200ms
API Latency (p99):      < 500ms
Database Query (p95):   < 50ms
Cache Hit Rate:         > 85%
Frontend LCP:           < 2.5s
Frontend CLS:           < 0.1
Frontend INP:           < 200ms
```

### Baseline Load Test Results (k6)

```bash
# Test configuration
Virtual Users:    100
Duration:         5 minutes
Endpoints:
  - GET /api/v1/test-cases (weight: 40%)
  - POST /api/v1/test-runs (weight: 30%)
  - GET /api/v1/runs/{id}/results (weight: 20%)
  - PATCH /api/v1/defects/{id} (weight: 10%)

Results:
  Requests:       120,000
  Success Rate:   99.5%
  p50 Latency:    85ms
  p95 Latency:    180ms
  p99 Latency:    420ms
  Error Rate:     0.5% (rate limit + transient errors)
```

### Profiling Baseline

```bash
# CPU profile
docker compose exec backend python -m cProfile -o app_cpu.prof app/main.py

# Memory profile
pip install memory_profiler
python -m memory_profiler app/main.py > memory.txt

# Analyze results
python -c "
  import pstats
  stats = pstats.Stats('app_cpu.prof')
  stats.sort_stats('cumtime')
  stats.print_stats(20)  # Top 20 functions
"
```

---

## Database Optimization

### Index Strategy

#### 1. Tenant Isolation Indexes (MANDATORY)

```sql
-- Every query filters by tenant_id first
CREATE INDEX idx_test_cases_tenant_id ON test_cases(tenant_id);
CREATE INDEX idx_test_runs_tenant_id ON test_runs(tenant_id);
CREATE INDEX idx_defects_tenant_id ON defects(tenant_id);

-- Composite indexes for common filters
CREATE INDEX idx_test_cases_tenant_project ON test_cases(tenant_id, project_id);
CREATE INDEX idx_test_runs_tenant_project_status ON test_runs(tenant_id, project_id, status);
```

#### 2. Query Optimization Indexes

```sql
-- Time-series queries (common for reports)
CREATE INDEX idx_test_runs_created_at_desc ON test_runs(created_at DESC);
CREATE INDEX idx_defects_created_at_desc ON defects(created_at DESC);
CREATE INDEX idx_audit_logs_created_at_desc ON audit_logs(created_at DESC);

-- Filtering queries
CREATE INDEX idx_defects_severity_status ON defects(severity, status);
CREATE INDEX idx_test_cases_priority_status ON test_cases(priority, status);
CREATE INDEX idx_test_runs_status ON test_runs(status);

-- Foreign key lookups
CREATE INDEX idx_test_run_results_test_case_id ON test_run_results(test_case_id);
CREATE INDEX idx_test_case_steps_test_case_id ON test_case_steps(test_case_id);
```

#### 3. Vector Similarity Index (pgvector)

```sql
-- For AI-driven test case similarity search
CREATE INDEX idx_test_cases_embedding ON test_cases 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);

-- Tune 'lists' based on table size:
-- < 1M rows: lists = 10-50
-- 1M-10M rows: lists = 50-100
-- > 10M rows: lists = 100-300
```

### Connection Pool Tuning

```python
# backend/app/infra/database.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Connections to keep pooled
    max_overflow=40,           # Additional temporary connections
    pool_timeout=30,           # Wait 30s for connection from pool
    pool_pre_ping=True,        # Verify connections before use
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo_pool=False            # Set to True to debug pool issues
)
```

### Query Optimization

#### Common Slow Patterns

**❌ N+1 Query Problem:**
```python
# SLOW: Fetches user for each case
cases = session.query(TestCase).all()
for case in cases:
    case.created_by.name  # Triggers DB query per case
```

**✅ Solution: Use joinedload**
```python
from sqlalchemy.orm import joinedload

cases = session.query(TestCase).options(
    joinedload(TestCase.created_by)
).all()
```

#### Aggregation Query Optimization

**❌ Slow: Count in application code**
```python
runs = session.query(TestRun).filter(...).all()
pass_count = len([r for r in runs if r.status == 'passed'])  # Memory-heavy
```

**✅ Fast: Use database aggregation**
```python
from sqlalchemy import func

pass_count = session.query(
    func.count(TestRun.id)
).filter(TestRun.status == 'passed').scalar()
```

#### Pagination Optimization

**❌ OFFSET is slow on large tables**
```python
# Page 1000 scans 100,000 rows
query.offset(1000 * page_size).limit(page_size)
```

**✅ Use keyset pagination (cursor-based)**
```python
# Backend implementation
def get_cases_keyset(project_id, limit=50, cursor=None):
    query = TestCase.query.filter_by(project_id=project_id)
    
    if cursor:
        cursor_id, cursor_created = decode_cursor(cursor)
        query = query.filter(
            (TestCase.created_at < cursor_created) |
            ((TestCase.created_at == cursor_created) & (TestCase.id > cursor_id))
        )
    
    cases = query.order_by(TestCase.created_at.desc(), TestCase.id).limit(limit + 1).all()
    
    return {
        'data': cases[:limit],
        'next_cursor': encode_cursor(cases[limit].id, cases[limit].created_at) if len(cases) > limit else None
    }
```

### Statistics & Query Plans

```bash
# Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM test_cases
WHERE tenant_id = $1 AND project_id = $2
ORDER BY created_at DESC
LIMIT 50;

# Update table statistics (done by autovacuum normally)
ANALYZE test_cases;

# Find missing indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename;
```

---

## Redis Caching Strategy

### Cache Architecture

```
┌─ Application ─┐
│ (FastAPI)     │
└────┬──────────┘
     │ (1) Check cache
     ▼
┌─────────────────────────┐
│ Redis (cache layer)     │
│ Key: resource-id        │ ◄─── 85%+ hit rate
│ TTL: 5-3600 seconds     │
└────────┬────────────────┘
         │ (2) If miss, fetch
         ▼
┌─ Database ─┐
│ PostgreSQL │
└────────────┘
```

### Cache Patterns

#### 1. Cache-Aside (Lazy Loading)

```python
# Most common pattern
async def get_test_case(case_id: str) -> TestCase:
    # 1. Try cache
    cached = await redis.get(f"test-case:{case_id}")
    if cached:
        return TestCase.model_validate_json(cached)
    
    # 2. Fetch from DB
    case = await db.query(TestCase).filter_by(id=case_id).first()
    
    # 3. Store in cache
    if case:
        await redis.setex(
            f"test-case:{case_id}",
            3600,  # TTL: 1 hour
            case.model_dump_json()
        )
    
    return case
```

#### 2. Refresh-on-Write (Invalidation)

```python
async def update_test_case(case_id: str, updates: dict):
    # 1. Update database
    case = await db.query(TestCase).filter_by(id=case_id).first()
    for key, value in updates.items():
        setattr(case, key, value)
    await db.commit()
    
    # 2. Invalidate cache
    await redis.delete(f"test-case:{case_id}")
    
    # 3. Optional: Pre-warm cache with fresh data
    await redis.setex(
        f"test-case:{case_id}",
        3600,
        case.model_dump_json()
    )
    
    return case
```

#### 3. Batch/Listing Cache

```python
async def list_test_cases(project_id: str, page: int = 1) -> dict:
    # Use project_id + page as cache key
    cache_key = f"test-cases:proj-{project_id}:page-{page}"
    
    # Try cache
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fetch from DB
    cases = await db.query(TestCase)\
        .filter_by(project_id=project_id)\
        .offset((page - 1) * 50)\
        .limit(50)\
        .all()
    
    result = {
        'data': [case.model_dump() for case in cases],
        'page': page
    }
    
    # Cache for 5 minutes (shorter for listings that change often)
    await redis.setex(cache_key, 300, json.dumps(result))
    
    return result
```

### Cache Keys Naming Convention

```
# Resource cache
{resource_type}:{resource_id}
Examples:
  test-case:tc-001
  test-run:run-123
  defect:def-456

# List/collection cache
{resource_type}:list:{filter_key}
Examples:
  test-cases:list:proj-123
  defects:list:proj-123:severity-high
  runs:list:project-123:status-completed

# Session/auth cache
session:{session_id}
user:{user_id}:org:{org_id}
token:{token_hash}

# Metrics/computed cache
metrics:proj-{project_id}:week-{week_num}
coverage:proj-{project_id}:latest
```

### Cache Invalidation Strategy

```python
# When to invalidate
async def on_test_case_updated(event: TestCaseUpdated):
    # Invalidate this resource
    await redis.delete(f"test-case:{event.case_id}")
    
    # Invalidate related collections
    await redis.delete(f"test-cases:list:proj-{event.project_id}:*")  # Wildcard
    
    # Invalidate parent metrics
    await redis.delete(f"metrics:proj-{event.project_id}:*")
```

### Redis Memory Management

```python
# backend/app/config.py
REDIS_MAX_MEMORY = "2gb"  # Set in Redis config
REDIS_EVICTION_POLICY = "allkeys-lru"  # Evict least recently used when full

# Monitor Redis memory
redis-cli INFO memory

# Set memory limit
CONFIG SET maxmemory 2gb
CONFIG SET maxmemory-policy allkeys-lru
```

---

## API Response Optimization

### Response Serialization

**❌ Slow: Serialize all relationships**
```python
@router.get("/test-cases/{case_id}")
async def get_case(case_id: str):
    case = await db.query(TestCase).options(
        joinedload(TestCase.steps),      # Loads all steps
        joinedload(TestCase.created_by), # Loads user details
        joinedload(TestCase.tags)        # Loads all tags
    ).filter_by(id=case_id).first()
    
    return case  # Returns 50KB response
```

**✅ Fast: Serialize only needed fields**
```python
class TestCaseResponse(BaseModel):
    id: str
    title: str
    description: str
    # Excludes: steps, tags, created_by (save ~40KB per request)

@router.get("/test-cases/{case_id}", response_model=TestCaseResponse)
async def get_case(case_id: str):
    case = await db.query(TestCase).filter_by(id=case_id).first()
    return TestCaseResponse.model_validate(case)
```

### Compression

```python
# Gzip responses > 500 bytes
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=500, compresslevel=6)

# Frontend receives compressed response ~70% smaller
# Example: 50KB → 15KB
```

### Pagination Defaults

```python
# Always paginate large result sets
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

@router.get("/test-cases")
async def list_cases(
    project_id: str,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0
):
    # Enforce limits
    limit = min(limit, MAX_PAGE_SIZE)
    offset = max(offset, 0)
    
    # ...
```

### N+1 Query Prevention

```python
# Use select_in_load for relationships
from sqlalchemy.orm import selectinload

cases = await session.query(TestCase)\
    .options(
        selectinload(TestCase.steps),
        selectinload(TestCase.tags)
    )\
    .filter_by(project_id=project_id)\
    .limit(50)\
    .all()

# Single query with JOIN, no N+1
```

---

## Frontend Performance

### Next.js Optimization

#### 1. Code Splitting

```tsx
// ❌ Slow: Bundle included in initial load
import HeavyComponent from './HeavyComponent';

export default function Page() {
  return <HeavyComponent />;
}

// ✅ Fast: Lazy load on demand
import dynamic from 'next/dynamic';

const HeavyComponent = dynamic(
  () => import('./HeavyComponent'),
  {
    loading: () => <Skeleton />,
    ssr: false  // Don't render on server
  }
);

export default function Page() {
  return <HeavyComponent />;
}
```

#### 2. Image Optimization

```tsx
// ❌ Slow: Unoptimized image
<img src="/screenshot.png" alt="Test result" />

// ✅ Fast: Next.js Image component
import Image from 'next/image';

<Image
  src="/screenshot.png"
  alt="Test result"
  width={800}
  height={600}
  quality={75}  // Reduce quality for faster delivery
  priority={false}  // Lazy load non-critical images
/>
```

#### 3. Query Data Caching

```tsx
// apps/web/lib/api-client.ts
import { useQuery } from '@tanstack/react-query';

// React Query handles caching with intelligent defaults
const useTestCases = (projectId: string) => {
  return useQuery({
    queryKey: ['test-cases', projectId],
    queryFn: () => apiClient.get(`/test-cases?project_id=${projectId}`),
    staleTime: 5 * 60 * 1000,  // 5 minutes
    gcTime: 10 * 60 * 1000,    // Keep cached data for 10 minutes
  });
};
```

#### 4. Virtual Scrolling (Long Lists)

```tsx
// For lists > 100 items
import { FixedSizeList } from 'react-window';

export function TestCaseList({ cases }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={cases.length}
      itemSize={50}
    >
      {({ index, style }) => (
        <div style={style}>
          {cases[index].title}
        </div>
      )}
    </FixedSizeList>
  );
}
```

### Web Vitals Monitoring

```tsx
// pages/_app.tsx
import { useEffect } from 'react';

export default function App({ Component, pageProps }) {
  useEffect(() => {
    // Monitor Core Web Vitals
    if ('web-vital' in window) {
      const sendVital = (metric) => {
        // Send to analytics service
        fetch('/api/analytics/web-vitals', {
          method: 'POST',
          body: JSON.stringify(metric)
        });
      };

      window.addEventListener('web-vital', sendVital);
    }
  }, []);

  return <Component {...pageProps} />;
}
```

---

## Monitoring & Profiling

### Application Performance Monitoring (APM)

```python
# Using Sentry APM (configured in app/config.py)
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=SENTRY_DSN,
    traces_sample_rate=0.1,  # 10% of requests
    integrations=[FastApiIntegration()]
)

# Traces automatically include:
# - HTTP request/response
# - Database queries
# - External service calls
# View in Sentry dashboard: Performance > Transactions
```

### Custom Performance Metrics

```python
# Track specific operations
import time
from prometheus_client import Histogram

ai_generation_duration = Histogram(
    'ai_test_generation_duration_seconds',
    'Time to generate test case with AI',
    buckets=(1, 5, 10, 30, 60)
)

async def generate_test_cases(prompt: str):
    with ai_generation_duration.time():
        # AI call here
        result = await ai_gateway.generate(prompt)
    
    return result
```

### Database Query Profiling

```python
# Enable query logging in development
# backend/app/config.py
if not settings.is_production:
    import logging
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    # Logs all SQL queries to stderr
```

### Memory Profiling

```bash
# Identify memory leaks
pip install memory_profiler pympler

# Run with memory tracking
python -m memory_profiler app/main.py

# Analyze heap
python -c "
  from pympler import muppy, summary
  
  # Snapshot 1
  all_objects_1 = muppy.get_objects()
  
  # Do work...
  
  # Snapshot 2
  all_objects_2 = muppy.get_objects()
  
  # Diff
  diff = summary.summarize([o for o in all_objects_2 if o not in all_objects_1])
  summary.print_(diff, limit=20)
"
```

---

## Load Testing

### k6 Load Test Script

```javascript
// tests/load/baseline.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up
    { duration: '5m', target: 50 },   // Stay at 50
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200', 'p(99)<500'],  // Assert SLA
    http_req_failed: ['rate<0.01'],
  }
};

export default function () {
  let token = __ENV.TOKEN;
  let projectId = __ENV.PROJECT_ID;
  
  // GET test cases (40% of traffic)
  let res = http.get(
    `http://localhost:8000/api/v1/test-cases?project_id=${projectId}&limit=50`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  
  check(res, { 'GET /test-cases: 200': (r) => r.status === 200 });
  
  // POST test run (30% of traffic)
  if (Math.random() < 0.3) {
    res = http.post(
      `http://localhost:8000/api/v1/runs`,
      JSON.stringify({
        project_id: projectId,
        case_ids: ['tc-001', 'tc-002'],
        name: 'Load test run'
      }),
      { headers: { Authorization: `Bearer ${token}` } }
    );
    check(res, { 'POST /runs: 201': (r) => r.status === 201 });
  }
  
  sleep(1);  // Think time between requests
}
```

### Running Load Tests

```bash
# Export load test traffic to metrics
k6 run tests/load/baseline.js \
  --vus 100 \
  --duration 5m \
  -e TOKEN=$JWT_TOKEN \
  -e PROJECT_ID=$PROJECT_ID \
  --out grafana

# View results in Grafana dashboard
# Then analyze:
# 1. p95 latency (should be < 200ms)
# 2. Error rate (should be < 1%)
# 3. Throughput (should be > 1000 req/s)
```

---

## Optimization Checklist

### Pre-Production Checklist

- [ ] **Database**
  - [ ] All indexes present (run: `\d+ table_name` in psql)
  - [ ] Query plans examined (EXPLAIN ANALYZE on slow queries)
  - [ ] Connection pool tuned (pool_size=20, max_overflow=40)
  - [ ] Table statistics up to date (ANALYZE)
  - [ ] Autovacuum enabled

- [ ] **Caching**
  - [ ] Redis configured and tested
  - [ ] Cache keys documented
  - [ ] TTLs set appropriately (5min-1hr)
  - [ ] Cache invalidation on writes
  - [ ] Cache hit rate > 85%

- [ ] **API Response**
  - [ ] Response compression enabled (GZIPMiddleware)
  - [ ] Unnecessary fields excluded from responses
  - [ ] Pagination enforced (MAX_PAGE_SIZE=200)
  - [ ] N+1 queries eliminated
  - [ ] API latency p95 < 200ms

- [ ] **Frontend**
  - [ ] Code splitting implemented
  - [ ] Images optimized
  - [ ] Lazy loading for non-critical components
  - [ ] React Query caching configured
  - [ ] Lighthouse score > 90

- [ ] **Monitoring**
  - [ ] APM configured (Sentry)
  - [ ] Key metrics defined (latency, errors, throughput)
  - [ ] Alerts set (SLA violations)
  - [ ] Dashboards created (Grafana)
  - [ ] Query slow log enabled

- [ ] **Load Testing**
  - [ ] Baseline load test passed
  - [ ] Performance SLAs met
  - [ ] Error rate < 1%
  - [ ] No memory leaks detected

---

## Common Performance Wins

| Optimization | Impact | Effort | ROI |
|--------------|--------|--------|-----|
| Add database indexes | -40% query time | Low | Very High |
| Enable response compression | -70% bandwidth | Low | Very High |
| Implement caching (Redis) | -80% DB load | Medium | Very High |
| Code splitting (frontend) | -50% bundle size | Medium | High |
| Lazy image loading | -30% LCP | Low | High |
| Query optimization | -60% slow queries | High | High |
| Connection pooling | -25% connection time | Low | Medium |
| Virtual scrolling | -70% memory (long lists) | Medium | Medium |

---

**End of Performance Tuning Guide**
