# Phase 3.4: Optimization + Scaling
**Status:** Planning & Implementation  
**Timeline:** 3 weeks (2 engineer + 1 DevOps)  
**Target:** Flaky test mitigation, CI/CD optimization, production hardening  
**Date:** 2026-06-09

---

## 1. Flaky Test Mitigation

### 1.1 Detection Framework

**Current State:**
- `/backend/app/domains/tspm/flaky_service.py` — exists
- `/backend/alembic/versions/20260419_0004_add_flaky_quarantine.py` — migration
- `/engine/services/flaky_detector.py` — Flask service
- `/e2e/utils/flaky-tracker.ts` — frontend tracker
- `/backend/tests/unit/test_flaky_service.py` — unit tests

**Implementation:**

```python
# backend/app/domains/tspm/flaky_service.py (existing, enhance)
class FlakyTestTracker:
    """Track test failures across runs to identify flaky patterns."""
    
    async def record_test_run(self, test_id: str, passed: bool, duration_ms: int):
        """Record individual test run result."""
        # Store to flaky_test_runs table
        
    async def quarantine_flaky(self, test_id: str, fail_count: int = 3):
        """Quarantine test if it fails 3+ times in 10 runs."""
        # Mark test as quarantined in flaky_tests table
        
    async def get_flaky_dashboard(self, project_id: str):
        """Return dashboard: flaky %rate, top 10 by fail count, trends."""
        return {
            "flaky_tests": [...],
            "total_runs": int,
            "flaky_rate_percent": float,
            "trending_up": [...],  # Recently becoming flaky
        }
```

**Tests:**
- `tests/unit/test_tspm_flaky_service_helpers.py` — 100% coverage of helpers
- `tests/integration/test_flaky_detection.py` — end-to-end detection flow

---

### 1.2 Root Cause Analysis Patterns

**Timing Issues:**
```python
# Pattern: async task not completing before assertion
# Fix: explicit wait with health check
async def wait_for_condition(condition_fn, timeout_ms=5000, poll_ms=100):
    """Poll condition until true or timeout."""
    start = time.time() * 1000
    while True:
        if condition_fn():
            return True
        if (time.time() * 1000 - start) > timeout_ms:
            raise TimeoutError(f"Condition not met after {timeout_ms}ms")
        await asyncio.sleep(poll_ms / 1000)
```

**Async Test Pollution:**
```python
# Pattern: pytest-asyncio event loop reuse → state bleed
# Fix: fixture isolation
@pytest.fixture(scope="function")
async def clean_event_loop():
    """Fresh event loop per test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
```

**External Service Mocking:**
```python
# Pattern: VCR cassettes for HTTP (avoid sleep delays)
import vcr

my_vcr = vcr.VCR(
    cassette_library_dir="tests/cassettes",
    record_mode="once",  # Record on first run, replay after
)

@my_vcr.use_cassette("external_api_call.yaml")
def test_with_recorded_http():
    """Uses recorded HTTP response, no actual network call."""
    pass
```

**Transaction Isolation:**
```python
# Pattern: DB state leakage across tests
# Fix: use DB fixtures with rollback
@pytest.fixture
async def db_transaction(db_session):
    """Transaction auto-rollback after test."""
    async with db_session.begin_nested():
        yield db_session
        # Auto-rollback via context manager
```

---

### 1.3 Monitoring Dashboard

**Frontend Component:**
```typescript
// apps/web/components/FlakyTestDashboard.tsx
export const FlakyTestDashboard = () => {
  const { data: flakyStats } = useQuery({
    queryKey: ["flaky-tests", projectId],
    queryFn: () => apiClient.get(`/api/v1/projects/${projectId}/flaky-tests`),
  });

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Flaky Test Rate: {flakyStats.flaky_rate_percent}%</CardTitle>
        </CardHeader>
        <CardContent>
          <LineChart 
            data={flakyStats.trends}
            keys={["pass_rate", "flaky_rate"]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Top 10 Flakiest Tests</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Test ID</TableHead>
                <TableHead>Fail Rate</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {flakyStats.flaky_tests.map(test => (
                <TableRow key={test.id}>
                  <TableCell>{test.name}</TableCell>
                  <TableCell>{test.fail_rate}%</TableCell>
                  <TableCell>
                    {test.is_quarantined ? "🔴 Quarantined" : "🟡 Monitoring"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Weekly Report</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <p>Total Tests: {flakyStats.total_tests}</p>
            <p>Flaky Tests: {flakyStats.flaky_count}</p>
            <p>Quarantined: {flakyStats.quarantined_count}</p>
            <p>Trending Up: {flakyStats.trending_up.length}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
```

**Backend Endpoint:**
```python
# backend/app/domains/tspm/router.py
@router.get("/projects/{project_id}/flaky-tests", tags=["TSPM"])
async def get_flaky_dashboard(
    project_id: str,
    current_user: User = Depends(require_permission("view_reports")),
):
    """Get flaky test dashboard for project."""
    return await flaky_service.get_flaky_dashboard(project_id)
```

---

## 2. CI/CD Optimization

### 2.1 Test Parallelization Tuning

**Current State:**
- Makefile has `regression-parallel` target
- Backend pytest can use `-n` flag with pytest-xdist
- Frontend Jest can use `--maxWorkers` flag

**Optimal Configuration:**

```bash
# backend/Makefile
PYTEST_WORKERS ?= 4  # Tuned for typical CI environment (4 CPU)
PYTEST_TIMEOUT ?= 300  # 5 minutes per test

test-parallel:
	cd backend && $(PYTHON) -m pytest \
		--dist=loadscope \
		-n $(PYTEST_WORKERS) \
		--timeout=$(PYTEST_TIMEOUT) \
		--tb=short \
		-v
```

**Load Balancing:**
```bash
# .github/workflows/test.yml (pseudo)
jobs:
  test:
    strategy:
      matrix:
        # Split tests into 4 jobs to run in parallel
        test-shard: [1, 2, 3, 4]
    steps:
      - name: Run shard
        run: |
          cd backend
          pytest \
            --dist=loadscope \
            -n 2 \
            --co -q | \
            python -c "
              import sys
              tests = sys.stdin.readlines()
              shard = int('${{ matrix.test-shard }}') - 1
              total = 4
              shard_tests = [t for i, t in enumerate(tests) if i % total == shard]
              print(' '.join(shard_tests))
            " | xargs pytest
```

---

### 2.2 Cache Optimization

**Dependency Cache:**
```yaml
# .github/workflows/ci.yml
- uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.npm
    key: ${{ runner.os }}-deps-${{ hashFiles('**/requirements.txt', '**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-deps-
```

**Test Data Cache:**
```python
# backend/tests/conftest.py
@pytest.fixture(scope="session")
def test_data_cache(tmp_path_factory):
    """Cache test database snapshot between test runs."""
    cache_dir = tmp_path_factory.mktemp("test_cache")
    # On first run: populate cache
    # On subsequent runs: restore from cache
    yield cache_dir
```

**Build Artifact Cache:**
```bash
# .github/workflows/ci.yml
- name: Cache Next.js build
  uses: actions/cache@v3
  with:
    path: apps/web/.next
    key: ${{ runner.os }}-nextjs-${{ hashFiles('apps/web/package-lock.json') }}
```

---

### 2.3 Fail-Fast Strategy

```yaml
# .github/workflows/ci.yml
jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - run: cd backend && pytest tests/unit/ -x  # Stop on first failure
  
  api-tests:
    name: API Tests
    needs: unit-tests  # Only run if unit tests pass
    runs-on: ubuntu-latest
    steps:
      - run: cd backend && pytest tests/integration/ -x
  
  e2e-tests:
    name: E2E Tests
    needs: [unit-tests, api-tests]  # Run regardless of API test failure
    runs-on: ubuntu-latest
    steps:
      - run: npm run test:e2e
```

---

### 2.4 Resource Optimization

**Container Sizing:**
```dockerfile
# engine/Dockerfile
FROM python:3.11-slim
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir poetry

# Multi-stage build
FROM python:3.11-slim as runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
```

**Network Optimization:**
```bash
# Use internal service links, avoid external API calls
ENV POSTGRES_HOST=postgres  # Container network, not localhost
ENV REDIS_HOST=redis
ENV AI_GATEWAY_URL=http://ai-gateway:8080  # Internal URL
```

---

## 3. Production Hardening

### 3.1 Environment Isolation

**Development:**
- Local Docker stack
- All tests enabled
- Mock external services
- Debug logging

**Staging:**
- Production-like infra
- Regression tests only (no data mutation)
- Real external service stubs
- Info-level logging

**Production:**
- Hardened infra
- Smoke tests only (critical paths)
- No data mutation
- Warn-level logging + alerts

**Configuration Matrix:**
```python
# backend/app/config.py
class Settings(BaseSettings):
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    
    @property
    def TEST_MODE(self) -> bool:
        """Allow tests only in dev/staging."""
        return self.ENVIRONMENT != "prod"
    
    @property
    def RUN_ALL_TESTS(self) -> bool:
        return self.ENVIRONMENT == "dev"
    
    @property
    def LOG_LEVEL(self) -> str:
        levels = {"dev": "DEBUG", "staging": "INFO", "prod": "WARN"}
        return levels[self.ENVIRONMENT]
```

---

### 3.2 Secrets Management

**Environment Variable Masking:**
```python
# backend/app/infra/logging.py
import logging

class SensitiveFilter(logging.Filter):
    """Redact sensitive values from logs."""
    
    SENSITIVE_KEYS = {"password", "token", "api_key", "secret"}
    
    def filter(self, record):
        msg = record.getMessage()
        for key in self.SENSITIVE_KEYS:
            msg = re.sub(
                f'"{key}"\s*:\s*"([^"]+)"',
                f'"{key}": "[REDACTED]"',
                msg,
                flags=re.IGNORECASE
            )
        record.msg = msg
        record.args = ()
        return True

# Wire into logging
logging.root.addFilter(SensitiveFilter())
```

**Credential Rotation:**
```python
# backend/app/domains/auth/service.py
async def rotate_api_keys(user_id: str):
    """Rotate user API keys (max 2 active)."""
    old_keys = await db.query(ApiKey).filter(
        ApiKey.user_id == user_id,
        ApiKey.status == "active"
    ).order_by(ApiKey.created_at).all()
    
    # Keep only latest key, revoke older ones
    for key in old_keys[:-1]:
        key.status = "revoked"
        key.revoked_at = datetime.utcnow()
    await db.commit()
```

**Audit Logging:**
```python
# backend/app/domains/audit/service.py
async def log_sensitive_action(
    action: str,
    actor_id: str,
    resource: str,
    changes: dict = None
):
    """Log sensitive actions for compliance."""
    await db.create(AuditLog, {
        "action": action,
        "actor_id": actor_id,
        "resource": resource,
        "changes": changes or {},
        "timestamp": datetime.utcnow(),
        "ip_address": get_client_ip(),
        "user_agent": get_user_agent(),
    })
```

---

### 3.3 Compliance & Security

**GDPR Data Handling:**
```python
# backend/app/domains/privacy/service.py
async def delete_user_data(user_id: str):
    """GDPR right to be forgotten."""
    # 1. Anonymize user identity
    user = await db.get(User, user_id)
    user.email = f"deleted_{user_id}@redacted.local"
    user.name = "Deleted User"
    
    # 2. Retain minimal audit trail
    await db.create(AuditLog, {
        "action": "user_deletion",
        "user_id": user_id,
        "timestamp": datetime.utcnow(),
    })
    
    # 3. Cascade delete personal data
    await db.delete_many(PersonalData, {"user_id": user_id})
    await db.commit()
```

**PII Redaction:**
```python
# backend/app/infra/sentry.py
import sentry_sdk

def before_send(event, hint):
    """Redact PII from Sentry reports."""
    if "request" in event:
        event["request"]["headers"] = {
            k: "[REDACTED]" if k.lower() in ["authorization", "cookie"]
            else v
            for k, v in event["request"]["headers"].items()
        }
    return event

sentry_sdk.init(
    before_send=before_send,
    traces_sample_rate=0.1 if ENVIRONMENT == "prod" else 1.0
)
```

**Compliance Tests:**
```python
# backend/tests/compliance/test_gdpr.py
@pytest.mark.compliance
async def test_user_deletion_is_irreversible(db_session):
    """GDPR: deleted user cannot be recovered."""
    user = await create_test_user()
    user_id = user.id
    
    await delete_user_data(user_id)
    
    # Verify deletion
    restored = await db_session.get(User, user_id)
    assert restored.email.startswith("deleted_")
    assert restored.name == "Deleted User"

@pytest.mark.compliance
async def test_pii_not_in_sentry(monkeypatch):
    """PII redaction: no email/phone in crash reports."""
    with monkeypatch.context() as m:
        captured_events = []
        m.setattr(
            "sentry_sdk.transport.Transport.capture_event",
            lambda self, event: captured_events.append(event)
        )
        
        # Trigger error with PII
        try:
            raise ValueError(f"User email: test@example.com")
        except:
            sentry_sdk.capture_exception()
        
        # Verify redaction
        event = captured_events[0]
        event_str = json.dumps(event)
        assert "test@example.com" not in event_str
```

---

## 4. Team Training

### 4.1 Documentation

**Test Automation Guide** (`docs/TEST_AUTOMATION_GUIDE.md`):
```markdown
# Test Automation Best Practices

## Unit Tests
- Pure functions, no I/O
- Cover happy path + edge cases
- Use fixtures for setup/teardown

## Integration Tests
- Real database, Redis, etc.
- Transaction-isolated fixtures
- VCR cassettes for external APIs

## E2E Tests
- Critical user workflows only
- Explicit waits (not sleeps)
- Page Object Model pattern

## Flaky Test Handling
1. Add explicit waits
2. Use health checks instead of sleep
3. Isolate async state
4. Use VCR for external APIs
5. Quarantine 3+ failures
```

**Best Practices Checklist:**
```markdown
## Code Review Checklist for Tests

- [ ] Unit tests use pure functions
- [ ] Integration tests use transactional fixtures
- [ ] E2E tests use Page Object Model
- [ ] No hardcoded timeouts (use explicit waits)
- [ ] External API calls use VCR cassettes
- [ ] Tests are deterministic (no flakiness)
- [ ] Test data is cleaned up after tests
- [ ] Error messages are descriptive
- [ ] Test names describe what they verify
- [ ] Coverage is >80% for critical paths
```

---

### 4.2 Workshops

**Workshop 1: pytest Advanced** (2h)
```python
# Topics:
# 1. Fixtures (function, class, session scope)
# 2. Parametrization (@pytest.mark.parametrize)
# 3. Markers for test organization
# 4. Mocking (unittest.mock, monkeypatch)
# 5. Async test patterns (pytest-asyncio)
# 6. Performance testing (pytest-benchmark)

# Hands-on:
# - Write 5 tests for sample code
# - Fix 3 flaky tests (given examples)
# - Optimize slow test with mocking
```

**Workshop 2: Karate API Testing** (2h)
```gherkin
# Topics:
# 1. Feature files & scenario outlines
# 2. API request/response assertions
# 3. Data-driven testing (Examples table)
# 4. Custom functions & JavaScript
# 5. Contract testing
# 6. Load testing with Karate

# Hands-on:
# - Write 5 API scenarios
# - Create data-driven test
# - Integrate with CI/CD
```

**Workshop 3: Playwright E2E** (2h)
```typescript
// Topics:
// 1. Page Object Model
// 2. Selectors & locators
// 3. Actions (click, fill, select)
// 4. Assertions & screenshots
// 5. Visual regression testing
// 6. Debugging & tracing

// Hands-on:
// - Write 3 user workflows
// - Fix 2 flaky E2E tests
// - Set up visual regression
```

---

### 4.3 Code Review Standards

**Test Quality Matrix:**

| Aspect | Poor | Good | Excellent |
|--------|------|------|-----------|
| **Clarity** | Names unclear | Names describe intent | Names + comments explain flow |
| **Isolation** | Tests affect each other | Fixtures ensure isolation | Perfect isolation + rollback |
| **Speed** | >10s per test | 100-500ms per test | <100ms per test |
| **Reliability** | Flaky (>1% failure) | Stable (<0.1% failure) | Zero flakiness (100+ runs) |
| **Coverage** | <50% | >80% | >95% critical paths |
| **Maintainability** | Hard to update | Easy to extend | Self-documenting |

---

### 4.4 Knowledge Base

**FAQ:**
```markdown
## Flaky Test Diagnosis

**Q: Test passes locally but fails in CI**
A: Common causes:
   1. Hardcoded timeouts (use explicit wait)
   2. Async state not flushed (add barrier)
   3. Mock inconsistency (use VCR cassettes)
   4. DB transaction isolation (use SERIALIZABLE)

**Q: Test slows down over time**
A: Common causes:
   1. Test data accumulation (add cleanup)
   2. DB not indexed (check query plan)
   3. External API calls (switch to VCR)
   4. Memory leak in fixture (check cleanup)

**Q: Test sometimes passes, sometimes fails**
A: Common causes:
   1. Race condition (use explicit wait)
   2. Order-dependent tests (run in isolation)
   3. Timing-dependent assertions (add buffer)
   4. Non-deterministic mocks (seed randomness)
```

---

## 5. Implementation Plan

### Phase 3.4.1: Flaky Test Mitigation (Week 1)
- [ ] Enhance `flaky_service.py` with detection logic
- [ ] Build flaky test dashboard (frontend + backend)
- [ ] Implement VCR cassette recording for external APIs
- [ ] Quarantine 3+ failing tests
- [ ] Create root cause analysis guide
- [ ] Tests: 100% coverage of flaky detection

### Phase 3.4.2: CI/CD Optimization (Week 2)
- [ ] Tune pytest parallelization (4 workers)
- [ ] Implement dependency caching (pip, npm)
- [ ] Set up fail-fast strategy (unit → api → e2e)
- [ ] Add build artifact caching
- [ ] Optimize container sizing
- [ ] Create CI/CD tuning runbook

### Phase 3.4.3: Production Hardening (Week 2-3)
- [ ] Implement environment-based settings
- [ ] Add secrets masking to logs
- [ ] Create credential rotation workflow
- [ ] Implement audit logging
- [ ] Add GDPR compliance tests
- [ ] Create security hardening checklist

### Phase 3.4.4: Team Training (Week 3)
- [ ] Finalize test automation guide
- [ ] Run 3 workshops (pytest, Karate, Playwright)
- [ ] Create code review checklist
- [ ] Build FAQ knowledge base
- [ ] Document troubleshooting guide
- [ ] Set up mentoring schedule

---

## 6. Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| **Flaky Test Rate** | <0.5% | Unknown |
| **Test Execution Time** | <45 min (full suite) | Unknown |
| **Cache Hit Rate** | >85% | TBD |
| **CI Pass Rate** | >99% | TBD |
| **P99 Test Duration** | <5s per test | TBD |
| **Team Test Coverage** | >80% | >90% (existing) |
| **Security Audit** | All green | In progress |
| **Knowledge Base** | 100% coverage | 0% (to create) |

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Flaky tests hard to reproduce | High | Use full CI logs + VCR cassettes |
| Cache poisoning in CI | High | Add cache invalidation on major updates |
| Secrets leaked in logs | Critical | Implement SensitiveFilter + audit |
| Team resistance to new tests | Medium | Show ROI: reduced production bugs |

---

## 8. Deliverables

1. **Flaky Test Dashboard** — Real-time monitoring UI + API
2. **CI/CD Tuning Runbook** — Step-by-step optimization guide
3. **Training Materials** — 3 workshop slide decks + code examples
4. **Hardening Checklist** — Security + compliance verification
5. **Knowledge Base** — FAQ + troubleshooting guide (Markdown)
6. **Metrics Dashboard** — Test execution time + flakiness trends

---

## 9. Timeline

| Week | Focus | Deliverables |
|------|-------|--------------|
| W1 | Flaky detection + quarantine | Dashboard, 100+ tests |
| W2 | CI/CD tuning + hardening | Runbook, cache setup |
| W3 | Team training + knowledge base | 3 workshops, FAQ, mentoring |

---

## 10. Success Criteria

- [ ] 0 flaky tests in production (quarantine working)
- [ ] Full test suite runs <45 min on 4 workers
- [ ] 0 secrets leaked in logs (audit passing)
- [ ] 100% GDPR compliance (tests passing)
- [ ] 80%+ team test automation knowledge
- [ ] <1% CI failure rate due to environment

---

## Resources

**Files Created/Modified:**
- `/backend/app/domains/tspm/flaky_service.py` — Enhanced
- `/backend/app/domains/tspm/flaky_router.py` — New endpoints
- `/apps/web/components/FlakyTestDashboard.tsx` — New
- `/backend/app/infra/logging.py` — SensitiveFilter
- `/backend/app/config.py` — Environment settings
- `/docs/TEST_AUTOMATION_GUIDE.md` — New
- `/docs/SECURITY_HARDENING_CHECKLIST.md` — New
- `/.github/workflows/ci.yml` — Updated with parallelization
- `/Makefile` — Tuning targets

**External Refs:**
- pytest-xdist: `https://pytest-xdist.readthedocs.io/`
- VCR.py: `https://vcrpy.readthedocs.io/`
- pytest-asyncio: `https://github.com/pytest-dev/pytest-asyncio`

---

**Next Steps:**
1. Review this plan with team
2. Prioritize quick wins (flaky detection, cache setup)
3. Start Week 1 implementation
4. Measure baseline metrics (current flakiness, execution time)
5. Schedule workshops by end of Week 2
