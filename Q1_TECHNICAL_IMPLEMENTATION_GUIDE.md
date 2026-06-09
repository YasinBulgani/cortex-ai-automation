# Q1 Enhancement Cycle — Technical Implementation Guide
**Status:** Ready for Development  
**Version:** 1.0  
**Date:** 2026-06-09  

---

## Table of Contents
1. [E2E Chaos Test Framework](#e2e-chaos-framework)
2. [Jira Sync Implementation Checklist](#jira-sync-checklist)
3. [Slack Integration Setup](#slack-setup)
4. [Performance Testing Setup](#perf-setup)
5. [Deployment & Monitoring](#deployment)
6. [Troubleshooting](#troubleshooting)

---

## E2E Chaos Test Framework

### 1.1 Directory Structure
```
backend/
├── tests/
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── chaos_patterns.py        # Chaos scenario tests
│   │   ├── race_conditions.py       # Concurrency tests
│   │   └── timeout_cascades.py      # Timeout/retry tests
│   └── fixtures/
│       ├── chaos_api_client.py      # Fixture: inject latency/errors
│       └── chaos_db.py              # Fixture: simulate deadlocks
```

### 1.2 Chaos API Client Fixture
```python
# backend/tests/fixtures/chaos_api_client.py
import asyncio
import random
from typing import Optional, Callable
from unittest.mock import patch, AsyncMock
import httpx

class ChaosApiClient:
    """Fixture for injecting failures into HTTP client"""
    
    def __init__(self):
        self.failures = []  # List of (threshold, error_type)
        self.latency_range = (0, 0)  # (min_ms, max_ms)
        self.failure_count = 0
    
    def inject_latency(self, max_ms: int, hits: int = 1):
        """Inject latency for N requests (context manager)"""
        return self._FailureInjector(self, latency_ms=max_ms, hits=hits)
    
    def inject_timeout(self, hits: int = 1):
        """Inject timeout errors for N requests"""
        return self._FailureInjector(self, timeout_hits=hits)
    
    def inject_error(self, status_code: int, hits: int = 1):
        """Inject HTTP error responses"""
        return self._FailureInjector(self, status_code=status_code, hits=hits)
    
    class _FailureInjector:
        def __init__(self, client: "ChaosApiClient", **kwargs):
            self.client = client
            self.latency_ms = kwargs.get('latency_ms', 0)
            self.timeout_hits = kwargs.get('timeout_hits', 0)
            self.status_code = kwargs.get('status_code', None)
            self.hits = kwargs.get('hits', 1)
        
        async def __aenter__(self):
            self.original_post = httpx.post
            self.original_get = httpx.get
            self.call_count = 0
            
            async def patched_request(*args, **kwargs):
                self.call_count += 1
                
                # Apply latency
                if self.latency_ms > 0 and self.call_count <= self.hits:
                    await asyncio.sleep(self.latency_ms / 1000)
                
                # Inject timeout
                if self.timeout_hits > 0 and self.call_count <= self.hits:
                    raise asyncio.TimeoutError("Chaos: timeout injected")
                
                # Inject error
                if self.status_code and self.call_count <= self.hits:
                    raise httpx.HTTPStatusError(
                        f"Chaos: {self.status_code}",
                        request=None,
                        response=None
                    )
                
                # Normal flow
                return await self.original_request(*args, **kwargs)
            
            # Patch httpx
            httpx.post = patched_request
            httpx.get = patched_request
            
            return self
        
        async def __aexit__(self, *args):
            httpx.post = self.original_post
            httpx.get = self.original_get
    
    async def clear_failures(self):
        """Reset all injected failures"""
        self.failures = []
        self.failure_count = 0

@pytest.fixture
async def chaos_api_client():
    """Inject into tests as fixture"""
    return ChaosApiClient()
```

### 1.3 Example: Network Timeout Test
```python
# backend/tests/e2e/chaos_patterns.py
@pytest.mark.asyncio
@pytest.mark.e2e
class TestChaosNetworkTimeout:
    """E2E-001: Network timeout → retry → circuit breaker"""
    
    async def test_timeout_triggers_retry(self, api_client, chaos_api_client):
        """
        Scenario: GET /api/v1/projects times out on attempt 1–2
        Expected: Succeeds on attempt 3 (exponential backoff)
        """
        with chaos_api_client.inject_timeout(hits=2):
            response = await api_client.get(
                "/api/v1/projects",
                retries=3,
                timeout_per_retry=2,
            )
        
        assert response.status_code == 200
        assert response.json() is not None
    
    async def test_timeout_circuit_breaker(self, api_client, chaos_api_client):
        """
        Scenario: 5 consecutive timeouts
        Expected: Circuit breaker opens → fail-fast
        """
        with chaos_api_client.inject_timeout(hits=5):
            with pytest.raises(CircuitBreakerOpen):
                for i in range(5):
                    await api_client.get(
                        "/api/v1/projects",
                        retries=1,  # No retry; circuit breaker in effect
                    )
    
    async def test_circuit_breaker_recovery(self, api_client, chaos_api_client):
        """
        Scenario: Circuit opens → wait 30s → half-open → 1 success → closed
        Expected: Circuit recovers after quiet period
        """
        # Phase 1: Trigger open
        with chaos_api_client.inject_timeout(hits=5):
            with pytest.raises(CircuitBreakerOpen):
                for _ in range(5):
                    await api_client.get("/api/v1/projects", retries=0)
        
        # Phase 2: Wait for half-open window
        await asyncio.sleep(31)  # 30s quiet + 1s buffer
        
        # Phase 3: Half-open test
        chaos_api_client.clear_failures()
        response = await api_client.get("/api/v1/projects")
        
        assert response.status_code == 200
        # Circuit should now be CLOSED
        assert api_client._circuit_breaker.state == "CLOSED"
```

### 1.4 Example: Race Condition Test
```python
# backend/tests/e2e/race_conditions.py
@pytest.mark.asyncio
@pytest.mark.e2e
class TestRaceConditions:
    """E2E-005: Concurrent test runs (isolation & no crosstalk)"""
    
    async def test_50_parallel_runs_isolated(self, project_factory, api_client):
        """
        Scenario: 50 test runs execute concurrently in same project
        Expected: No state corruption, proper isolation, all succeed
        
        This tests:
        - Mutex/locking on shared resources
        - Transaction isolation levels
        - Read-after-write consistency
        """
        # Setup: Create 50 independent test cases
        test_cases = [
            await project_factory.create_test_case(
                project_id=123,
                name=f"TC-{i:03d}",
                steps=[{"action": "click", "element": f"btn_{i}"}]
            )
            for i in range(50)
        ]
        
        # Execute: Launch 50 concurrent test runs
        async def execute_single(tc_id: int) -> dict:
            response = await api_client.post(
                f"/api/v1/test-execution/run",
                json={"test_case_id": tc_id},
            )
            assert response.status_code in (200, 202)
            return response.json()
        
        # Gather all results
        start_time = time.time()
        results = await asyncio.gather(
            *[execute_single(tc.id) for tc in test_cases],
            return_exceptions=True
        )
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Assert: All succeeded
        assert len(results) == 50
        assert all(not isinstance(r, Exception) for r in results)
        
        # Assert: No state corruption (fetch and verify each TC)
        for i, tc in enumerate(test_cases):
            tc_data = await api_client.get(f"/api/v1/test-cases/{tc.id}")
            assert tc_data.json()["name"] == f"TC-{i:03d}"
            
            # Verify run_count incremented properly
            assert tc_data.json()["total_runs"] == 1
        
        # Performance check
        avg_latency = elapsed_ms / 50
        print(f"Concurrent execution: {elapsed_ms:.0f}ms for 50 runs ({avg_latency:.0f}ms avg)")
        assert avg_latency < 2000  # < 2s per run under load
    
    async def test_defect_state_race(self, defect_factory, api_client):
        """
        Scenario: Two agents modify defect state simultaneously
        Expected: Final state is consistent, one operation wins
        
        This tests:
        - Optimistic locking (version field)
        - Conflict resolution
        - No data corruption
        """
        defect = await defect_factory.create(status="CLOSED")
        
        # Concurrent updates: Agent 1 → IN_PROGRESS, Agent 2 → REOPENED
        async def update_state(new_status: str):
            try:
                resp = await api_client.put(
                    f"/api/v1/defects/{defect.id}",
                    json={"status": new_status}
                )
                return resp.json() if resp.status_code == 200 else None
            except Exception as e:
                return e
        
        results = await asyncio.gather(
            update_state("IN_PROGRESS"),
            update_state("REOPENED"),
        )
        
        # One succeeds, one fails (conflict)
        successes = [r for r in results if r and not isinstance(r, Exception)]
        assert len(successes) == 1
        
        # Final state is valid
        final = await api_client.get(f"/api/v1/defects/{defect.id}")
        assert final.json()["status"] in ("IN_PROGRESS", "REOPENED")
```

### 1.5 Pytest Configuration for Chaos Tests
```python
# backend/pytest.ini (add markers)
markers =
    e2e: End-to-end scenario tests (chaos, race, timeouts)
    chaos: Chaos engineering tests (inject failures)
    race: Race condition tests (concurrent execution)
    timeout: Timeout cascade tests (deadline propagation)

# backend/conftest.py (add fixture)
@pytest.fixture(scope="session")
def event_loop():
    """Custom event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def api_client(db_session):
    """API client with chaos injection capability"""
    from tests.fixtures.chaos_api_client import ChaosApiClient
    return ChaosApiClient()
```

---

## Jira Sync Checklist

### 2.1 Database Migrations
```bash
# Generate migration
alembic revision --autogenerate -m "jira_bidirectional_sync"

# Review and apply
alembic upgrade head
```

### 2.2 Jira OAuth Configuration
```python
# backend/app/config.py (add to Settings)
class Settings(BaseSettings):
    JIRA_CLIENT_ID: str = Field(..., description="Jira OAuth client ID")
    JIRA_CLIENT_SECRET: str = Field(..., description="Jira OAuth secret")
    JIRA_INSTANCE_URL: str = Field(..., description="Jira instance (e.g., https://neurex.atlassian.net)")
    JIRA_WEBHOOK_SECRET: str = Field(..., description="Webhook HMAC secret")
    JIRA_SYNC_BATCH_SIZE: int = Field(100, description="Batch size for sync operations")
    JIRA_RATE_LIMIT_REQUESTS_PER_SEC: int = Field(10, description="Rate limit to Jira API")
    
    class Config:
        env_file = ".env"
```

### 2.3 Environment Variables (.env)
```bash
# .env
JIRA_CLIENT_ID=your_client_id_here
JIRA_CLIENT_SECRET=your_client_secret_here
JIRA_INSTANCE_URL=https://neurex.atlassian.net
JIRA_WEBHOOK_SECRET=your_webhook_secret_here
```

### 2.4 Router Registration
```python
# backend/app/core/router_registry.py (add if not exists)
from app.domains.jira.router import jira_router

DOMAIN_ROUTERS = {
    ...
    "jira": jira_router,
}
```

### 2.5 Async Service Task Definition
```python
# backend/app/domains/jira/service.py (additional setup)
from app.infra.models import AsyncJob

async def start_sync_task(org_id: int, direction: str) -> int:
    """
    Start background sync task.
    Returns: task_id for polling
    """
    task = AsyncJob(
        org_id=org_id,
        task_type="jira_sync",
        status="PENDING",
        metadata={
            "direction": direction,  # "tc_to_jira" or "jira_to_tc"
        }
    )
    session.add(task)
    await session.commit()
    
    # Queue background task
    background_tasks.add_task(
        jira_sync_worker,
        task_id=task.id,
        org_id=org_id,
        direction=direction
    )
    
    return task.id

async def jira_sync_worker(task_id: int, org_id: int, direction: str):
    """Background worker for sync"""
    task = await session.get(AsyncJob, task_id)
    task.status = "IN_PROGRESS"
    task.started_at = datetime.utcnow()
    await session.commit()
    
    try:
        service = JiraSyncService(session, jira_client, cache)
        if direction == "tc_to_jira":
            result = await service.sync_test_cases_to_jira(org_id)
        else:
            result = await service.sync_jira_issues_to_test_cases(org_id)
        
        task.status = "COMPLETED"
        task.metadata["result"] = result
    except Exception as e:
        task.status = "FAILED"
        task.metadata["error"] = str(e)
    finally:
        task.completed_at = datetime.utcnow()
        await session.commit()
```

### 2.6 Testing Jira Sync
```bash
# Run Jira sync tests
pytest backend/tests/test_jira_sync.py -v -s

# Run with coverage
pytest backend/tests/test_jira_sync.py --cov=app.domains.jira --cov-report=html

# Watch mode (if using pytest-watch)
ptw backend/tests/test_jira_sync.py
```

---

## Slack Setup

### 3.1 Slack App Configuration
1. **Go to** https://api.slack.com/apps
2. **Create New App** → From scratch
3. **App Name:** Neurex
4. **Workspace:** Your test workspace
5. **OAuth & Permissions:**
   - `chat:write` — Send messages
   - `channels:read` — List channels
   - `files:write` — Upload files (for charts)
   - `users:read` — Get user info
6. **Install App** → Copy `Bot Token` (xoxb-...)
7. **Webhook Events:**
   - URL: `https://neurex.local/api/engine/jira/webhook/issue-changed`
   - Subscribe to: `issue_updated`, `issue_created`
8. **Save** → Copy `Signing Secret`

### 3.2 Environment Configuration
```bash
# .env
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_WEBHOOK_SECRET=your-webhook-secret-here
SLACK_CHANNEL_RUNS=#neurex-runs
SLACK_CHANNEL_DEFECTS=#neurex-defects
SLACK_CHANNEL_DAILY=#neurex-daily
```

### 3.3 Slack Client Wrapper
```python
# backend/app/integrations/slack_client.py
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class AsyncSlackClient:
    """Async wrapper around Slack SDK"""
    
    def __init__(self, bot_token: str):
        self.client = WebClient(token=bot_token)
    
    async def post_message(self, channel: str, **kwargs):
        """Send message to channel"""
        try:
            response = self.client.chat_postMessage(
                channel=channel,
                **kwargs
            )
            return response["ts"]  # Message timestamp
        except SlackApiError as e:
            raise SlackDeliveryError(f"Failed to post: {e.response['error']}")
    
    async def upload_file(self, channels: list, file: bytes, filename: str):
        """Upload file (for charts)"""
        try:
            response = self.client.files_upload(
                channels=channels,
                file=file,
                filename=filename
            )
            return response["file"]["id"]
        except SlackApiError as e:
            raise SlackDeliveryError(f"Failed to upload: {e.response['error']}")
    
    async def get_channel_info(self, channel_name: str) -> dict:
        """Get channel ID by name"""
        try:
            response = self.client.conversations_list()
            for chan in response["channels"]:
                if chan["name"] == channel_name.lstrip("#"):
                    return {"id": chan["id"], "name": chan["name"]}
            raise ValueError(f"Channel {channel_name} not found")
        except SlackApiError as e:
            raise SlackDeliveryError(f"Failed to get channel: {e.response['error']}")

@lru_cache
def get_slack_client() -> AsyncSlackClient:
    """Dependency injection"""
    return AsyncSlackClient(settings.SLACK_BOT_TOKEN)
```

### 3.4 Testing Slack Integration
```bash
# Run Slack notification tests
pytest backend/tests/test_slack_notifications.py -v

# Test webhook signature verification
pytest backend/tests/test_slack_webhook.py -v

# Integration test (requires live Slack workspace)
pytest backend/tests/test_slack_notifications.py -m integration
```

---

## Performance Setup

### 4.1 k6 Installation & Configuration
```bash
# Install k6
brew install k6

# Verify
k6 --version

# Install plugins (if using)
k6 version
```

### 4.2 k6 Test Execution
```bash
# Run baseline (5min)
k6 run performance-tests/perf-v2/baseline-full-stack.js \
  --vus 50 \
  --duration 5m \
  -e BASE_URL=http://localhost:8000 \
  -e API_TOKEN=eyJ...

# Run with output to JSON (for analysis)
k6 run performance-tests/perf-v2/baseline-full-stack.js \
  -o json=baseline-results.json

# Run in cloud (k6 Cloud dashboard)
k6 cloud performance-tests/perf-v2/baseline-full-stack.js
```

### 4.3 Prometheus + Grafana Setup
```bash
# Start Prometheus
docker run -d \
  -p 9090:9090 \
  -v ./infra/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Start Grafana
docker run -d \
  -p 3001:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana

# Access
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

### 4.4 Grafana Dashboard Import
1. Go to http://localhost:3001
2. **Create** → **Import**
3. **Paste JSON** from `infra/grafana/dashboards/perf-baseline-v2.json`
4. **Save** → View metrics in real-time

### 4.5 Running Baseline Tests
```bash
# Full baseline suite (15min)
make test-perf-baseline-v2

# Or manual:
cd backend && pytest tests/perf/test_baseline_v2.py -v

# With profiling
pytest tests/perf/test_baseline_v2.py --profile
```

---

## Deployment & Monitoring

### 5.1 Deploy to Staging
```bash
# 1. Merge to feature branch
git checkout -b feature/q1-enhancements main

# 2. Create migrations
alembic revision --autogenerate -m "q1_enhancements"

# 3. Run tests
make test-regression

# 4. Build Docker image
docker build -t neurex-backend:q1-latest .

# 5. Deploy to staging
kubectl set image deployment/neurex-backend \
  neurex-backend=neurex-backend:q1-latest \
  -n staging
```

### 5.2 Monitoring Dashboard
```yaml
# infra/prometheus/rules/q1-alerts.yml
groups:
  - name: q1_enhancements
    interval: 30s
    rules:
      - alert: JiraSyncFailureRate
        expr: rate(jira_sync_errors_total[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Jira sync error rate > 5%"
      
      - alert: SlackDeliveryQueueBacklog
        expr: slack_queue_pending_messages > 1000
        for: 10m
        annotations:
          summary: "Slack notification queue backlog > 1000"
      
      - alert: ChaosTestFailure
        expr: rate(chaos_test_failures_total[5m]) > 0.01
        for: 2m
        annotations:
          summary: "Chaos test failure rate > 1%"
```

### 5.3 Health Check Endpoints
```python
# backend/app/domains/health/router.py (add to health domain)
@health_router.get("/readiness")
async def readiness_check():
    """Readiness for Q1 features"""
    checks = {
        "jira_sync_service": await check_jira_service(),
        "slack_client": await check_slack_client(),
        "chaos_test_framework": await check_chaos_framework(),
        "perf_baseline": await check_perf_baseline(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
    }, status_code
```

---

## Troubleshooting

### Issue: Jira OAuth Token Expired
```python
# Solution: Implement refresh token logic
async def refresh_jira_token():
    response = await httpx.post(
        "https://auth.atlassian.com/oauth/token",
        json={
            "grant_type": "refresh_token",
            "client_id": settings.JIRA_CLIENT_ID,
            "client_secret": settings.JIRA_CLIENT_SECRET,
            "refresh_token": stored_refresh_token,
        }
    )
    new_token = response.json()["access_token"]
    await cache.set("jira_access_token", new_token, ex=3600)
```

### Issue: Slack Webhook Signature Validation Fails
```python
# Solution: Verify signing secret
import hmac
import hashlib

def verify_slack_signature(request_body: bytes, signature: str, secret: str) -> bool:
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    basestring = f"v0:{timestamp}:{request_body.decode()}"
    
    my_signature = f"v0={hmac.new(
        secret.encode(),
        basestring.encode(),
        hashlib.sha256
    ).hexdigest()}"
    
    return hmac.compare_digest(my_signature, signature)
```

### Issue: Chaos Tests Flaky (Race Condition)
```python
# Solution: Use proper async synchronization
from asyncio import Lock

class TestDataFactory:
    _lock = Lock()
    _counter = 0
    
    @classmethod
    async def create_test_case(cls, **kwargs):
        async with cls._lock:
            cls._counter += 1
            kwargs.setdefault("name", f"TC-{cls._counter:06d}")
        
        return await TestCase.create(**kwargs)
```

### Issue: Jira Sync Hangs on Large Batch
```python
# Solution: Implement pagination with checkpoints
async def sync_test_cases_with_pagination(org_id: int, page_size: int = 100):
    offset = 0
    while True:
        batch = await session.execute(
            select(TestCase)
            .where(TestCase.org_id == org_id)
            .order_by(TestCase.id)
            .offset(offset)
            .limit(page_size)
        )
        
        tcs = batch.scalars().all()
        if not tcs:
            break
        
        # Save checkpoint
        checkpoint = JiraSyncCheckpoint(
            org_id=org_id,
            last_synced_id=tcs[-1].id,
            synced_count=offset + len(tcs),
        )
        session.add(checkpoint)
        await session.commit()
        
        # Sync this batch
        for tc in tcs:
            await sync_single_test_case(tc)
        
        offset += page_size
        await asyncio.sleep(1)  # Rate limit
```

### Issue: Performance Baseline Regression
```bash
# Solution: Compare against baseline
k6 run performance-tests/perf-v2/baseline-full-stack.js \
  -o json=current-baseline.json

# Analyze
python3 scripts/compare_baselines.py \
  baseline-v1.json current-baseline.json

# Expected output:
# P99 Latency: 145ms → 95ms (34% improvement ✅)
# Cache Hit Rate: 45% → 82% (82% improvement ✅)
# Throughput: 420 → 620 req/s (48% improvement ✅)
```

---

## Quick Reference: Make Targets

Add to `Makefile`:
```makefile
.PHONY: test-e2e-chaos test-jira-sync test-slack test-perf-baseline

test-e2e-chaos:
	pytest backend/tests/e2e/chaos_patterns.py -v -s

test-jira-sync:
	pytest backend/tests/test_jira_sync.py -v

test-slack:
	pytest backend/tests/test_slack_notifications.py -v

test-perf-baseline:
	cd backend && pytest tests/perf/test_baseline_v2.py -v

perf-baseline-k6:
	k6 run performance-tests/perf-v2/baseline-full-stack.js \
	  -e BASE_URL=http://localhost:8000 \
	  -e API_TOKEN=$$JWT_TOKEN

test-q1-all: test-e2e-chaos test-jira-sync test-slack test-perf-baseline
	@echo "✅ Q1 Enhancement Suite Passed"
```

---

## Summary Checklist

- [ ] E2E Chaos Framework deployed
  - [ ] `tests/e2e/` directory created
  - [ ] `ChaosApiClient` fixture implemented
  - [ ] 10 scenario tests written
  - [ ] Chaos markers added to pytest.ini
  
- [ ] Jira Integration complete
  - [ ] Database migrations applied
  - [ ] OAuth configured (client_id, secret)
  - [ ] `JiraSyncService` implemented
  - [ ] Router endpoints mounted
  - [ ] 15 test cases passing
  
- [ ] Slack Integration complete
  - [ ] Slack app created + tokens configured
  - [ ] `SlackNotificationService` implemented
  - [ ] Notification templates (run, defect, digest)
  - [ ] Retry queue with exponential backoff
  - [ ] 10 test cases passing
  
- [ ] Performance Baseline v2 deployed
  - [ ] k6 tests written (11 tests)
  - [ ] Prometheus + Grafana dashboard active
  - [ ] Baseline metrics recorded
  - [ ] SLO alerts configured
  
- [ ] CI/CD Integration
  - [ ] `.github/workflows/q1-enhancement.yml` created
  - [ ] Nightly chaos tests scheduled
  - [ ] Performance regression detection enabled
  - [ ] Slack status notifications active
  
- [ ] Documentation
  - [ ] Architecture diagrams created
  - [ ] API reference updated
  - [ ] Runbooks written
  - [ ] Troubleshooting guide published

