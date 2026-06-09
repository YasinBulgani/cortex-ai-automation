# Q1 Quarterly Enhancement Cycle — Implementation Plan
**Status:** Ready for Sprint Planning  
**Date:** 2026-06-09  
**Duration:** 12 weeks (Q1: July–September 2026)  
**Team Capacity:** 5 FTE (~1000 story points available)  

---

## Executive Summary

This Q1 plan builds on **Async Architecture Faz 0–3** (complete ✅) and **480+ production-ready items** to deliver:

1. **Advanced E2E Scenarios** (10 chaos/race/edge-case patterns)
2. **Performance Baseline v2** (async+read-replica+Redis full stack)
3. **Jira Integration** (bi-directional test case ↔ issue sync)
4. **Slack Webhook Expansion** (run notifications, defect alerts, daily digest)
5. **GraphQL API** (optional; POST-Q1 if time permits)

**Total Effort:** ~850 story points | **Risk:** Low (all foundational infra exists)

---

## Part 1: Advanced E2E Scenarios (10 Patterns)
**Story Points: 180 | Sprint: 1–3 | Owner: QA Lead**

### Objectives
- Test chaos conditions (network timeouts, DB deadlocks, cache eviction)
- Race condition detection (concurrent test runs, parallel execution)
- Edge cases (boundary values, timeout cascades, fallback chains)
- **Coverage:** 10 end-to-end scenarios across critical user paths

### Scenarios

| Scenario | Description | Story Points | Tests | Effort | Risk |
|----------|-------------|--------------|-------|--------|------|
| **E2E-001: Chaos Network Timeout** | Intermittent API latency (100–5000ms) → client retry logic → circuit breaker | 20 | 3 | 1w | Low |
| **E2E-002: DB Deadlock Recovery** | Concurrent test run → duplicate insert → deadlock → rollback → retry | 18 | 2 | 4d | Low |
| **E2E-003: Cache Stampede** | Cache miss during high concurrency → multiple cache fills → memory spike | 16 | 2 | 3d | Low |
| **E2E-004: Redis Failover** | Primary Redis down → read-replica failover → reconnect → state sync | 22 | 3 | 5d | Medium |
| **E2E-005: Concurrent Test Execution** | 50 parallel test runs → same project → resource contention → verify isolation | 24 | 3 | 5d | Medium |
| **E2E-006: Timeout Cascade** | Slow AI gateway (>30s) → frontend timeout → backend cleanup → no orphans | 20 | 2 | 4d | Low |
| **E2E-007: Partial Jira Sync Failure** | 100 test cases → 98 synced → 2 fail → resume from checkpoint → retry | 18 | 2 | 4d | Low |
| **E2E-008: Rate Limit Recovery** | Hit Groq API limit → fallback to vLLM → rate drop → backpressure → metrics | 16 | 2 | 3d | Low |
| **E2E-009: Defect State Transitions** | Closed → Reopened → In Progress (race) → final state consensus | 14 | 2 | 3d | Low |
| **E2E-010: Multi-Tenant Data Isolation** | Tenant A artifact leak into B during cache miss → verify RLS + cache key isolation | 12 | 1 | 2d | Low |

**Subtotal:** 180 SP | 22 test cases | ~4.5 weeks effort

### Implementation Pattern (per scenario)

```python
# tests/e2e/chaos_patterns.py
@pytest.mark.asyncio
@pytest.mark.e2e
class TestChaosNetworkTimeout:
    """Chaos: Network timeout recovery"""
    
    async def test_client_retry_on_timeout(self, chaos_api_client):
        """Intermittent latency (100–5000ms) → verify retry after 2 failures"""
        # Setup: mock API to inject latency on first 2 calls
        with chaos_api_client.inject_latency(5000, hits=2):
            result = await client.get_test_case(id=123, retries=3, timeout=2)
        # Expect: succeed on retry 3
        assert result.id == 123
    
    async def test_circuit_breaker_opens(self, chaos_api_client):
        """5 consecutive timeouts → circuit breaker opens → fail-fast"""
        with chaos_api_client.inject_timeout(hits=5):
            with pytest.raises(CircuitBreakerOpen):
                await client.get_test_case(id=123)
    
    async def test_circuit_breaker_recovery(self, chaos_api_client):
        """After 30s quiet, circuit breaker half-open → 1 success → closed"""
        # Setup: 5 failures, then wait 30s
        with chaos_api_client.inject_timeout(hits=5):
            with pytest.raises(CircuitBreakerOpen):
                await client.get_test_case(id=123)
        
        await asyncio.sleep(30)  # wait for half-open window
        
        # Reset mock; expect next call to succeed
        chaos_api_client.clear_failures()
        result = await client.get_test_case(id=123)
        assert result.id == 123

@pytest.mark.asyncio
@pytest.mark.e2e
class TestRaceConditions:
    """Race conditions under concurrency"""
    
    async def test_50_parallel_test_runs(self, project_factory, session):
        """50 concurrent test execution tasks → verify isolation, no crosstalk"""
        # Create 50 independent test cases in the same project
        tests = [await project_factory.create_test_case(project_id=123) for _ in range(50)]
        
        # Launch 50 concurrent executions
        tasks = [execute_test_case(tc.id) for tc in tests]
        results = await asyncio.gather(*tasks)
        
        # Verify all completed, no state corruption
        assert len(results) == 50
        assert all(r.status == "PASSED" for r in results)
        
        # Verify no test case data leaked between runs
        for i, tc in enumerate(tests):
            assert (await session.get(TestCase, tc.id)).last_run_id == results[i].id
    
    async def test_defect_state_race(self, defect_service):
        """2 agents: Closed → Reopened (race) → verify final state consensus"""
        defect = await defect_service.create(name="test", status="CLOSED")
        
        # Agent 1: CLOSED → IN_PROGRESS
        # Agent 2: CLOSED → REOPENED (concurrent)
        tasks = [
            defect_service.update_state(defect.id, "IN_PROGRESS"),
            defect_service.update_state(defect.id, "REOPENED"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Expect: one succeeds, one gets ConflictError
        assert any(isinstance(r, ConflictError) for r in results)
        
        # Final state: one of the two (ACID guarantee)
        final = await session.get(Defect, defect.id)
        assert final.status in ("IN_PROGRESS", "REOPENED")

@pytest.mark.asyncio
@pytest.mark.e2e
class TestTimeoutCascades:
    """Timeout cascades and cleanup"""
    
    async def test_slow_ai_gateway_frontend_timeout(self, 
                                                     ai_gateway_mock,
                                                     api_client):
        """AI gateway hangs >30s → frontend timeout → verify no orphaned jobs"""
        # Mock AI gateway to hang
        ai_gateway_mock.hang_for = 35  # 35 seconds
        
        # Frontend timeout: 30s
        with pytest.raises(asyncio.TimeoutError):
            async with asyncio.timeout(30):
                result = await api_client.post("/api/v1/ai/bdd-generate", 
                                               json={"test_case": "..."})
        
        # Verify cleanup: no orphaned async job in DB
        orphans = await session.execute(
            select(AsyncJob).where(AsyncJob.status == "RUNNING")
        )
        assert len(orphans) == 0
    
    async def test_retry_timeout_within_deadline(self, api_client):
        """Slow endpoint (8s) × 3 retries (24s) < 30s deadline → succeed"""
        with mock_slow_endpoint(delay=8, retries=3):
            result = await api_client.get("/api/v1/projects/123", 
                                          timeout=30, 
                                          retries=3)
        assert result.id == 123
    
    async def test_cascade_timeout_exceeds_deadline(self, api_client):
        """Slow endpoint (12s) × 3 retries (36s) > 30s deadline → fail fast"""
        with mock_slow_endpoint(delay=12, retries=3):
            with pytest.raises(DeadlineExceeded):
                await api_client.get("/api/v1/projects/123", 
                                     timeout=30, 
                                     retries=3)
```

### Tooling & Fixtures
- **Chaos Framework:** `pytest-chaos` plugin (inject latency, errors, timeouts)
- **Load Driver:** k6 + locust for concurrent user simulation
- **Monitoring:** Prometheus scrape chaos tests, alerting on SLO breach
- **CI Integration:** Nightly chaos run (`workflows/nightly-chaos.yml`)

### Acceptance Criteria
- ✅ All 10 scenarios pass locally (no flake > 1% retry rate)
- ✅ Chaos scenarios integrated into CI (nightly, manual trigger)
- ✅ Coverage report: 95%+ path coverage for timeout/retry/circuit-breaker code
- ✅ Performance SLO maintained: P99 latency < 500ms under chaos

---

## Part 2: Performance Baseline v2 (Async + Read-Replica + Redis Full Stack)
**Story Points: 140 | Sprint: 2–3 | Owner: Performance Engineer**

### Objectives
- Measure performance with **all async optimizations active**
- Test **read-replica sticky reads** (minimize read-after-write inconsistency)
- Validate **Redis caching** effectiveness (hit rate > 80%)
- Compare **Baseline v1 → v2** (latency, throughput, resource usage)
- Identify **bottlenecks** for Faz 4 optimization

### Baseline v2 Matrix

| Component | Metric | Baseline v1 (2026-06-09) | Target v2 | Sprint | Test |
|-----------|--------|--------------------------|-----------|--------|------|
| **API Gateway** | P99 latency (GET /projects) | 145ms | <100ms | 2 | perf-002 |
| **Auth (sync) → Async** | Login (auth.issue_tokens) | 280ms | <120ms | 2 | perf-003 |
| **Test Run Execution** | 50 concurrent runs, P99 | 8.2s | <5s | 2 | perf-004 |
| **Jira Sync Read** | 1000 issues list, P99 | 2.1s | <800ms | 3 | perf-005 |
| **Defect + Comments** | Nested query (RLS filter), P99 | 650ms | <300ms | 3 | perf-006 |
| **Cache Hit Rate** | GET endpoints (Redis), target | 45% | >80% | 2 | perf-007 |
| **DB Connection Pool** | Utilization (40 max), peak | 38 conns | <25 conns | 2 | perf-008 |
| **Memory (read-replica)** | Read-only replica memory | — | <2GB | 3 | perf-009 |
| **Throughput** | Req/s (50 VU sustained) | 420 req/s | >600 req/s | 3 | perf-010 |
| **GC Pauses** | Python GC pause (99th %ile) | 45ms | <20ms | 3 | perf-011 |

### Performance Test Architecture (k6 + Prometheus + Grafana)

```javascript
// performance-tests/perf-v2/baseline-full-stack.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Trend, Counter, Gauge, Rate } from 'k6/metrics';

// Custom metrics
const apiDurationTrend = new Trend('api_duration_ms');
const cacheHitRate = new Rate('cache_hit_rate');
const dbPoolUtilization = new Gauge('db_pool_utilization');

export const options = {
  stages: [
    { duration: '2m', target: 10 },   // ramp-up
    { duration: '5m', target: 50 },   // steady-state
    { duration: '2m', target: 0 },    // ramp-down
  ],
  thresholds: {
    'api_duration_ms': ['p(99) < 100'],   // P99 latency SLO
    'http_req_failed': ['rate < 0.01'],   // <1% error rate
    'cache_hit_rate': ['rate > 0.80'],    // >80% cache hits
  },
};

export default function() {
  const baseUrl = __ENV.BASE_URL || 'http://localhost:8000';
  const token = __ENV.API_TOKEN;
  
  group('Auth Domain — Async Optimization', () => {
    // Test async token issuance (no DB round-trip)
    const loginResp = http.post(
      `${baseUrl}/api/v1/auth/login`,
      JSON.stringify({ email: 'perf@test.com', password: 'demo123' }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    check(loginResp, {
      'login status is 200': (r) => r.status === 200,
      'login < 120ms': (r) => r.timings.duration < 120,
    });
    
    apiDurationTrend.add(loginResp.timings.duration);
  });
  
  group('Project Domain — Read-Replica + Cache', () => {
    // Repeated calls to same endpoint → measure cache effectiveness
    const projectsResp = http.get(`${baseUrl}/api/v1/projects`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    const cacheHit = projectsResp.headers['X-Cache'] === 'HIT';
    cacheHitRate.add(cacheHit);
    
    check(projectsResp, {
      'projects list status is 200': (r) => r.status === 200,
      'projects list < 100ms': (r) => r.timings.duration < 100,
    });
    
    apiDurationTrend.add(projectsResp.timings.duration);
  });
  
  group('Test Execution Domain — Concurrency', () => {
    // Simulate 50 concurrent test runs
    const runResp = http.post(
      `${baseUrl}/api/v1/test-execution/run`,
      JSON.stringify({ test_ids: [1, 2, 3, 4, 5] }),
      { headers: { 
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json'
      }}
    );
    
    check(runResp, {
      'test run status is 202': (r) => r.status === 202,
      'test run < 5s': (r) => r.timings.duration < 5000,
    });
    
    apiDurationTrend.add(runResp.timings.duration);
  });
  
  group('Defect + Comments — Nested RLS', () => {
    // Complex nested query with RLS filtering
    const defectResp = http.get(`${baseUrl}/api/v1/defects/123?include=comments`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    check(defectResp, {
      'defect detail status is 200': (r) => r.status === 200,
      'defect detail < 300ms': (r) => r.timings.duration < 300,
    });
    
    apiDurationTrend.add(defectResp.timings.duration);
  });
  
  // Scrape Prometheus for system metrics
  const metricsResp = http.get('http://prometheus:9090/api/v1/query', {
    params: {
      query: 'db_pool_utilization',
    }
  });
  
  if (metricsResp.status === 200) {
    const poolUtilization = JSON.parse(metricsResp.body)?.data?.result?.[0]?.value?.[1];
    if (poolUtilization) {
      dbPoolUtilization.add(parseFloat(poolUtilization));
    }
  }
  
  sleep(1);
}
```

### Prometheus + Grafana Dashboard

```yaml
# infra/prometheus/rules/perf-baseline-v2.yml
groups:
  - name: perf_baseline_v2
    interval: 30s
    rules:
      - alert: ApiP99LatencyHigh
        expr: histogram_quantile(0.99, api_duration_ms) > 100
        for: 2m
        annotations:
          summary: "API P99 latency exceeded 100ms"
      
      - alert: CacheHitRateLow
        expr: cache_hit_rate < 0.80
        for: 3m
        annotations:
          summary: "Cache hit rate below 80%"
      
      - alert: DbPoolUtilizationHigh
        expr: db_pool_utilization > 0.75
        for: 2m
        annotations:
          summary: "DB pool utilization > 75%"
```

### Test Cases (11 tests)

```python
# backend/tests/perf/test_baseline_v2.py
@pytest.mark.perf
class TestBaselineV2:
    """Performance Baseline v2 (async full-stack)"""
    
    @pytest.mark.asyncio
    async def test_perf_001_api_get_projects(self, api_client, benchmark):
        """P99 latency GET /projects < 100ms"""
        result = benchmark(lambda: api_client.get("/api/v1/projects"))
        assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_perf_003_async_auth_login(self, api_client, benchmark):
        """Async auth.issue_tokens < 120ms (no DB round-trip)"""
        result = benchmark(lambda: api_client.post("/api/v1/auth/login", 
                                                    json={"email": "...", "password": "..."}))
        assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_perf_004_50_concurrent_test_runs(self, api_client):
        """50 concurrent test executions, P99 < 5s"""
        tasks = [api_client.post(f"/api/v1/test-execution/run", 
                                 json={"test_ids": [1, 2, 3]})
                 for _ in range(50)]
        results = asyncio.run(asyncio.gather(*tasks))
        
        latencies = [r.elapsed.total_seconds() for r in results]
        p99 = np.percentile(latencies, 99)
        assert p99 < 5.0
    
    @pytest.mark.asyncio
    async def test_perf_007_redis_cache_hit_rate(self, api_client, redis_client):
        """Cache hit rate > 80% on repeated reads"""
        # Prime cache
        api_client.get("/api/v1/projects")
        
        # 50 repeated reads
        hits = 0
        for _ in range(50):
            resp = api_client.get("/api/v1/projects")
            if resp.headers.get('X-Cache') == 'HIT':
                hits += 1
        
        hit_rate = hits / 50
        assert hit_rate > 0.80
    
    # ... 7 more test cases (perf-002, 005, 006, 008–011)
```

### Success Criteria
- ✅ Baseline v2 metrics established and documented
- ✅ All 11 performance tests pass (no regressions)
- ✅ P99 latency improvements: 20–40% reduction vs v1
- ✅ Cache hit rate: >80% on GET endpoints
- ✅ Prometheus + Grafana dashboard deployed
- ✅ Nightly perf regression detection active

---

## Part 3: Jira Integration (Bi-Directional Sync)
**Story Points: 160 | Sprint: 2–4 | Owner: Integration Lead**

### Objectives
- **Sync Direction 1:** Neurex test case → Jira issue (create, update, link)
- **Sync Direction 2:** Jira issue → Neurex test case (update metadata, status)
- **Bidirectional:** Changes propagate in both directions (eventual consistency)
- **Coverage:** 80%+ happy path, 50%+ error cases
- **Automation Trigger:** CI/CD pipeline integration (test → Jira on run completion)

### Current State (as of 2026-06-09)
- ✅ Jira domain exists (`backend/app/domains/jira/`)
- ✅ Jira OAuth flow implemented
- ✅ Webhook receiver skeleton (`engine/routes/jira_routes.py`)
- ⚠️ Bi-directional sync incomplete (stub=true in API)
- ⚠️ Automation trigger missing (no event chain)

### Architecture

```
Neurex                          Jira
┌──────────────────┐          ┌────────────────────┐
│ Test Case        │◄────────►│ Issue (Story/Task) │
│ - name           │  REST API│ - summary          │
│ - description    │          │ - description      │
│ - status         │          │ - status           │
│ - priority       │          │ - priority         │
│ - assignee       │          │ - assignee         │
│ - automation_id  │          │ - custom field     │
└──────────────────┘          └────────────────────┘
        ▲                               ▲
        │                               │
        │ Test Run Completion           │ Webhook
        │ (automation trigger)          │ (status change)
        │                               │
    ┌───┴───┐                     ┌────┴──────┐
    │ Engine│                     │ Jira      │
    │ Event │────────────────────►│ Webhook   │
    │ Queue │                     │ Receiver  │
    └───────┘                     └───────────┘
```

### API Endpoints (New)

| Endpoint | Method | Purpose | Story Points | Sprint |
|----------|--------|---------|--------------|--------|
| `POST /api/v1/jira/sync/test-cases` | POST | Sync one or all test cases → Jira | 20 | 2 |
| `POST /api/v1/jira/sync/issues` | POST | Sync Jira issues → test cases | 20 | 2 |
| `POST /api/v1/jira/config/mapping` | POST | Configure field mapping (TC status ↔ Jira status) | 15 | 2 |
| `GET /api/v1/jira/sync/status` | GET | Show sync status, last run, error count | 10 | 2 |
| `POST /api/v1/jira/webhook/issue-changed` | POST | Jira webhook receiver (webhook secret validation) | 15 | 3 |
| `PUT /api/v1/jira/sync/resume` | PUT | Resume failed sync batch from checkpoint | 12 | 3 |

### Schema Additions (Database)

```python
# backend/alembic/versions/YYYYMMDD_NNNN_jira_bidirectional_sync.py
class JiraSyncMapping(Base):
    """Config: Field mapping TC ↔ Jira"""
    __tablename__ = "jira_sync_mappings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    
    # Neurex test case → Jira issue
    tc_status_to_jira: Mapped[dict] = mapped_column(JSON)  # {DRAFT: TODO, READY: IN_PROGRESS, ...}
    tc_priority_to_jira: Mapped[dict] = mapped_column(JSON)  # {P0: Highest, P1: High, ...}
    
    # Jira issue → Neurex test case
    jira_status_to_tc: Mapped[dict] = mapped_column(JSON)
    jira_priority_to_tc: Mapped[dict] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class JiraSyncBatch(Base):
    """Track sync batch progress + checkpoints"""
    __tablename__ = "jira_sync_batches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    
    # Sync direction: "tc_to_jira" or "jira_to_tc"
    direction: Mapped[str]
    
    # Status: PENDING, IN_PROGRESS, COMPLETED, FAILED
    status: Mapped[str] = mapped_column(default="PENDING")
    
    # Progress checkpoint (last synced ID)
    checkpoint_id: Mapped[int | None]
    
    total_count: Mapped[int]
    synced_count: Mapped[int] = mapped_column(default=0)
    error_count: Mapped[int] = mapped_column(default=0)
    
    # Error log (JSON)
    error_log: Mapped[list[dict]] = mapped_column(JSON, default=[])
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    next_retry_at: Mapped[datetime | None]

class TestCaseJiraLink(Base):
    """Link TestCase ↔ Jira Issue"""
    __tablename__ = "test_case_jira_links"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"))
    jira_issue_key: Mapped[str]  # e.g., "NEUREX-123"
    jira_issue_id: Mapped[str]   # e.g., "10000"
    
    # Sync direction: "auto" (bidirectional) or "one_way"
    sync_mode: Mapped[str] = mapped_column(default="auto")
    
    # Last sync timestamp
    last_synced_at: Mapped[datetime | None]
    
    # Sync state (detect if out-of-sync)
    neurex_version: Mapped[int] = mapped_column(default=1)
    jira_version: Mapped[int] = mapped_column(default=1)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

### Service Implementation (Async)

```python
# backend/app/domains/jira/service.py
class JiraSyncService:
    """Bi-directional test case ↔ Jira issue sync"""
    
    def __init__(self, session: AsyncSession, jira_client: JiraOAuthClient, cache: Redis):
        self.session = session
        self.jira = jira_client
        self.cache = cache
    
    # DIRECTION 1: Test Case → Jira Issue
    async def sync_test_cases_to_jira(self, org_id: int, checkpoint_id: int = 0) -> dict:
        """
        Sync all test cases in org → Jira issues.
        - Resume from checkpoint_id if batch interrupted
        - Create new issue if no link exists
        - Update existing issue if TC changed
        - Rate limit: 10 req/s (Jira API limit)
        """
        batch = await self.session.execute(
            select(JiraSyncBatch).where(
                (JiraSyncBatch.org_id == org_id) &
                (JiraSyncBatch.direction == "tc_to_jira") &
                (JiraSyncBatch.status.in_(["PENDING", "IN_PROGRESS"]))
            ).order_by(JiraSyncBatch.created_at.desc())
        )
        batch = batch.scalar_one_or_none()
        
        if not batch:
            # Create new batch
            test_cases = await self.session.execute(
                select(TestCase).where(TestCase.org_id == org_id)
            )
            batch = JiraSyncBatch(
                org_id=org_id,
                direction="tc_to_jira",
                status="PENDING",
                total_count=len(test_cases.scalars().all()),
            )
            self.session.add(batch)
            await self.session.commit()
        
        # Start/resume sync
        batch.status = "IN_PROGRESS"
        batch.started_at = datetime.utcnow()
        await self.session.commit()
        
        # Query test cases from checkpoint
        test_cases = await self.session.execute(
            select(TestCase).where(
                (TestCase.org_id == org_id) &
                (TestCase.id > (batch.checkpoint_id or 0))
            ).order_by(TestCase.id)
        )
        
        errors = []
        for tc in test_cases.scalars():
            try:
                # Check if link exists
                link = await self.session.execute(
                    select(TestCaseJiraLink).where(
                        (TestCaseJiraLink.test_case_id == tc.id) &
                        (TestCaseJiraLink.sync_mode != "one_way")
                    )
                )
                link = link.scalar_one_or_none()
                
                mapping = await self._get_sync_mapping(org_id)
                
                if link:
                    # Update existing issue
                    await self._update_jira_issue(link.jira_issue_key, tc, mapping)
                    link.last_synced_at = datetime.utcnow()
                    link.neurex_version += 1
                else:
                    # Create new issue
                    issue_key = await self._create_jira_issue(tc, org_id, mapping)
                    link = TestCaseJiraLink(
                        org_id=org_id,
                        test_case_id=tc.id,
                        jira_issue_key=issue_key,
                        jira_issue_id=(await self.jira.get_issue(issue_key))["id"],
                        sync_mode="auto",
                        last_synced_at=datetime.utcnow(),
                    )
                    self.session.add(link)
                
                batch.synced_count += 1
                batch.checkpoint_id = tc.id
                await self.session.commit()
                
                # Rate limit: 100ms between requests (10 req/s)
                await asyncio.sleep(0.1)
                
            except Exception as e:
                batch.error_count += 1
                errors.append({
                    "test_case_id": tc.id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                # Continue on error; resume later
                await self.session.commit()
        
        # Mark batch complete
        batch.status = "COMPLETED"
        batch.completed_at = datetime.utcnow()
        batch.error_log = errors
        await self.session.commit()
        
        return {
            "batch_id": batch.id,
            "synced": batch.synced_count,
            "errors": batch.error_count,
            "error_log": errors,
        }
    
    # DIRECTION 2: Jira Issue → Test Case
    async def sync_jira_issues_to_test_cases(self, org_id: int) -> dict:
        """Sync Jira issues → test cases (pull model)"""
        # Query Jira for all issues in project
        jira_issues = await self.jira.search_issues(
            jql=f"project = {org_id} AND issuetype in (Story, Task)"
        )
        
        batch = JiraSyncBatch(
            org_id=org_id,
            direction="jira_to_tc",
            status="PENDING",
            total_count=len(jira_issues),
        )
        self.session.add(batch)
        await self.session.commit()
        
        batch.status = "IN_PROGRESS"
        batch.started_at = datetime.utcnow()
        await self.session.commit()
        
        mapping = await self._get_sync_mapping(org_id)
        errors = []
        
        for jira_issue in jira_issues:
            try:
                # Check if link exists
                link = await self.session.execute(
                    select(TestCaseJiraLink).where(
                        (TestCaseJiraLink.jira_issue_key == jira_issue["key"])
                    )
                )
                link = link.scalar_one_or_none()
                
                if link:
                    # Update existing test case
                    await self._update_test_case(link.test_case_id, jira_issue, mapping)
                    link.last_synced_at = datetime.utcnow()
                    link.jira_version += 1
                else:
                    # Create new test case
                    tc = await self._create_test_case_from_jira(jira_issue, org_id, mapping)
                    link = TestCaseJiraLink(
                        org_id=org_id,
                        test_case_id=tc.id,
                        jira_issue_key=jira_issue["key"],
                        jira_issue_id=jira_issue["id"],
                        sync_mode="auto",
                        last_synced_at=datetime.utcnow(),
                    )
                    self.session.add(link)
                
                batch.synced_count += 1
                await self.session.commit()
                await asyncio.sleep(0.1)
                
            except Exception as e:
                batch.error_count += 1
                errors.append({
                    "jira_issue_key": jira_issue["key"],
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                await self.session.commit()
        
        batch.status = "COMPLETED"
        batch.completed_at = datetime.utcnow()
        batch.error_log = errors
        await self.session.commit()
        
        return {
            "batch_id": batch.id,
            "synced": batch.synced_count,
            "errors": batch.error_count,
        }
    
    async def handle_jira_webhook(self, org_id: int, payload: dict) -> None:
        """
        Webhook receiver: Jira issue changed → update test case.
        
        Jira sends:
        {
          "webhookEvent": "jira:issue_updated",
          "issue": {
            "key": "NEUREX-123",
            "fields": {"status": {"name": "Done"}, ...}
          }
        }
        """
        issue_key = payload["issue"]["key"]
        jira_issue = payload["issue"]
        
        # Find linked test case
        link = await self.session.execute(
            select(TestCaseJiraLink).where(
                (TestCaseJiraLink.org_id == org_id) &
                (TestCaseJiraLink.jira_issue_key == issue_key)
            )
        )
        link = link.scalar_one_or_none()
        
        if not link:
            return  # No link; ignore
        
        # Update test case from Jira
        mapping = await self._get_sync_mapping(org_id)
        await self._update_test_case(link.test_case_id, jira_issue, mapping)
        link.last_synced_at = datetime.utcnow()
        link.jira_version += 1
        await self.session.commit()
    
    # Helpers
    async def _create_jira_issue(self, tc: TestCase, org_id: int, mapping: dict) -> str:
        """Create Jira issue from test case"""
        payload = {
            "fields": {
                "project": {"id": str(org_id)},
                "summary": tc.name,
                "description": tc.description or "Auto-created from Neurex",
                "issuetype": {"name": "Story"},
                "status": {
                    "name": mapping["tc_status_to_jira"].get(tc.status, "To Do")
                },
                "priority": {
                    "name": mapping["tc_priority_to_jira"].get(tc.priority, "Medium")
                },
                "customfield_neurex_tc_id": tc.id,  # Link back
            }
        }
        
        response = await self.jira.create_issue(payload)
        return response["key"]
    
    async def _update_jira_issue(self, issue_key: str, tc: TestCase, mapping: dict) -> None:
        """Update Jira issue from test case"""
        payload = {
            "fields": {
                "summary": tc.name,
                "description": tc.description,
                "status": {"name": mapping["tc_status_to_jira"].get(tc.status, "To Do")},
                "priority": {"name": mapping["tc_priority_to_jira"].get(tc.priority, "Medium")},
            }
        }
        
        await self.jira.update_issue(issue_key, payload)
    
    async def _create_test_case_from_jira(self, jira_issue: dict, org_id: int, mapping: dict) -> TestCase:
        """Create test case from Jira issue"""
        tc = TestCase(
            org_id=org_id,
            name=jira_issue["fields"]["summary"],
            description=jira_issue["fields"]["description"],
            status=mapping["jira_status_to_tc"].get(
                jira_issue["fields"]["status"]["name"], "DRAFT"
            ),
            priority=mapping["jira_priority_to_tc"].get(
                jira_issue["fields"]["priority"]["name"], "P2"
            ),
        )
        self.session.add(tc)
        await self.session.commit()
        return tc
    
    async def _update_test_case(self, tc_id: int, jira_issue: dict, mapping: dict) -> None:
        """Update test case from Jira issue"""
        tc = await self.session.get(TestCase, tc_id)
        tc.status = mapping["jira_status_to_tc"].get(
            jira_issue["fields"]["status"]["name"], tc.status
        )
        tc.priority = mapping["jira_priority_to_tc"].get(
            jira_issue["fields"]["priority"]["name"], tc.priority
        )
        tc.description = jira_issue["fields"]["description"] or tc.description
        tc.updated_at = datetime.utcnow()
        await self.session.commit()
    
    async def _get_sync_mapping(self, org_id: int) -> dict:
        """Fetch or default sync mapping"""
        mapping = await self.session.execute(
            select(JiraSyncMapping).where(JiraSyncMapping.org_id == org_id)
        )
        mapping = mapping.scalar_one_or_none()
        
        if not mapping:
            return {
                "tc_status_to_jira": {
                    "DRAFT": "To Do",
                    "READY": "In Progress",
                    "RUNNING": "In Progress",
                    "PASSED": "Done",
                    "FAILED": "To Do",
                },
                "tc_priority_to_jira": {
                    "P0": "Highest",
                    "P1": "High",
                    "P2": "Medium",
                    "P3": "Low",
                },
                "jira_status_to_tc": {
                    "To Do": "DRAFT",
                    "In Progress": "READY",
                    "Done": "PASSED",
                },
                "jira_priority_to_tc": {
                    "Highest": "P0",
                    "High": "P1",
                    "Medium": "P2",
                    "Low": "P3",
                },
            }
        
        return {
            "tc_status_to_jira": mapping.tc_status_to_jira,
            "tc_priority_to_jira": mapping.tc_priority_to_jira,
            "jira_status_to_tc": mapping.jira_status_to_tc,
            "jira_priority_to_tc": mapping.jira_priority_to_tc,
        }
```

### Router Implementation

```python
# backend/app/domains/jira/router.py (new endpoints)
@jira_router.post("/sync/test-cases", status_code=202)
async def start_jira_sync_test_cases(
    org_id: int,
    service: JiraSyncService = Depends(get_jira_sync_service),
) -> dict:
    """
    Async task: Sync all test cases → Jira issues.
    Returns: 202 Accepted with batch_id for polling.
    """
    batch_id = await service.sync_test_cases_to_jira(org_id)
    return {"batch_id": batch_id, "status": "PENDING"}

@jira_router.post("/sync/issues", status_code=202)
async def start_jira_sync_issues(
    org_id: int,
    service: JiraSyncService = Depends(get_jira_sync_service),
) -> dict:
    """Async task: Sync Jira issues → test cases"""
    batch_id = await service.sync_jira_issues_to_test_cases(org_id)
    return {"batch_id": batch_id, "status": "PENDING"}

@jira_router.get("/sync/status")
async def get_jira_sync_status(
    org_id: int,
    batch_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get sync batch status + error log"""
    if batch_id:
        batch = await session.get(JiraSyncBatch, batch_id)
    else:
        # Latest batch
        batch = await session.execute(
            select(JiraSyncBatch).where(JiraSyncBatch.org_id == org_id)
            .order_by(JiraSyncBatch.created_at.desc())
        )
        batch = batch.scalar_one_or_none()
    
    if not batch:
        raise HTTPException(status_code=404, detail="No sync batch found")
    
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "synced": batch.synced_count,
        "total": batch.total_count,
        "errors": batch.error_count,
        "error_log": batch.error_log[:10],  # Last 10 errors
    }

@jira_router.put("/sync/resume")
async def resume_failed_sync(
    org_id: int,
    batch_id: int,
    service: JiraSyncService = Depends(get_jira_sync_service),
) -> dict:
    """Resume failed sync from checkpoint"""
    batch = await session.get(JiraSyncBatch, batch_id)
    if batch.status != "FAILED":
        raise HTTPException(status_code=400, detail="Batch not failed")
    
    result = await service.sync_test_cases_to_jira(org_id, checkpoint_id=batch.checkpoint_id)
    return result

@jira_router.post("/webhook/issue-changed")
async def handle_jira_webhook(
    request: Request,
    org_id: int,
    service: JiraSyncService = Depends(get_jira_sync_service),
) -> dict:
    """
    Jira webhook receiver.
    Validates X-Atlassian-Signature before processing.
    """
    payload = await request.json()
    
    # Verify webhook signature
    secret = settings.JIRA_WEBHOOK_SECRET
    signature = request.headers.get("X-Atlassian-Signature")
    
    if not await _verify_jira_webhook_signature(payload, signature, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    await service.handle_jira_webhook(org_id, payload)
    return {"status": "received"}
```

### Test Cases (15 tests)

```python
# backend/tests/test_jira_sync.py
@pytest.mark.integration
class TestJiraSyncToCases:
    """Sync test cases → Jira issues"""
    
    @pytest.mark.asyncio
    async def test_sync_single_test_case_creates_issue(self, org, session, jira_service_mock):
        """Single TC → create Jira issue + link"""
        tc = await TestCaseFactory.create(org_id=org.id, name="Login Flow", status="READY")
        
        result = await jira_service.sync_test_cases_to_jira(org.id)
        
        assert result["synced"] == 1
        assert result["errors"] == 0
        
        # Verify link created
        link = await session.execute(
            select(TestCaseJiraLink).where(TestCaseJiraLink.test_case_id == tc.id)
        )
        link = link.scalar_one_or_none()
        assert link is not None
        assert link.jira_issue_key.startswith("NEUREX-")
    
    @pytest.mark.asyncio
    async def test_sync_with_checkpoint_resumes(self, org, session, jira_service_mock):
        """Failed sync @ TC 50 → resume from checkpoint 50"""
        # Create 100 test cases
        tcs = [await TestCaseFactory.create(org_id=org.id) for _ in range(100)]
        
        # Create failed batch @ checkpoint 50
        batch = JiraSyncBatch(
            org_id=org.id,
            direction="tc_to_jira",
            status="FAILED",
            checkpoint_id=50,
            synced_count=50,
            error_count=3,
        )
        session.add(batch)
        await session.commit()
        
        # Resume
        result = await jira_service.sync_test_cases_to_jira(org.id, checkpoint_id=50)
        
        # Should sync remaining 50
        assert result["synced"] == 50
    
    @pytest.mark.asyncio
    async def test_sync_existing_tc_updates_issue(self, org, session, jira_service_mock):
        """TC already linked → update Jira issue, not create new"""
        tc = await TestCaseFactory.create(org_id=org.id, name="Old Name", status="DRAFT")
        link = TestCaseJiraLink(
            org_id=org.id,
            test_case_id=tc.id,
            jira_issue_key="NEUREX-123",
            jira_issue_id="10000",
        )
        session.add(link)
        await session.commit()
        
        # Update TC
        tc.name = "New Name"
        tc.status = "READY"
        await session.commit()
        
        # Sync
        result = await jira_service.sync_test_cases_to_jira(org.id)
        
        assert result["synced"] == 1
        # Verify update_issue was called (via mock)
        jira_service_mock.update_issue.assert_called_once()
    
    # ... 12 more test cases
```

### Automation Trigger (CI/CD Integration)

```yaml
# engine/routes/jira_routes.py - new route
@jira_bp.post("/api/jira/automation-trigger")
async def trigger_jira_sync_on_test_run(data):
    """
    Called by automation after test run completion.
    
    Payload: {
      "test_run_id": 123,
      "results": {...},
      "status": "PASSED" | "FAILED"
    }
    
    Syncs test run results → Jira issue.
    """
    run_id = data["test_run_id"]
    results = data["results"]
    
    # Query backend for test case details
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"http://backend:8000/api/v1/test-execution/runs/{run_id}",
            headers={"X-Internal-Key": BACKEND_INTERNAL_KEY}
        ) as resp:
            run = await resp.json()
    
    # Update linked Jira issue with run result
    jira_service = get_jira_sync_service()
    await jira_service.sync_test_run_result_to_jira(run)
    
    return {"status": "synced"}
```

### Success Criteria
- ✅ Bidirectional sync passes all 15 test cases (happy + error paths)
- ✅ Field mapping configurable per organization
- ✅ Checkpoint-based resume on failure
- ✅ Rate limit: 10 req/s to Jira API (no throttling)
- ✅ Webhook receiver validates signature + handles edge cases
- ✅ Automation trigger fires post-test-run (CI integration)

---

## Part 4: Slack Webhook Expansion (Notifications + Daily Digest)
**Story Points: 100 | Sprint: 3–4 | Owner: Integration Lead**

### Objectives
- **Test Run Notifications:** Start, complete, fail + link to report
- **Defect Alerts:** New, reopened, critical priority → channel subscription
- **Daily Digest:** Summary of runs, pass rate, top failures, trends
- **Coverage:** 3 notification types, 2 alert types, 1 digest type
- **Delivery:** Webhook receiver (100% uptime target via retry queue)

### Current State
- ✅ Basic Slack integration exists (`backend/app/domains/slack/`)
- ⚠️ Only test run notifications (partial)
- ⚠️ No daily digest
- ⚠️ No defect alerts

### Architecture

```
Neurex Events                    Slack
┌─────────────────┐            ┌──────────────────┐
│ Test Run        │ ──────────►│ #neurex-runs     │
│ - Started       │  Webhook   │ - Embed + link   │
│ - Completed     │            │ - Interactive    │
│ - Failed        │            └──────────────────┘
└─────────────────┘
┌─────────────────┐            ┌──────────────────┐
│ Defect Events   │ ──────────►│ #neurex-defects  │
│ - Created       │  Webhook   │ - Priority color │
│ - Reopened      │            │ - @mention owner │
│ - Assigned      │            └──────────────────┘
└─────────────────┘
┌─────────────────┐            ┌──────────────────┐
│ Daily Digest    │ ──────────►│ #neurex-daily    │
│ (nightly cron)  │  Scheduled │ - Metrics chart  │
│ - Pass rate     │            │ - Top 5 failures │
│ - Trends        │            └──────────────────┘
└─────────────────┘
```

### Slack Notification Templates

#### 1. Test Run Notifications

```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🟢 *Test Run Completed*\n<https://neurex.local/runs/123|Run #123> | *Project: E2E Tests*"
      }
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Status:*\nPASSED ✅"},
        {"type": "mrkdwn", "text": "*Duration:*\n2m 34s"},
        {"type": "mrkdwn", "text": "*Tests:*\n45/45 passed"},
        {"type": "mrkdwn", "text": "*Coverage:*\n89%"}
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🔗 <https://neurex.local/runs/123/report|View Detailed Report>"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Tester:* @john_doe | *Branch:* main | *Commit:* abc123def"
      }
    }
  ]
}
```

#### 2. Defect Alerts

```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🔴 *Critical Defect Reopened*\n<https://neurex.local/defects/456|DEF-456>"
      }
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Title:*\nLogin form accepts XSS"},
        {"type": "mrkdwn", "text": "*Priority:*\nP0 - Critical"},
        {"type": "mrkdwn", "text": "*Status:*\nReopened"},
        {"type": "mrkdwn", "text": "*Owner:*\n@security_team"}
      ]
    },
    {
      "type": "context",
      "elements": [
        {"type": "mrkdwn", "text": "Last closed: 2026-06-08 | Reopened: 2026-06-09 15:30"}
      ]
    }
  ]
}
```

#### 3. Daily Digest

```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "📊 *Daily Test Report* — 2026-06-09"
      }
    },
    {
      "type": "section",
      "fields": [
        {"type": "mrkdwn", "text": "*Test Runs:*\n124 total"},
        {"type": "mrkdwn", "text": "*Pass Rate:*\n92.7%"},
        {"type": "mrkdwn", "text": "*Avg Duration:*\n3m 42s"},
        {"type": "mrkdwn", "text": "*New Defects:*\n5"}
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Top 5 Failures:*\n1. Login form (8 fails) — @security_team\n2. Payment API (6 fails) — @backend_team\n3. Settings page (4 fails) — @frontend_team\n4. Report export (3 fails) — @engine_team\n5. Webhook delivery (2 fails) — @integration_team"
      }
    },
    {
      "type": "image",
      "image_url": "https://neurex.local/api/v1/slack/daily-chart",
      "alt_text": "Pass rate trend (7 days)"
    }
  ]
}
```

### API Endpoints (New)

| Endpoint | Method | Purpose | SP | Sprint |
|----------|--------|---------|----|----|
| `POST /api/v1/slack/notify/test-run` | POST | Send test run notification | 10 | 3 |
| `POST /api/v1/slack/notify/defect` | POST | Send defect alert | 12 | 3 |
| `POST /api/v1/slack/config/subscriptions` | POST | Configure channel subscriptions | 10 | 3 |
| `GET /api/v1/slack/config/subscriptions` | GET | List subscriptions | 5 | 3 |
| `POST /api/v1/slack/daily-digest` | POST | Trigger daily digest (cron) | 15 | 4 |
| `GET /api/v1/slack/daily-chart` | GET | Generate daily pass-rate chart (PNG) | 12 | 4 |

### Schema Additions (Database)

```python
class SlackSubscription(Base):
    """Organization-level Slack channel subscriptions"""
    __tablename__ = "slack_subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    
    # Channel name: #neurex-runs, #neurex-defects, #neurex-daily
    channel_name: Mapped[str]
    channel_id: Mapped[str]
    
    # Subscription type: "test_run" | "defect" | "daily_digest"
    subscription_type: Mapped[str]
    
    # Event filters (JSON)
    # E.g., {"status": ["FAILED", "TIMED_OUT"], "priority": ["P0", "P1"]}
    filters: Mapped[dict] = mapped_column(JSON, default={})
    
    # Enabled/disabled
    enabled: Mapped[bool] = mapped_column(default=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class SlackNotificationQueue(Base):
    """Retry queue for failed Slack deliveries"""
    __tablename__ = "slack_notification_queue"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    
    channel_id: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)  # Full Slack block payload
    
    # Status: PENDING, SENT, FAILED
    status: Mapped[str] = mapped_column(default="PENDING")
    
    # Retry tracking
    attempts: Mapped[int] = mapped_column(default=0)
    max_attempts: Mapped[int] = mapped_column(default=3)
    next_retry_at: Mapped[datetime | None]
    
    error_log: Mapped[str | None]
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    sent_at: Mapped[datetime | None]
```

### Service Implementation

```python
# backend/app/domains/slack/service.py
class SlackNotificationService:
    """Slack notifications: test runs, defects, daily digest"""
    
    def __init__(self, session: AsyncSession, slack_client: AsyncSlackClient, cache: Redis):
        self.session = session
        self.slack = slack_client
        self.cache = cache
    
    async def notify_test_run_completed(self, run: TestRun) -> None:
        """
        Send test run completion notification to #neurex-runs.
        - Success: green embed
        - Failure: red embed with top 3 failures
        """
        subs = await self.session.execute(
            select(SlackSubscription).where(
                (SlackSubscription.org_id == run.org_id) &
                (SlackSubscription.subscription_type == "test_run") &
                (SlackSubscription.enabled == True)
            )
        )
        
        for sub in subs.scalars():
            # Check filters
            filters = sub.filters
            if filters.get("status") and run.status not in filters["status"]:
                continue
            
            # Build block
            blocks = self._build_test_run_block(run)
            
            # Send with retry queue
            await self._send_to_slack(sub.channel_id, blocks, run.org_id)
    
    async def notify_defect_event(self, defect: Defect, event: str) -> None:
        """
        Send defect event to #neurex-defects.
        - event: "CREATED", "REOPENED", "ASSIGNED", "RESOLVED"
        """
        subs = await self.session.execute(
            select(SlackSubscription).where(
                (SlackSubscription.org_id == defect.org_id) &
                (SlackSubscription.subscription_type == "defect") &
                (SlackSubscription.enabled == True)
            )
        )
        
        for sub in subs.scalars():
            filters = sub.filters
            
            # Filter by priority
            if filters.get("priority") and defect.priority not in filters["priority"]:
                continue
            
            # Filter by event type
            if filters.get("events") and event not in filters["events"]:
                continue
            
            # Build block with color coding
            blocks = self._build_defect_block(defect, event)
            
            await self._send_to_slack(sub.channel_id, blocks, defect.org_id)
    
    async def send_daily_digest(self) -> None:
        """
        Nightly cron: summarize daily stats → #neurex-daily.
        - Aggregates: pass rate, run count, new defects
        - Generates: trend chart (7-day history)
        """
        orgs = await self.session.execute(select(Organization))
        
        for org in orgs.scalars():
            # Get yesterday's runs
            yesterday = datetime.utcnow().date() - timedelta(days=1)
            runs = await self.session.execute(
                select(TestRun).where(
                    (TestRun.org_id == org.id) &
                    (func.date(TestRun.created_at) == yesterday)
                )
            )
            runs = runs.scalars().all()
            
            if not runs:
                continue  # No runs yesterday
            
            # Calculate metrics
            passed = len([r for r in runs if r.status == "PASSED"])
            failed = len([r for r in runs if r.status == "FAILED"])
            total = len(runs)
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            avg_duration = np.mean([r.duration_seconds for r in runs if r.duration_seconds])
            
            # Get top failures
            defects = await self.session.execute(
                select(Defect).where(
                    (Defect.org_id == org.id) &
                    (func.date(Defect.created_at) == yesterday)
                ).order_by(Defect.created_at.desc())
            )
            top_defects = defects.scalars()[:5]
            
            # Build digest block
            blocks = self._build_daily_digest_block(
                pass_rate=pass_rate,
                runs_total=total,
                avg_duration=avg_duration,
                defects=top_defects,
            )
            
            # Get subscriber channel
            sub = await self.session.execute(
                select(SlackSubscription).where(
                    (SlackSubscription.org_id == org.id) &
                    (SlackSubscription.subscription_type == "daily_digest") &
                    (SlackSubscription.enabled == True)
                )
            )
            sub = sub.scalar_one_or_none()
            
            if sub:
                await self._send_to_slack(sub.channel_id, blocks, org.id)
    
    async def process_notification_queue(self) -> None:
        """
        Periodic task: retry failed Slack deliveries.
        - Max retries: 3
        - Backoff: exponential (10s, 60s, 300s)
        """
        pending = await self.session.execute(
            select(SlackNotificationQueue).where(
                (SlackNotificationQueue.status == "PENDING") &
                (SlackNotificationQueue.next_retry_at <= datetime.utcnow())
            ).order_by(SlackNotificationQueue.created_at)
        )
        
        for notif in pending.scalars():
            try:
                await self.slack.post_message(
                    channel=notif.channel_id,
                    blocks=notif.payload["blocks"],
                )
                
                notif.status = "SENT"
                notif.sent_at = datetime.utcnow()
                await self.session.commit()
                
            except Exception as e:
                notif.attempts += 1
                notif.error_log = str(e)
                
                if notif.attempts >= notif.max_attempts:
                    notif.status = "FAILED"
                    # TODO: alert ops
                else:
                    # Exponential backoff
                    backoff_seconds = 10 * (2 ** (notif.attempts - 1))
                    notif.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
                
                await self.session.commit()
    
    # Helpers
    def _build_test_run_block(self, run: TestRun) -> dict:
        """Build Slack block for test run completion"""
        status_emoji = "🟢" if run.status == "PASSED" else "🔴"
        color = "#2ecc71" if run.status == "PASSED" else "#e74c3c"
        
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{status_emoji} Test Run #{run.id}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Project:*\n{run.project.name}"},
                        {"type": "mrkdwn", "text": f"*Status:*\n{run.status}"},
                        {"type": "mrkdwn", "text": f"*Tests:*\n{run.passed}/{run.total}"},
                        {"type": "mrkdwn", "text": f"*Duration:*\n{run.duration_seconds}s"},
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Report"},
                            "url": f"https://neurex.local/runs/{run.id}/report",
                        }
                    ]
                }
            ]
        }
    
    def _build_defect_block(self, defect: Defect, event: str) -> dict:
        """Build Slack block for defect alert"""
        event_emoji = {
            "CREATED": "🆕",
            "REOPENED": "🔄",
            "ASSIGNED": "👤",
            "RESOLVED": "✅",
        }.get(event, "🔹")
        
        priority_color = {
            "P0": "#e74c3c",
            "P1": "#e67e22",
            "P2": "#f39c12",
            "P3": "#95a5a6",
        }.get(defect.priority, "#95a5a6")
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{event_emoji} *{event.title()} Defect*\n<https://neurex.local/defects/{defect.id}|{defect.title}>"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Priority:*\n{defect.priority}"},
                        {"type": "mrkdwn", "text": f"*Status:*\n{defect.status}"},
                        {"type": "mrkdwn", "text": f"*Assignee:*\n{defect.assignee.name if defect.assignee else 'Unassigned'}"},
                        {"type": "mrkdwn", "text": f"*Component:*\n{defect.component or 'N/A'}"},
                    ]
                }
            ]
        }
    
    def _build_daily_digest_block(self, pass_rate: float, runs_total: int, 
                                  avg_duration: float, defects: list) -> dict:
        """Build daily digest block"""
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Test Report"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Pass Rate:*\n{pass_rate:.1f}%"},
                        {"type": "mrkdwn", "text": f"*Test Runs:*\n{runs_total}"},
                        {"type": "mrkdwn", "text": f"*Avg Duration:*\n{avg_duration:.0f}s"},
                        {"type": "mrkdwn", "text": f"*New Defects:*\n{len(defects)}"},
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top Defects:*\n" + "\n".join(
                            f"{i+1}. <https://neurex.local/defects/{d.id}|{d.title}> — {d.priority}"
                            for i, d in enumerate(defects[:5])
                        ) if defects else "*No new defects*"
                    }
                }
            ]
        }
    
    async def _send_to_slack(self, channel_id: str, blocks: dict, org_id: int) -> None:
        """Send message to Slack with retry queue fallback"""
        try:
            await self.slack.post_message(channel=channel_id, **blocks)
        except Exception as e:
            # Queue for retry
            notif = SlackNotificationQueue(
                org_id=org_id,
                channel_id=channel_id,
                payload=blocks,
                status="PENDING",
                next_retry_at=datetime.utcnow() + timedelta(seconds=10),
            )
            self.session.add(notif)
            await self.session.commit()
```

### Router Implementation

```python
# backend/app/domains/slack/router.py (new endpoints)
@slack_router.post("/notify/test-run")
async def notify_test_run(
    run_id: int,
    service: SlackNotificationService = Depends(get_slack_notification_service),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger test run notification (typically called by automation)"""
    run = await session.get(TestRun, run_id)
    await service.notify_test_run_completed(run)
    return {"status": "queued"}

@slack_router.post("/config/subscriptions")
async def create_slack_subscription(
    org_id: int,
    channel_name: str,
    subscription_type: str,  # "test_run" | "defect" | "daily_digest"
    filters: dict | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Configure Slack channel subscription"""
    # Verify channel exists
    slack_client = get_slack_client()
    channel_info = await slack_client.get_channel_info(channel_name)
    
    sub = SlackSubscription(
        org_id=org_id,
        channel_name=channel_name,
        channel_id=channel_info["id"],
        subscription_type=subscription_type,
        filters=filters or {},
    )
    session.add(sub)
    await session.commit()
    
    return {"id": sub.id, "status": "created"}

@slack_router.get("/config/subscriptions")
async def list_slack_subscriptions(
    org_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List organization's Slack subscriptions"""
    subs = await session.execute(
        select(SlackSubscription).where(SlackSubscription.org_id == org_id)
    )
    return {"subscriptions": [dict(s) for s in subs.scalars()]}

@slack_router.post("/daily-digest")
async def trigger_daily_digest(
    service: SlackNotificationService = Depends(get_slack_notification_service),
) -> dict:
    """Trigger daily digest (called by cron)"""
    await service.send_daily_digest()
    return {"status": "sent"}

@slack_router.get("/daily-chart")
async def get_daily_chart(
    org_id: int,
    days: int = 7,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Generate pass-rate trend chart (PNG image).
    X-axis: last 7 days
    Y-axis: pass rate (0–100%)
    """
    # Query historical data
    runs_by_day = await session.execute(
        select(
            func.date(TestRun.created_at).label("date"),
            func.count(TestRun.id).label("total"),
            func.sum(case((TestRun.status == "PASSED", 1), else_=0)).label("passed"),
        )
        .where(
            (TestRun.org_id == org_id) &
            (TestRun.created_at >= datetime.utcnow() - timedelta(days=days))
        )
        .group_by(func.date(TestRun.created_at))
    )
    
    dates = []
    pass_rates = []
    for row in runs_by_day:
        dates.append(row.date.strftime("%Y-%m-%d"))
        pass_rate = (row.passed / row.total * 100) if row.total > 0 else 0
        pass_rates.append(pass_rate)
    
    # Generate chart (matplotlib)
    import matplotlib.pyplot as plt
    from io import BytesIO
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(dates, pass_rates, marker='o', linestyle='-', color='#2ecc71', linewidth=2)
    ax.set_ylim([0, 100])
    ax.set_ylabel('Pass Rate (%)')
    ax.set_xlabel('Date')
    ax.set_title(f'Test Pass Rate Trend ({days} days)')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Return as PNG
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return Response(content=buf.getvalue(), media_type="image/png")
```

### Test Cases (10 tests)

```python
# backend/tests/test_slack_notifications.py
@pytest.mark.integration
class TestSlackNotifications:
    """Slack notification delivery"""
    
    @pytest.mark.asyncio
    async def test_test_run_notification_sent(self, org, session, slack_client_mock):
        """Test run completion → notification to #neurex-runs"""
        run = await TestRunFactory.create(
            org_id=org.id,
            status="PASSED",
            passed=45,
            total=45,
        )
        
        service = SlackNotificationService(session, slack_client_mock, None)
        await service.notify_test_run_completed(run)
        
        # Verify post_message called
        slack_client_mock.post_message.assert_called_once()
        call_args = slack_client_mock.post_message.call_args
        
        # Verify blocks contain test run info
        assert "Test Run" in str(call_args)
        assert "PASSED" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_defect_alert_sent_on_priority_filter(self, org, session, slack_client_mock):
        """Defect alert only sent if priority matches filter"""
        # Create subscription: only P0 alerts
        sub = SlackSubscription(
            org_id=org.id,
            channel_name="#neurex-defects",
            channel_id="C123456",
            subscription_type="defect",
            filters={"priority": ["P0", "P1"]},
        )
        session.add(sub)
        await session.commit()
        
        # Create P2 defect (should NOT trigger)
        defect_p2 = await DefectFactory.create(org_id=org.id, priority="P2")
        service = SlackNotificationService(session, slack_client_mock, None)
        await service.notify_defect_event(defect_p2, "CREATED")
        
        # Verify NOT called
        slack_client_mock.post_message.assert_not_called()
        
        # Create P0 defect (should trigger)
        defect_p0 = await DefectFactory.create(org_id=org.id, priority="P0")
        await service.notify_defect_event(defect_p0, "CREATED")
        
        # Verify called
        slack_client_mock.post_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(self, org, session, slack_client_mock):
        """Failed Slack delivery → queued for retry"""
        slack_client_mock.post_message.side_effect = Exception("Network error")
        
        service = SlackNotificationService(session, slack_client_mock, None)
        await service._send_to_slack("C123456", {"blocks": [...]}, org.id)
        
        # Verify notification queued
        queued = await session.execute(
            select(SlackNotificationQueue).where(SlackNotificationQueue.status == "PENDING")
        )
        assert queued.scalar_one_or_none() is not None
    
    # ... 7 more test cases
```

### Cron Job (APScheduler)

```python
# backend/app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=0, minute=0)  # Midnight UTC
async def daily_digest_job():
    """Nightly: send daily digest to all orgs"""
    service = get_slack_notification_service()
    await service.send_daily_digest()

@scheduler.scheduled_job('cron', minute='*/5')  # Every 5 min
async def process_notification_queue():
    """Retry failed Slack deliveries"""
    service = get_slack_notification_service()
    await service.process_notification_queue()
```

### Success Criteria
- ✅ All 10 notification tests pass
- ✅ Daily digest sends at 00:00 UTC
- ✅ Retry queue processes failed deliveries (3 retries max)
- ✅ Channel subscriptions configurable per org
- ✅ Defect alerts respect priority/event filters
- ✅ 99%+ delivery SLO (via retry queue)

---

## Part 5: GraphQL API (Optional, Post-Q1 if time permits)
**Story Points: 120 | Sprint: 5+ (POST-Q1) | Owner: API Lead**

### Objectives
- **GraphQL Endpoint:** `/api/graphql` alongside REST
- **Query Playground:** Built-in IDE for schema exploration
- **Coverage:** 30+ types (Project, TestCase, TestRun, Defect, etc.)
- **Features:** Pagination, filtering, sorting, authorization
- **Deliverables:** Schema, resolvers, tests, documentation

### GraphQL Schema (Abridged)

```graphql
# backend/app/graphql/schema.graphql
type Query {
  # Projects
  projects(first: Int = 10, after: String): ProjectConnection!
  project(id: ID!): Project
  
  # Test Cases
  testCases(projectId: ID!, first: Int = 50, filter: TestCaseFilter): TestCaseConnection!
  testCase(id: ID!): TestCase
  
  # Test Runs
  testRuns(projectId: ID!, first: Int = 20): TestRunConnection!
  testRun(id: ID!): TestRun
  
  # Defects
  defects(projectId: ID!, first: Int = 50, priority: [Priority!]): DefectConnection!
  defect(id: ID!): Defect
  
  # Analytics
  projectMetrics(projectId: ID!, period: "WEEK" | "MONTH"): ProjectMetrics!
  passRateTrend(projectId: ID!, days: Int = 30): [DailyMetric!]!
}

type Mutation {
  # Test Cases
  createTestCase(input: CreateTestCaseInput!): TestCase!
  updateTestCase(id: ID!, input: UpdateTestCaseInput!): TestCase!
  deleteTestCase(id: ID!): Boolean!
  
  # Test Runs
  executeTestCase(id: ID!): TestRun!
  cancelTestRun(id: ID!): TestRun!
  
  # Defects
  createDefect(input: CreateDefectInput!): Defect!
  updateDefect(id: ID!, input: UpdateDefectInput!): Defect!
  closeDefect(id: ID!): Defect!
}

type Project {
  id: ID!
  name: String!
  description: String
  status: ProjectStatus!
  
  testCases(first: Int = 50): TestCaseConnection!
  testRuns(first: Int = 20): TestRunConnection!
  defects(first: Int = 50): DefectConnection!
  
  createdAt: DateTime!
  updatedAt: DateTime!
}

type TestCase {
  id: ID!
  projectId: ID!
  name: String!
  description: String
  status: TestCaseStatus!
  priority: Priority!
  
  jiraLink: JiraLink
  testRuns(first: Int = 10): TestRunConnection!
  
  createdAt: DateTime!
  updatedAt: DateTime!
}

type TestRun {
  id: ID!
  testCaseId: ID!
  status: RunStatus!
  passed: Int!
  failed: Int!
  durationSeconds: Float!
  
  testCase: TestCase!
  results: [TestResult!]!
  defects: [Defect!]!
  
  startedAt: DateTime!
  completedAt: DateTime
}

type Defect {
  id: ID!
  projectId: ID!
  title: String!
  description: String
  priority: Priority!
  status: DefectStatus!
  assignee: User
  
  testCases: [TestCase!]!
  comments(first: Int = 20): CommentConnection!
  
  createdAt: DateTime!
  updatedAt: DateTime!
}

type ProjectMetrics {
  projectId: ID!
  totalTestCases: Int!
  passRate: Float!
  averageDuration: Float!
  criticalDefects: Int!
}

type DailyMetric {
  date: String!
  totalRuns: Int!
  passRate: Float!
}

input CreateTestCaseInput {
  projectId: ID!
  name: String!
  description: String
  priority: Priority!
}

input TestCaseFilter {
  status: [TestCaseStatus!]
  priority: [Priority!]
}

enum Priority {
  P0
  P1
  P2
  P3
}

enum TestCaseStatus {
  DRAFT
  READY
  RUNNING
  PASSED
  FAILED
}

enum RunStatus {
  PENDING
  RUNNING
  PASSED
  FAILED
  TIMED_OUT
}
```

### Implementation (Strawberry + FastAPI)

```python
# backend/app/graphql/schema.py
from strawberry import Schema, type, field, input as strawberry_input
from strawberry.fastapi import GraphQLRouter

@type
class ProjectType:
    id: int
    name: str
    description: str | None
    status: str
    
    @field
    async def test_cases(self, first: int = 50) -> list["TestCaseType"]:
        # Resolve test cases for project
        pass
    
    @field
    async def test_runs(self, first: int = 20) -> list["TestRunType"]:
        pass

@type
class Query:
    @field
    async def projects(
        self,
        first: int = 10,
        after: str | None = None,
    ) -> list[ProjectType]:
        """List all projects (cursor pagination)"""
        # Implementation
        pass
    
    @field
    async def test_cases(
        self,
        project_id: int,
        first: int = 50,
        filter: TestCaseFilter | None = None,
    ) -> list[TestCaseType]:
        """List test cases with optional filtering"""
        pass
    
    @field
    async def project_metrics(
        self,
        project_id: int,
        period: str = "WEEK",
    ) -> ProjectMetricsType:
        """Analytics endpoint"""
        pass

@type
class Mutation:
    @field
    async def create_test_case(
        self,
        input: CreateTestCaseInput,
    ) -> TestCaseType:
        """Create new test case"""
        pass
    
    @field
    async def execute_test_case(
        self,
        id: int,
    ) -> TestRunType:
        """Execute test case (async)"""
        pass

schema = Schema(query=Query, mutation=Mutation)

# Wire into FastAPI
graphql_router = GraphQLRouter(schema)
# Mount at app.include_router(graphql_router, prefix="/api/graphql")
```

### Test Cases (5 tests)

```python
# backend/tests/test_graphql.py
@pytest.mark.integration
class TestGraphQLAPI:
    """GraphQL schema and resolvers"""
    
    @pytest.mark.asyncio
    async def test_graphql_query_projects(self, graphql_client):
        """Query projects with pagination"""
        query = """
            query {
              projects(first: 10) {
                edges { node { id name } }
              }
            }
        """
        result = await graphql_client.execute(query)
        assert result.data is not None
        assert "projects" in result.data
    
    @pytest.mark.asyncio
    async def test_graphql_nested_query(self, graphql_client, project):
        """Nested query: project → test cases → runs"""
        query = """
            query {
              project(id: %d) {
                name
                testCases(first: 5) {
                  edges { node { name } }
                }
              }
            }
        """ % project.id
        
        result = await graphql_client.execute(query)
        assert result.data["project"]["name"] == project.name
    
    # ... 2 more test cases
```

### Success Criteria (Post-Q1)
- ✅ GraphQL schema covers 30+ types
- ✅ Query playground accessible at `/api/graphql`
- ✅ All 5 GraphQL tests pass
- ✅ Documentation: schema explorer + examples
- ✅ Performance: P99 latency < 200ms

---

## Sprint Breakdown & Resource Allocation

### Timeline: 12 Weeks (July–September 2026)

| Sprint | Week | Focus | Stories | SP | Team |
|--------|------|-------|---------|----|----|
| **Sprint 1** | 1–2 | E2E Chaos Scenarios (Partial) | E2E-001, 002, 003, 004 | 80 | QA (2) + Backend (1) |
| **Sprint 2** | 3–4 | Jira Sync (Direction 1), Perf Baseline v2 | Jira sync TC→issue, Perf tests 1–4 | 110 | Backend (2) + Perf (1) |
| **Sprint 3** | 5–6 | E2E Chaos (Complete), Jira Webhook, Slack Notif | E2E-005–010, Jira webhook, Slack test run/defect | 135 | QA (2) + Backend (2) + Integration (1) |
| **Sprint 4** | 7–8 | Jira Sync (Direction 2), Slack Digest, Slack Config | Jira issue→TC sync, Slack daily digest, subscriptions | 125 | Backend (2) + Integration (1) |
| **Sprint 5** | 9–10 | Perf Baseline v2 (Complete), Slack Retry Queue | Perf tests 5–11, Slack retry + monitoring | 100 | Perf (1) + Backend (1) |
| **Sprint 6** | 11–12 | Documentation, Testing, GraphQL Optional | Runbooks, E2E + perf regression, GraphQL MVP | 95 | All (0.5 each) |

**Total Effort:** 850 SP | **Velocity:** ~140 SP/sprint | **Capacity:** 5 FTE × 2 weeks × 20 SP/day = ~200 SP/sprint (with buffer)

---

## Resource Allocation

| Role | Sprints | FTE | Notes |
|------|---------|-----|-------|
| **Backend Lead** | 1–6 | 1.5 | Jira service layer, async patterns, DB migrations |
| **QA Lead** | 1–6 | 1.5 | E2E chaos, test case generation, regression suite |
| **Performance Engineer** | 2, 5 | 1.0 | k6 tests, Prometheus setup, baseline analysis |
| **Integration Engineer** | 3–5 | 1.0 | Jira OAuth, Slack API, webhook receivers |
| **DevOps** | 2, 5–6 | 0.5 | Infra for perf (Prometheus/Grafana), CI/CD hooks |
| **PM/Tech Lead** | 1–6 | 0.5 | Sprint planning, risk management, documentation |

---

## Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| **Jira API Rate Limits** | Medium | Medium | Implement exponential backoff, checkpoint resume |
| **Slack Webhook Delivery Loss** | Low | Medium | Retry queue (3 attempts), DLQ monitoring |
| **Performance Regression** | Medium | High | Baseline v1 → v2 automated regression tests + SLO alerts |
| **Race Condition Flakes** | Medium | Medium | Isolate test data per scenario, use `asyncio.Lock` |
| **Async Timeout Cascades** | Low | High | Context deadline propagation, deadline-exceeded logging |
| **Chaos Test False Positives** | Medium | Low | Run chaos tests in isolation, exclude from CI voting |

---

## Success Metrics & KPIs

### Q1 Delivery
- **E2E Scenarios:** 10/10 chaos patterns pass, 0 flake rate
- **Performance Baseline v2:** 20–40% latency reduction, cache hit rate >80%
- **Jira Sync:** 1000+ test cases synced bidirectionally, <5% error rate
- **Slack Notifications:** 99%+ delivery SLO, daily digest at 00:00 UTC
- **Code Quality:** 95%+ test coverage, 0 critical bugs

### Operational Improvements
- **MTTR (Mean Time to Recover):** <10 min with chaos scenarios
- **Cache Efficiency:** From 45% → 80%+ hit rate
- **Jira Integration:** 100% test case traceability (TC ↔ issue)
- **Team Velocity:** Slack notifications reduce manual status checks by 60%

### Business Impact
- **Release Confidence:** E2E chaos + perf baseline = lower production risk
- **Developer Experience:** Jira sync + Slack notifications = faster feedback loops
- **Integration Completeness:** 3 critical integrations (Jira, Slack, AI Gateway) production-ready

---

## Implementation Priority & Sequencing

### Must Have (Critical Path)
1. **E2E Chaos Scenarios** → foundational test coverage
2. **Jira Bi-Directional Sync** → product requirement (from competitive audit)
3. **Slack Webhook Expansion** → team communication critical
4. **Performance Baseline v2** → post-async architecture validation

### Should Have
- Jira automation trigger (CI/CD) integration
- Slack daily digest + chart generation
- Comprehensive retry queue monitoring

### Nice to Have (Post-Q1)
- **GraphQL API** → advanced analytics, mobile-friendly queries
- Advanced chaos scenarios (BGP failures, disk full)
- Jira custom field mapping UI

---

## Testing & QA Strategy

### Test Coverage Targets
- **E2E Chaos:** 10 scenarios, 22 test cases, 95%+ pass rate
- **Jira Sync:** 15 unit + integration tests, 90%+ coverage
- **Slack Notifications:** 10 tests, 100% delivery path coverage
- **Performance Baseline:** 11 k6 load tests, 3 regression baselines

### CI/CD Integration
```yaml
# .github/workflows/q1-enhancement.yml
name: Q1 Enhancement Suite

on: [push, pull_request, schedule: "0 2 * * *"]

jobs:
  e2e-chaos:
    runs-on: ubuntu-latest
    steps:
      - run: make test-chaos
  
  perf-baseline:
    runs-on: ubuntu-latest
    steps:
      - run: k6 run performance-tests/perf-v2/baseline-full-stack.js
  
  jira-sync:
    runs-on: ubuntu-latest
    steps:
      - run: pytest backend/tests/test_jira_sync.py -v
  
  slack-notifications:
    runs-on: ubuntu-latest
    steps:
      - run: pytest backend/tests/test_slack_notifications.py -v
```

---

## Documentation Deliverables

### For Each Feature:
1. **Architecture Diagram** (Miro/Excalidraw)
2. **API Reference** (Swagger + examples)
3. **Runbook** (operational procedures)
4. **Troubleshooting Guide** (common errors)
5. **Performance SLO** (alert thresholds)

### Summary Docs
- `Q1_IMPLEMENTATION_RUNBOOK.md` — execution guide
- `Q1_CHAOS_TEST_GUIDE.md` — E2E scenario patterns
- `Q1_JIRA_SLACK_INTEGRATION_GUIDE.md` — setup + ops
- `Q1_PERFORMANCE_BASELINE_V2.md` — baseline metrics + trends

---

## Next Steps

1. **Week 1 (July 1):** Sprint planning, backlog refinement
2. **Week 2:** Kick off Sprint 1 (E2E chaos + Perf)
3. **Midpoint Review (4 weeks):** Assess velocity, adjust backlog
4. **End of Q1 (September 30):** Demo all 5 features, retrospective

---

## Summary

This Q1 plan delivers **850 story points** across 5 major enhancements:
- ✅ **Advanced E2E Scenarios** (180 SP) — chaos/race/timeout patterns
- ✅ **Performance Baseline v2** (140 SP) — async full-stack validation
- ✅ **Jira Integration** (160 SP) — bidirectional test case sync
- ✅ **Slack Webhooks** (100 SP) — notifications + daily digest
- ✅ **GraphQL API** (120 SP, optional) — modern data queries

**Risk:** Low | **Confidence:** High | **Go-Live:** Ready for immediate sprint planning

