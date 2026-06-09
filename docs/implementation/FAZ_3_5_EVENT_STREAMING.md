# Faz 3.5 — Event Streaming Integration (Kafka/Redis)

**Status:** Implementation Guide | **Date:** 2026-06-09  
**Scope:** Kafka/Redis event broker, consumer groups, schema registry, outbox migration

---

## Overview

Faz 3.5 upgrades event infrastructure from in-memory event bus + Redis Streams outbox relay to production-grade event streaming with schema versioning and exactly-once semantics.

### Goals
1. **Topic-based pub/sub** — Domain-specific topics (auth.events, test_management.events, etc.)
2. **Schema registry** — Avro/Protobuf versioning with backward/forward compatibility
3. **Exactly-once semantics** — Transactional producers + consumer groups
4. **Outbox → Kafka** — Migrate from Redis Streams to Kafka for scale
5. **Downstream consumers** — Analytics, webhooks, audit logs as separate services
6. **Backpressure handling** — Slow consumer detection, lag monitoring

---

## Architecture

### Event Flow (Post-Faz 3.5)

```
Domain Service
    ↓
[Outbox Table] — atomic write with business operation
    ↓
OutboxRelayKafka (background loop)
    ├─ Fetch pending entries (atomic claim)
    ├─ Map event_type → Kafka topic (e.g., "auth.user_login" → "auth.events")
    ├─ Publish with partition key (aggregate_id) for ordering
    └─ Mark as delivered/failed
    ↓
Kafka Broker (3-node cluster, 2x replication)
    ├─ Topic: "auth.events" (3 partitions)
    ├─ Topic: "test_management.events"
    ├─ Topic: "execution.events"
    ├─ Topic: "defect.events"
    └─ Topic: "audit.events"
    ↓
Consumer Groups (scale independently)
    ├─ analytics_processor (reads all topics)
    ├─ webhook_dispatcher (auth + defect events)
    ├─ audit_logger (audit topic)
    └─ ...custom subscribers
    ↓
Downstream Systems
    ├─ AnalyticsDB (Postgres materialized views)
    ├─ WebhookQueue (HTTP delivery)
    └─ AuditTrail (immutable log)
```

### Broker Selection

**Kafka** (Recommended for production):
- Partitioned topics → horizontal scaling
- Replication factor 2 → fault tolerance
- Offset management → exactly-once with consumer groups
- Retention policy → replay & recovery
- Performance: 1M+ msgs/sec per broker

**Redis Streams** (Development/small deployments):
- Single broker (no partitioning)
- Consumer groups with PEL
- Lower ops overhead
- Performance: 100K msgs/sec

---

## Topic Configuration

### Topic-per-Domain Pattern

| Topic | Domain | Partitions | Retention | Key |
|-------|--------|-----------|-----------|-----|
| `auth.events` | Authentication | 3 | 7 days | `user_id` |
| `test_management.events` | Test scenarios | 3 | 14 days | `project_id` |
| `execution.events` | Test execution | 3 | 30 days | `execution_id` |
| `defect.events` | Defect tracking | 3 | 30 days | `defect_id` |
| `audit.events` | Audit trail | 5 | 90 days | `tenant_id` |

### Partition Keys (Ordering Guarantees)

- **auth.events**: `user_id` — all user actions in order
- **test_management.events**: `project_id` — project scenario consistency
- **execution.events**: `execution_id` — test run ordering
- **defect.events**: `defect_id` — defect state machine ordering

---

## Schema Evolution

### Avro Schemas

```python
from app.infra.event_streaming.schemas import EventSchema, SchemaRegistry

# Define schema
auth_event_v1 = EventSchema(
    namespace="com.neurex.auth",
    name="UserLoginEvent",
    version=1,
    fields={
        "event_id": "string",
        "user_id": "string",
        "action": "string",
        "timestamp": "string",
        "success": "boolean",
    },
    doc="User login event",
    compatibility="BACKWARD",  # New versions can read v1 data
)

# Register
registry = get_schema_registry()
registry.register("auth.events", auth_event_v1)

# Later: Add field (backward compatible)
auth_event_v2 = EventSchema(
    namespace="com.neurex.auth",
    name="UserLoginEvent",
    version=2,
    fields={
        "event_id": "string",
        "user_id": "string",
        "action": "string",
        "timestamp": "string",
        "success": "boolean",
        "mfa_enabled": "boolean",  # NEW: optional in v1
    },
    compatibility="BACKWARD",
)
registry.register("auth.events", auth_event_v2)  # OK: backward compatible
```

### Compatibility Modes

| Mode | Rule | Example |
|------|------|---------|
| `BACKWARD` | New schema reads old data | Add optional fields |
| `FORWARD` | Old schema reads new data | Remove required fields |
| `FULL` | Both directions | Exact field set match |
| `NONE` | No compatibility | Breaking schema changes (force=True) |

---

## Installation & Setup

### 1. Add Dependencies

```bash
# backend/requirements.txt
aiokafka==0.8.0+         # Kafka async producer/consumer
redis==5.0.0+            # Redis async client
protobuf==4.24.0+        # Protobuf schema support (optional)
confluent-kafka==2.3.0+  # Confluent client (optional)
```

### 2. Start Kafka Cluster (Docker)

```bash
# Start 3-node Zookeeper + Kafka cluster + Kafka UI
docker compose -f infra/kafka-docker-compose.yml up -d

# Kafka UI: http://localhost:8888
# Create topics: auto-created by broker (KAFKA_AUTO_CREATE_TOPICS_ENABLE=true)
```

### 3. Database Migration

```bash
# Create streaming tables
alembic revision --autogenerate -m "event_streaming_tables"
alembic upgrade head
```

Migration creates:
- `stream_events` — published event log (audit trail)
- `consumer_group_offsets` — offset backup
- `consumer_group_metrics` — time-series metrics
- `event_subscriptions` — routing config
- `event_dlq` — dead-letter queue

### 4. Environment Configuration

```bash
# .env
# Broker selection
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
# OR
KAFKA_ENABLED=false
REDIS_STREAMS_ENABLED=true

# Relay behavior
OUTBOX_RELAY_ENABLED=true
OUTBOX_RELAY_POLL_INTERVAL_SECONDS=2
OUTBOX_RELAY_BATCH_SIZE=100

# Consumer groups
ANALYTICS_CONSUMER_GROUP=analytics-processor
WEBHOOK_CONSUMER_GROUP=webhook-dispatcher
```

---

## Usage Examples

### Publishing Events (Automatic via Outbox)

```python
from app.infra.outbox import OutboxRepository

# Service layer
def create_user(user_data):
    user = User.create(user_data)
    
    # Atomically write event to outbox table
    outbox_repo.append(
        OutboxEntry(
            event_type="auth.user_created",
            aggregate_id=user.id,
            payload={
                "user_id": user.id,
                "email": user.email,
                "action": "created",
            },
        )
    )
    
    # Background relay publishes to Kafka automatically
    return user
```

### Consumer: Analytics Processor

```python
from app.infra.event_streaming import ExactlyOnceConsumer

async def analytics_processor():
    """Consume auth + test_management events."""
    consumer = ExactlyOnceConsumer(
        group_id="analytics-processor",
        bootstrap_servers="localhost:9092",
    )
    
    await consumer.subscribe(["auth.events", "test_management.events"])
    
    async def on_event(msg: ConsumerMessage):
        print(f"Event: {msg.topic} #{msg.offset}")
        print(f"Payload: {msg.value}")
        
        # Update analytics DB
        if msg.topic == "auth.events":
            analytics_db.record_login(msg.value)
        elif msg.topic == "test_management.events":
            analytics_db.record_execution(msg.value)
    
    await consumer.consume(on_event)
```

### Consumer: Webhook Dispatcher

```python
async def webhook_dispatcher():
    """Send webhooks for auth + defect events."""
    consumer = RedisStreamConsumer(
        group_id="webhook-dispatcher",
        redis_url="redis://localhost:6379/1",
    )
    
    await consumer.subscribe(["auth.events", "defect.events"])
    
    async def send_webhook(msg: ConsumerMessage):
        webhook_url = config.get_webhook(msg.topic)
        if webhook_url:
            try:
                await http.post(webhook_url, json=msg.value, timeout=5)
            except Exception as e:
                raise  # Consumer will retry (up to max_retries)
    
    await consumer.consume(send_webhook)
```

### Schema Validation

```python
from app.infra.event_streaming.schemas import get_schema_registry

registry = get_schema_registry()

# Validate event before publishing
event = {"user_id": "...", "action": "login"}
if registry.validate_event("auth.events", event):
    await broker.publish("auth.events", event)
else:
    logger.error("Invalid event")
```

### Metrics & Monitoring

```python
async def monitor_consumer_lag():
    """Monitor consumer lag."""
    consumer = ExactlyOnceConsumer(group_id="analytics-processor")
    
    while True:
        metrics = await consumer.get_metrics()
        for m in metrics:
            print(f"Topic: {m.topic}, Lag: {m.lag}, Rate: {m.processing_rate}")
            
            if m.is_lagging(lag_threshold=1000):
                alert(f"Consumer lagging: {m.group_id} ({m.lag} msgs behind)")
        
        await asyncio.sleep(30)
```

---

## Deployment Scenarios

### Scenario 1: Development (Redis Streams, Single Node)

```yaml
# docker-compose.yml (existing)
redis:
  image: redis:7-alpine
  # ...
```

**Config:**
```bash
KAFKA_ENABLED=false
REDIS_STREAMS_ENABLED=true
REDIS_URL=redis://localhost:6379/1
```

**Setup:** No extra services needed. Outbox relay uses Redis broker.

---

### Scenario 2: Production (Kafka, 3-Node Cluster)

```bash
# Start Kafka cluster
docker compose -f infra/kafka-docker-compose.yml up -d

# Health check
kafka-broker-api-versions --bootstrap-server localhost:9092
```

**Config:**
```bash
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka-broker-1:9092,kafka-broker-2:9092,kafka-broker-3:9092
OUTBOX_RELAY_ENABLED=true
OUTBOX_RELAY_POLL_INTERVAL_SECONDS=2
OUTBOX_RELAY_BATCH_SIZE=100
```

**Services:**
```yaml
# docker-compose.yml updates
services:
  # Outbox relay (separate container)
  outbox-relay:
    build: ./backend
    command: python -m app.infra.event_streaming.outbox_relay_cli
    environment:
      DATABASE_URL: postgresql://...
      KAFKA_BOOTSTRAP_SERVERS: kafka-broker-1:9092,...
    depends_on:
      - postgres
      - kafka-broker-1
  
  # Analytics consumer
  analytics-processor:
    build: ./backend
    command: python -m app.services.analytics.consumer
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka-broker-1:9092,...
    depends_on:
      - kafka-broker-1
```

---

### Scenario 3: Hybrid (Kafka for core, Redis for webhooks)

```bash
# Start both
docker compose up -d redis
docker compose -f infra/kafka-docker-compose.yml up -d kafka-broker-1 kafka-broker-2 kafka-broker-3
```

**Config:**
```bash
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka-broker-1:9092,...
REDIS_STREAMS_ENABLED=true  # Webhooks use Redis
```

**Routing:**
```python
# Outbox relay publishes to Kafka (high-volume core events)
# Webhook consumer reads from Redis (lower priority)
```

---

## Migration Path: Redis Streams → Kafka

### Phase 1: Dual-write (1 week)

```python
# Outbox relay publishes to BOTH Redis + Kafka
class OutboxRelayDualWrite(OutboxRelayKafka):
    async def _publish_entry(self, entry):
        # Kafka
        kafka_id = await super()._publish_entry(entry)
        
        # Redis (fallback, legacy)
        redis_id = await self.redis_broker.publish(topic, event)
        
        return kafka_id
```

**Benefit:** Validate Kafka in production while Redis handles traffic.

### Phase 2: Kafka primary (1 week)

```python
# Consumers read from Kafka, ignore Redis
KAFKA_ENABLED=true
OUTBOX_RELAY_BROKER=kafka
```

**Validation:**
- Consumer lag < 100ms
- 0 DLQ entries
- All downstream systems healthy

### Phase 3: Redis cleanup (optional)

```bash
# Keep Redis for session cache, rate limiting
# Streams can be flushed
```

---

## Monitoring & Alerting

### Key Metrics

```python
# Consumer lag
lag = current_offset - committed_offset
alert if lag > 10000  # 10K msgs behind

# Processing rate
rate = msgs_processed / time_window
alert if rate < expected_rate * 0.5  # 50% drop

# Error rate (DLQ)
dlq_count = len(event_dlq)
alert if dlq_count > 100
```

### Logs

```bash
# Follow outbox relay logs
docker logs -f neurex_outbox_relay

# Kafka topic monitoring
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group analytics-processor --describe

# Lag overview
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --all-groups --describe
```

### Dashboards

- **Kafka UI**: http://localhost:8888 (topics, offsets, lag)
- **Consumer Metrics Dashboard**: Grafana + Prometheus (via app metrics)
- **DLQ Monitoring**: Custom endpoint `/admin/event-dlq`

---

## Testing

### Unit Tests: Schema Validation

```python
# tests/unit/test_event_schemas.py
def test_schema_backward_compat():
    v1 = EventSchema(name="LoginEvent", version=1, fields={"user_id": "string"})
    v2 = EventSchema(name="LoginEvent", version=2, 
                     fields={"user_id": "string", "mfa": "string"},
                     compatibility="BACKWARD")
    
    registry.register("auth.events", v1)
    registry.register("auth.events", v2)  # Should succeed
    
    # Old data (v1) can be read by v2
    old_event = {"user_id": "123"}
    assert registry.validate_event("auth.events", old_event)
```

### Integration Tests: Broker

```python
# tests/integration/test_kafka_broker.py
@pytest.mark.asyncio
async def test_kafka_publish_subscribe():
    broker = KafkaBroker(bootstrap_servers="localhost:9092")
    consumer = ExactlyOnceConsumer(group_id="test-group")
    
    # Publish
    msg_id = await broker.publish("test-topic", {"data": "test"})
    
    # Consume
    received = []
    async def handler(msg):
        received.append(msg)
    
    await consumer.subscribe(["test-topic"])
    # (run consume in background)
    
    await asyncio.sleep(0.5)
    assert len(received) == 1
    assert received[0].value == {"data": "test"}
```

### E2E Tests: Outbox Relay

```python
# tests/e2e/test_outbox_relay_kafka.py
@pytest.mark.asyncio
async def test_outbox_to_kafka_end_to_end():
    # Write to outbox
    outbox.append(OutboxEntry(
        event_type="auth.user_created",
        aggregate_id="user-123",
        payload={"email": "test@example.com"}
    ))
    
    # Run relay
    relay = build_kafka_relay(
        kafka_bootstrap_servers="localhost:9092",
        repository=outbox_repo,
    )
    await relay.process_batch()
    
    # Verify in Kafka
    consumer = ExactlyOnceConsumer(group_id="test")
    await consumer.subscribe(["auth.events"])
    received = []
    
    def handler(msg):
        received.append(msg)
    
    await asyncio.sleep(1)  # Wait for delivery
    assert len(received) == 1
    assert received[0].value["email"] == "test@example.com"
```

---

## Troubleshooting

### Issue: Consumer lag increasing (lagging)

**Cause:** Handler too slow, insufficient consumers
**Fix:**
```bash
# 1. Scale consumers (partition count = max consumers)
kafka-topics --bootstrap-server localhost:9092 \
  --topic auth.events --alter --partitions 5

# 2. Optimize handler
async def handler(msg):
    # Use batch processing instead of one-by-one
    batch.append(msg)
    if len(batch) >= 100:
        await db.insert_batch(batch)

# 3. Monitor processing rate
metrics = await consumer.get_metrics()
for m in metrics:
    print(f"Rate: {m.processing_rate} msgs/sec")
```

### Issue: DLQ filling up (poison messages)

**Cause:** Invalid event schema, downstream error
**Fix:**
```bash
# 1. Inspect DLQ
SELECT * FROM event_dlq WHERE resolved = false LIMIT 10;

# 2. Fix root cause
# - Update schema if backward incompatible
# - Fix downstream service
# - Re-queue if transient

# 3. Replay from DLQ
UPDATE event_dlq SET resolved = true WHERE id = '...';
INSERT INTO outbox (event_type, payload) SELECT ... FROM event_dlq;
```

### Issue: Kafka broker down (single broker)

**Cause:** Single point of failure
**Fix:**
```bash
# 1. Scale to 3 brokers
docker compose -f infra/kafka-docker-compose.yml up -d

# 2. Set replication_factor = 2 (auto on new topics)
KAFKA_DEFAULT_REPLICATION_FACTOR=2

# 3. Recovery after restart
kafka-broker-api-versions --bootstrap-server localhost:9092
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **Publish latency** | <10ms p99 | Kafka producer |
| **Consumer lag** | <100ms | Fresh data |
| **Throughput** | 100K+ msgs/sec | 3-node cluster |
| **Availability** | 99.9% | 2x replication |
| **Recovery time** | <5min | Broker failover |

---

## Next Steps (Faz 3.6+)

1. **Schema Registry Service** — External Confluent/AWS Schema Registry
2. **Event Sourcing** — Domain events as source of truth (instead of snapshots)
3. **CQRS** — Command-Query Responsibility Separation
4. **Temporal Events** — Time-travel debugging & audit trails
5. **Event Replay** — Rebuild projections from event stream
6. **Distributed Tracing** — OpenTelemetry integration per event

---

## References

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Avro Schema Evolution](https://avro.apache.org/docs/current/spec.html#schema_evolution)
- [Exactly-Once Semantics](https://kafka.apache.org/documentation/#semantics)
