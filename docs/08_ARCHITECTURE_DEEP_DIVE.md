# Neurex Architecture Deep-Dive

**Last Updated:** 2026-06-09  
**Scope:** Complete system design, data flow, integration patterns  
**Audience:** Architects, senior engineers, decision makers  
**Design Status:** Production-Proven, Cloud-Native

---

## Table of Contents

1. [System Design Overview](#system-design-overview)
2. [Microservices Architecture](#microservices-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Domain-Driven Design](#domain-driven-design)
5. [Resilience Patterns](#resilience-patterns)
6. [Scalability Architecture](#scalability-architecture)
7. [Integration Patterns](#integration-patterns)
8. [Technology Stack Decisions](#technology-stack-decisions)

---

## System Design Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       User Layer                            │
├──────────────────────────────┬──────────────────────────────┤
│  Web Browser (React/Next.js) │  Mobile (Native/Web)        │
│  (http://localhost:3000)      │  (Responsive UI)           │
└──────────────────┬───────────┴────────────┬─────────────────┘
                   │ HTTPS/WS              │
                   ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│               API Gateway Layer (Load Balancer)             │
│  - Request routing                                          │
│  - Rate limiting                                            │
│  - TLS termination                                          │
│  - Request correlation ID                                  │
└──────────────────┬───────────────────────────────────────────┘
                   │ TCP:8000
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Backend (3 replicas, auto-scaling 3-10)           │
│                                                              │
│  ├─► Domain Routers (53 modules)                           │
│  ├─► Service Layer (business logic)                        │
│  ├─► Repository Layer (data access)                        │
│  └─► Middleware (auth, logging, tracing)                   │
└────────────────┬──────────────────────────────────────────┬─┘
                 │                                          │
      ┌──────────▼────────────┐          ┌────────────────▼──┐
      │ PostgreSQL Primary    │          │ Redis Cache       │
      │ (RLS per tenant_id)   │          │ (Session + Cache) │
      │                       │          │                   │
      │ - Tables: 60+         │          │ - DB: 0 (session) │
      │ - pgvector ext        │          │ - DB: 1 (cache)   │
      │ - Read-replica sync   │          │                   │
      └──────────────────────┘          └───────────────────┘
           ▲      │
           │      └──► Replication (Faz 3.1)
           │
    ┌──────┴─► Read Replica (Faz 3.1)
    │          (Read-only copy)
    │
    ├──► Backup (pg_dump daily)
    └──► Audit Log (PostgreSQL audit)

┌──────────────────────────────────────────────────────────────┐
│  Engine (Flask, Internal Only)                               │
│  Port: 5001 (no internet)                                   │
│  Auth: X-Internal-Key header                               │
│                                                              │
│  ├─► Test Execution Engine                                 │
│  ├─► Playwright/Appium/Selenium drivers                    │
│  ├─► Locator strategy & resolution                         │
│  └─► Test artifact generation                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  AI Gateway (FastAPI, Port 8080, Internal)                   │
│  Provider Fallback Chain:                                   │
│    1. Ollama (local models, fast)                           │
│    2. vLLM (local inference, optimized)                     │
│    3. Groq (fast inference cloud)                           │
│    4. Gemini (Google LLM)                                   │
│    5. OpenAI (fallback)                                     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  External Integrations (Event-Driven)                        │
│                                                              │
│  ├─► Jira (webhook + API sync)                             │
│  ├─► GitHub/GitLab (CI/CD webhooks)                        │
│  ├─► Slack (notifications)                                 │
│  ├─► Email (SendGrid)                                      │
│  ├─► S3/MinIO (artifact storage)                           │
│  └─► DataDog/Sentry (observability)                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Microservices Architecture

### Service Topology

Neurex uses **53 domain modules** organized as a monolith (not split into separate services).

**Why monolith + domains?**
- ✅ Single deployment unit
- ✅ Transactions across domains (ACID)
- ✅ Easier to debug (no distributed tracing complexity)
- ✅ Simpler authorization (RLS at DB layer)
- ✅ Scales vertically for now, can split to microservices later

### Domain Structure

Each domain follows **DDD (Domain-Driven Design)** pattern:

```
backend/app/domains/<domain>/
├── router.py           # HTTP endpoints
├── service.py          # Business logic
├── schemas.py          # Pydantic models (request/response)
├── models.py           # SQLAlchemy ORM models
├── repository.py       # Data access (queries)
├── exceptions.py       # Domain-specific exceptions
└── tests/
    ├── test_service.py # Unit tests (pure functions)
    └── test_router.py  # Integration tests (HTTP + DB)
```

### Example Domain: Test Management

```
backend/app/domains/test_management/
├── router.py
│   ├── POST   /test-cases              → create_case()
│   ├── GET    /test-cases              → list_cases()
│   ├── GET    /test-cases/{id}         → get_case()
│   ├── PATCH  /test-cases/{id}         → update_case()
│   ├── DELETE /test-cases/{id}         → delete_case()
│   └── POST   /test-cases/bulk-import  → bulk_import()
│
├── service.py
│   ├── create_test_case(title, description, ...)
│   ├── get_test_cases_for_project(project_id)
│   ├── update_test_case_priority(case_id, priority)
│   ├── delete_test_case(case_id)
│   └── analyze_test_automation_gaps()
│
├── schemas.py
│   ├── CreateTestCaseRequest
│   ├── UpdateTestCaseRequest
│   ├── TestCaseResponse
│   ├── BulkImportRequest
│   └── TestCaseMetricsResponse
│
└── models.py
    ├── TestCase (SQLAlchemy model)
    ├── TestCaseStep
    ├── TestCaseTag
    └── TestCaseMetrics (denormalized for perf)
```

---

## Data Flow Diagrams

### Login Flow (Authentication)

```
User                    Frontend              Backend                 DB
 │                          │                     │                    │
 ├─ enter credentials       │                     │                    │
 │                          │                     │                    │
 └─ POST /auth/login ──────►│                     │                    │
                            │                     │                    │
                            ├─ POST to backend   │                    │
                            │ {email, password}  │                    │
                            │                     │                    │
                            │                  validate_password()    │
                            │                     ├────► SELECT * FROM users WHERE email = ?
                            │                     │◄────│
                            │                     │                    │
                            │                  pwd_context.verify()    │
                            │                     │                    │
                            │                  generate JWT tokens     │
                            │                     │                    │
                            │                  UPDATE user.last_login  │
                            │                     ├───►│ UPDATE users..
                            │                     │◄────│
                            │                     │                    │
                            │◄─ {access, refresh}─│                    │
                            │                     │                    │
 ◄─────────────────────────┤                     │                    │
 │ store tokens in         │                     │                    │
 │ HttpOnly cookie         │                     │                    │
 │                         │                     │                    │
```

### Test Case Creation & Automation

```
User                  Frontend           Backend                    AI Gateway
 │                        │                 │                          │
 ├─ Create test case      │                 │                          │
 │                        │                 │                          │
 │ title: "Login test"    │                 │                          │
 └─ POST /test-cases ────►│                 │                          │
                          │                 │                          │
                          ├─ POST /api/v1  │                          │
                          │                 │                          │
                          │         insert into test_cases              │
                          │         (id, project_id, title, ...)       │
                          │         VALUES(...)                        │
                          │                 │                          │
                          │                 ├─ emit: TestCaseCreated   │
                          │                 │                          │
                          │        (optional) Auto-generate steps? ────┤
                          │                 │                          │
                          │                 ├─ POST /v1/generate-steps │
                          │                 │                          │
                          │                 │ model=analyst            │
                          │                 │ prompt="steps for Login" │
                          │                 │────────────────────────►│
                          │                 │                          │
                          │                 │        (fallback chain)  │
                          │                 │      1. ollama (local)   │
                          │                 │      2. groq (fast)      │
                          │                 │      3. gemini           │
                          │                 │                          │
                          │                 │◄───────{steps}──────────│
                          │                 │                          │
                          │                 ├─ POST /test-case-steps  │
                          │                 │   INSERT steps[]         │
                          │                 │                          │
                          │◄───────────────┤ TestCaseCreated {id}     │
                          │                 │                          │
 ◄───────────────────────┤                 │                          │
 │ show created test case │                 │                          │
 │                        │                 │                          │
```

### Test Execution Flow (RQ Job Queue)

```
User                Frontend          Backend                    Engine              Redis Queue
 │                      │                │                         │                    │
 ├─ Run test cases      │                │                         │                    │
 │                      │                │                         │                    │
 └─ POST /runs ────────►│                │                         │                    │
                        │                │                         │                    │
                        ├─ POST          │                         │                    │
                        │                │                         │                    │
                        │      create_run()                        │                    │
                        │      INSERT test_runs                    │                    │
                        │      (status='queued')                   │                    │
                        │                │                         │                    │
                        │       Enqueue job to Redis ─────────────►│                    │
                        │                │                         │    LPUSH rq:queue │
                        │                │                         │                ───►│
                        │                │                         │                    │
                        ◄────────────────┤ {run_id, status='queue'}│                    │
                        │                │                         │                    │
 ◄──────────────────────┤                │                         │                    │
 │ (polling) GET /runs/ │                │                         │                    │
 │          /{run_id}   │                │                         │                    │
 │                      │                │                         │                    │
 └──────────────────────┤                │                         │                    │
                        │                │                         │                    │
                        ├─ GET /runs/123 │                         │                    │
                        │     (status:    │                         │                    │
                        │      running)   │                         │                    │
                        │                │                         │                    │
                        │              RQ Worker (background)      │                    │
                        │                │◄──────LPOP──────────────┤◄───────────────────│
                        │                │                         │                    │
                        │                │    UPDATE test_runs SET │                    │
                        │                │    status='running'     │                    │
                        │                │                         │                    │
                        │                │    For each case_id:    │                    │
                        │                │    POST /execute ──────►│                    │
                        │                │    {case_id, steps}     │                    │
                        │                │                         │                    │
                        │                │                    Launch browser           │
                        │                │                    Execute steps            │
                        │                │                    Take screenshots         │
                        │                │                    Compare results         │
                        │                │                         │                    │
                        │                │◄───{result, artifacts}──│                    │
                        │                │                         │                    │
                        │                │    INSERT test_run_results                  │
                        │                │                         │                    │
                        │                │    UPDATE test_runs SET │                    │
                        │                │    status='completed'   │                    │
                        │                │    passed_count=15      │                    │
                        │                │    failed_count=2       │                    │
                        │                │                         │                    │
 ◄──────────────────────┤                │                         │                    │
 │ GET returns:         │                │                         │                    │
 │ {status: completed,  │                │                         │                    │
 │  passed: 15,         │                │                         │                    │
 │  failed: 2}          │                │                         │                    │
 │                      │                │                         │                    │
```

---

## Domain-Driven Design

### Bounded Contexts (Domains)

Neurex organizes business logic into isolated domains:

```
┌─────────────────────────────────────────────────────┐
│  Auth Domain                                        │
│  ├─ Login/Logout                                   │
│  ├─ Token management                               │
│  ├─ MFA                                             │
│  └─ Permission checks                              │
└─────────────────────────────────────────────────────┘
         │
         │ (Auth context set in request)
         ▼
┌─────────────────────────────────────────────────────┐
│  Test Management Domain                             │
│  ├─ Test case CRUD                                 │
│  ├─ Test step management                           │
│  ├─ Test metrics (automation coverage)             │
│  └─ Test tagging                                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Test Execution Domain                              │
│  ├─ Run creation                                    │
│  ├─ Result tracking                                │
│  ├─ Artifact management                            │
│  └─ Performance metrics                             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Defect Domain                                      │
│  ├─ Defect creation (from failed tests)            │
│  ├─ Severity/Priority classification               │
│  ├─ Jira sync                                      │
│  └─ Defect trend analysis                          │
└─────────────────────────────────────────────────────┘

... 49 more domains
```

### Anti-Corruption Layer (ACL)

When integrating with external systems, use anti-corruption layer to translate:

```python
# Example: Jira integration
# app/domains/jira/acl.py

class JiraACL:
    """Translate between Neurex and Jira domain models."""
    
    @staticmethod
    def neurex_defect_to_jira_issue(defect: Defect) -> dict:
        """Convert Neurex defect to Jira issue format."""
        return {
            "fields": {
                "project": {"key": "PROJ"},
                "summary": defect.title,
                "description": defect.description,
                "issuetype": {"name": "Bug"},
                "priority": {
                    "critical": "Highest",
                    "high": "High",
                    "medium": "Medium",
                    "low": "Low",
                }[defect.severity],
            }
        }
    
    @staticmethod
    def jira_issue_to_neurex_defect(issue: dict) -> Defect:
        """Convert Jira issue back to Neurex defect."""
        return Defect(
            title=issue["fields"]["summary"],
            description=issue["fields"]["description"],
            jira_issue_key=issue["key"],
            severity={
                "Highest": "critical",
                "High": "high",
                "Medium": "medium",
                "Low": "low",
            }.get(issue["fields"]["priority"]["name"], "medium"),
        )
```

---

## Resilience Patterns

### Circuit Breaker Pattern

Prevent cascading failures when external services are slow/down:

```python
# app/infra/resilience.py

from pybreaker import CircuitBreaker

ai_gateway_breaker = CircuitBreaker(
    fail_max=5,              # Open after 5 failures
    reset_timeout=60,        # Try again after 60s
    listeners=[
        lambda cb, *args: logger.warning(f"AI Gateway circuit open"),
    ]
)

@ai_gateway_breaker
async def call_ai_gateway(prompt: str) -> str:
    response = await httpx.post(
        "http://ai-gateway:8080/v1/complete",
        json={"prompt": prompt}
    )
    return response.json()

# Usage:
try:
    result = await call_ai_gateway("Generate test")
except CircuitBreakerListener:
    logger.error("AI Gateway unavailable, using fallback")
    result = fallback_generate_test()
```

### Retry with Exponential Backoff

```python
async def call_external_api_with_retry(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            response = await httpx.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Retry {attempt+1}/{max_retries} after {wait_time}s: {e}")
            await asyncio.sleep(wait_time)
```

### Timeout Context (Deadline)

Prevent queries from running forever:

```python
# app/core/runtime.py

class QueryDeadlineContext:
    """Set deadline for database queries."""
    
    def __init__(self, timeout_seconds: float = 30):
        self.timeout = timeout_seconds
    
    async def __aenter__(self):
        # Postgres: SET local statement_timeout
        await self.session.execute(
            text(f"SET LOCAL statement_timeout = {self.timeout * 1000}")
        )
    
    async def __aexit__(self, *args):
        pass

# Usage:
async def slow_query():
    async with QueryDeadlineContext(timeout_seconds=30):
        result = await db.query(TestCase).all()  # Will error if > 30s
```

### Bulkhead Pattern

Isolate resources to prevent one task from consuming all capacity:

```python
# Thread pools for different task types
ai_generation_pool = ThreadPoolExecutor(max_workers=3)
email_pool = ThreadPoolExecutor(max_workers=5)
webhook_pool = ThreadPoolExecutor(max_workers=2)

# Queue with max size
test_execution_queue = asyncio.Queue(maxsize=100)

# If queue is full, reject new requests
async def enqueue_test_run(run_id: str):
    try:
        await asyncio.wait_for(
            test_execution_queue.put(run_id),
            timeout=1.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Queue full, try again later")
```

---

## Scalability Architecture

### Horizontal Scaling

**Backend API Servers:**
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3  # Auto-scale 3-10 based on CPU/Memory
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/db  # Shared DB
      REDIS_URL: redis://redis:6379/0  # Shared Redis
```

**Kubernetes auto-scaling:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: neurex-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: neurex-backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Database Scaling Strategy

**Phase 1 (Current): Single PostgreSQL**
- Good for: < 1M test cases
- Limit: Single machine resources

**Phase 2: Read Replica (Faz 3.1 — Implemented)**
- Replicate all writes to read-only replica
- Route SELECT queries to replica (with sticky reads)
- Benefit: Scale read throughput

**Phase 3: Sharding (Future)**
- Shard by tenant_id or project_id
- Separate database per shard
- Benefit: Unlimited scale

### Cache Scalability

**Current (Redis single instance):**
- Good for: < 10GB cache size
- Limit: Memory capacity

**Future (Redis Cluster):**
```
Redis Node 1 (3GB)  --\
Redis Node 2 (3GB)  ---[Cluster]---►  Gossip protocol
Redis Node 3 (3GB)  --/  (16 shards)  Auto rebalancing
```

---

## Integration Patterns

### Webhook Integration (Outgoing)

Neurex sends events to external systems:

```python
# app/domains/webhook/service.py

class WebhookService:
    async def deliver_webhook(
        self,
        webhook_id: str,
        event: dict,
        retry: int = 0
    ):
        webhook = await db.query(Webhook).filter_by(id=webhook_id).first()
        
        # Sign webhook (HMAC-SHA256)
        payload = json.dumps(event)
        signature = hmac.new(
            webhook.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Send with exponential backoff
        try:
            response = await httpx.post(
                webhook.url,
                json=event,
                headers={
                    "X-Webhook-Signature": signature,
                    "X-Webhook-ID": webhook_id,
                    "X-Delivery-ID": str(uuid.uuid4())
                },
                timeout=10
            )
            
            # Log delivery
            await db.create(WebhookLog)(
                webhook_id=webhook_id,
                event_type=event["type"],
                response_status=response.status_code,
                delivered_at=datetime.utcnow()
            )
            
        except Exception as e:
            if retry < 3:
                # Retry with backoff (2^retry seconds)
                await asyncio.sleep(2 ** retry)
                await self.deliver_webhook(webhook_id, event, retry + 1)
            else:
                logger.error(f"Webhook delivery failed after 3 retries: {e}")
```

### Jira Sync (Bidirectional)

```python
# app/domains/jira/service.py

class JiraSyncService:
    async def sync_defect_to_jira(self, defect: Defect):
        """Neurex → Jira"""
        # Convert to Jira format
        jira_issue = JiraACL.neurex_defect_to_jira_issue(defect)
        
        # Create in Jira
        response = await self.jira_client.create_issue(jira_issue)
        
        # Store mapping
        defect.jira_issue_key = response["key"]
        await db.commit()
    
    async def sync_jira_to_neurex(self, issue_key: str):
        """Jira → Neurex (webhook triggered)"""
        # Fetch from Jira
        jira_issue = await self.jira_client.get_issue(issue_key)
        
        # Check if we already have this defect
        defect = await db.query(Defect).filter_by(
            jira_issue_key=issue_key
        ).first()
        
        if defect:
            # Update existing
            jira_issue_data = JiraACL.jira_issue_to_neurex_defect(jira_issue)
            for field, value in jira_issue_data.items():
                setattr(defect, field, value)
        else:
            # Create new
            defect = JiraACL.jira_issue_to_neurex_defect(jira_issue)
            db.add(defect)
        
        await db.commit()
```

### Event-Driven Architecture (Outbox Pattern)

Ensure reliability of async events (don't lose events if service crashes):

```python
# app/infra/outbox.py

class OutboxService:
    """Ensure events are reliably delivered even if service crashes."""
    
    async def emit_event(
        self,
        event_type: str,
        entity_id: str,
        data: dict
    ):
        # 1. Create outbox record (same transaction as main change)
        outbox_record = OutboxEvent(
            event_type=event_type,
            entity_id=entity_id,
            payload=data,
            created_at=datetime.utcnow()
        )
        session.add(outbox_record)
        await session.commit()  # Atomically save both
        
        # 2. Background worker processes outbox
        # (separate transaction)
        async def process_outbox():
            records = await db.query(OutboxEvent).filter(
                OutboxEvent.processed_at.is_(None)
            ).all()
            
            for record in records:
                try:
                    await self.deliver_event(record)
                    record.processed_at = datetime.utcnow()
                    await db.commit()
                except Exception as e:
                    logger.error(f"Event delivery failed: {e}")
                    # Retry on next iteration
        
        # Enqueue background task
        await task_queue.enqueue(process_outbox)
```

---

## Technology Stack Decisions

### Why FastAPI?

- ✅ Async/await support (modern Python)
- ✅ Automatic OpenAPI documentation
- ✅ Fast execution (near C performance)
- ✅ Type hints validation (Pydantic)
- ✅ Large ecosystem (SQLAlchemy, Celery, etc)

**Considered alternatives:**
- Django: Too much ORM magic, slower
- Starlette: Lower-level (FastAPI builds on it)
- Flask: Synchronous only (we need async)

### Why PostgreSQL?

- ✅ ACID transactions (data integrity)
- ✅ Row Level Security (multi-tenancy)
- ✅ pgvector extension (AI embeddings)
- ✅ Trigger support (audit logging)
- ✅ Excellent Python support (psycopg3)

**Considered alternatives:**
- MySQL: No RLS, weaker ACID
- MongoDB: No transactions, complex to scale
- Cassandra: Eventually consistent (not suitable for accounting)

### Why Redis?

- ✅ Sub-millisecond latency (cache)
- ✅ Atomic operations (session management)
- ✅ Pub/Sub (real-time updates)
- ✅ Expiration (automatic TTL)

**Considered alternatives:**
- Memcached: No persistence, no TTL
- DynamoDB: Too slow for cache
- Elasticsearch: Over-featured for cache

### Why Next.js Frontend?

- ✅ Server-side rendering (SEO, performance)
- ✅ Static generation (fast initial load)
- ✅ Built-in image optimization
- ✅ Vercel deployment integration
- ✅ TypeScript support (type safety)

**Considered alternatives:**
- React SPA: No SSR, worse SEO
- Nuxt: Better for Vue (we use React)
- Svelte: Smaller community

---

## Monitoring & Observability

### Instrumentation

**Application metrics (Prometheus):**
```python
from prometheus_client import Counter, Histogram, Gauge

http_requests = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0)
)

active_connections = Gauge(
    'database_connections_active',
    'Active database connections'
)
```

**Distributed tracing (OpenTelemetry):**
```python
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider

jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    trace.BatchSpanProcessor(jaeger_exporter)
)

# Usage:
tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("test_execution") as span:
    span.set_attribute("test_id", test_id)
    # Code here
```

---

**End of Architecture Deep-Dive**
