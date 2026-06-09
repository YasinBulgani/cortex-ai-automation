# Event Streaming Infrastructure (Faz 3.5)

Production-grade event streaming with Kafka/Redis, schema registry, exactly-once semantics, and backpressure handling.

## Directory Structure

```
app/infra/event_streaming/
├── __init__.py                  # Package exports
├── broker.py                    # EventBroker interface, KafkaBroker, RedisBroker
├── consumer.py                  # ConsumerGroup, ExactlyOnceConsumer, RedisStreamConsumer
├── schemas.py                   # EventSchema, SchemaRegistry, schema evolution
├── models.py                    # SQLAlchemy models (stream_events, dlq, metrics)
├── outbox_relay_kafka.py        # Outbox → Kafka relay with exactly-once
├── outbox_relay_cli.py          # Standalone relay CLI
└── README.md                    # This file
```

## Quick Start

### 1. Install Dependencies

```bash
pip install aiokafka redis
```

### 2. Development (Redis Streams)

```python
from app.infra.event_streaming.broker import RedisBroker

broker = RedisBroker(redis_url="redis://localhost:6379/0")

# Publish
await broker.publish("auth.events", {
    "user_id": "123",
    "action": "login",
})

# Close
await broker.close()
```

### 3. Production (Kafka)

```python
from app.infra.event_streaming.broker import KafkaBroker

broker = KafkaBroker(bootstrap_servers="kafka-1:9092,kafka-2:9092,kafka-3:9092")

# Publish with partition key (guarantees ordering)
await broker.publish(
    "auth.events",
    {"user_id": "123", "action": "login"},
    partition_key="123"  # Routes to same partition
)

await broker.close()
```

### 4. Schema Registry

```python
from app.infra.event_streaming.schemas import EventSchema, get_schema_registry

registry = get_schema_registry()

# Define schema
schema = EventSchema(
    namespace="com.neurex.auth",
    name="UserLoginEvent",
    version=1,
    fields={
        "user_id": "string",
        "action": "string",
        "timestamp": "string",
    },
)

# Register
registry.register("auth.events", schema)

# Validate
event = {"user_id": "123", "action": "login", "timestamp": "2026-06-09T..."}
assert registry.validate_event("auth.events", event)
```

### 5. Consumers

```python
from app.infra.event_streaming.consumer import ExactlyOnceConsumer, ConsumerMessage

consumer = ExactlyOnceConsumer(
    group_id="analytics-processor",
    bootstrap_servers="kafka-1:9092",
)

await consumer.subscribe(["auth.events", "test_management.events"])

async def on_event(msg: ConsumerMessage):
    print(f"Event: {msg.topic} #{msg.offset}")
    print(f"Data: {msg.value}")
    # Process event (update DB, send webhooks, etc.)

await consumer.consume(on_event)  # Runs forever
```

## Core Components

### Broker Interface

```python
class EventBroker(ABC):
    async def publish(
        self,
        topic: str,
        event: dict,
        partition_key: Optional[str] = None
    ) -> str:
        """Publish event. Returns message ID (offset/entry)."""

    async def close(self) -> None:
        """Graceful shutdown."""
```

**Implementations:**
- **KafkaBroker**: Partitioned, replicated, exactly-once (production)
- **RedisBroker**: Single broker, lighter weight (dev/small deployments)

### Consumer Interface

```python
class ConsumerGroup(ABC):
    async def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics."""

    async def consume(
        self,
        handler: Callable[[ConsumerMessage], None],
        timeout_ms: int = 1000
    ) -> None:
        """Run consume loop, call handler for each message."""

    async def commit_offset(
        self,
        topic: str,
        partition: Optional[int],
        offset: Union[int, str]
    ) -> None:
        """Commit offset for consumer group."""

    async def get_metrics(self) -> List[ConsumerGroupMetrics]:
        """Get lag & performance metrics."""

    async def close(self) -> None:
        """Shutdown consumer."""
```

**Implementations:**
- **ExactlyOnceConsumer**: Kafka with transactional semantics, DLQ
- **RedisStreamConsumer**: Redis Streams with PEL tracking

### Schema Registry

```python
class SchemaRegistry:
    def register(self, topic: str, schema: EventSchema) -> SchemaVersion:
        """Register schema with compatibility check."""

    def get(self, topic: str, version: Optional[int] = None) -> Optional[EventSchema]:
        """Get schema by topic/version."""

    def validate_event(self, topic: str, event: dict) -> bool:
        """Validate event against latest schema."""

    def list_schemas(self) -> Dict[str, List[EventSchema]]:
        """List all registered schemas."""
```

**Features:**
- Schema versioning with explicit versions
- Backward/Forward/Full compatibility modes
- Avro & Protobuf export
- Automatic evolution checking

### Outbox Relay (Kafka)

```python
class OutboxRelayKafka:
    async def run_forever(
        self,
        poll_interval: float = 2.0,
        batch_size: int = 100
    ) -> None:
        """Run relay loop continuously."""

    async def process_batch(self, limit: int = 100) -> None:
        """Process one batch of pending outbox entries."""
```

**Features:**
- Atomic fetch + mark (skip_locked)
- Exactly-once via idempotent producer
- Partition-key routing for ordering
- Retry logic with dead-letter queue
- Event type → topic mapping

## Event Flow

### Publishing (Outbox Pattern)

```
Domain Service
    ↓
[Business Operation] + [Outbox.append()] — atomic write
    ↓
OutboxRelayKafka (background, 2s poll interval)
    ├─ Fetch pending entries (batch_size=100)
    ├─ Atomically mark as PROCESSING (skip_locked)
    ├─ Map event_type → Kafka topic
    ├─ Publish with partition key (aggregate_id)
    └─ Mark as DELIVERED or FAILED
    ↓
Kafka Broker (3-node cluster)
    ├─ Partition by key (ordering guarantee)
    ├─ Replicate to 2+ followers
    └─ Persist to disk (compression=snappy)
```

### Consuming (Exactly-Once)

```
Kafka Broker
    ↓
Consumer Group (isolation_level=read_committed)
    ├─ XREADGROUP: fetch uncommitted messages
    ├─ Call handler(message)
    ├─ If success: commit offset
    └─ If failure (max_retries exceeded): send to DLQ
    ↓
Application Handler
    ├─ Analytics: update materialized views
    ├─ Webhooks: send HTTP requests
    ├─ Audit: log to immutable trail
    └─ ... custom subscriptions
```

## Database Models

### stream_events

Published event audit trail (read-only, append-only).

```sql
CREATE TABLE stream_events (
    id UUID PRIMARY KEY,
    topic VARCHAR(255),           -- "auth.events"
    schema_name VARCHAR(255),     -- "UserLoginEvent"
    schema_version INTEGER,       -- 1, 2, ...
    tenant_id UUID,               -- Multi-tenancy
    correlation_id VARCHAR(255),  -- Request trace
    event_id VARCHAR(255) UNIQUE, -- Idempotency key
    payload JSONB,                -- Event data
    status VARCHAR(20),           -- "pending" | "published" | "failed"
    broker VARCHAR(50),           -- "kafka" | "redis"
    broker_message_id VARCHAR(255), -- Offset/entry ID
    published_at TIMESTAMP,
    consumed_count INTEGER,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_stream_events_topic ON stream_events(topic);
CREATE INDEX idx_stream_events_tenant ON stream_events(tenant_id);
CREATE INDEX idx_stream_events_status ON stream_events(status);
```

### consumer_group_offsets

Offset backup for recovery after consumer restart.

```sql
CREATE TABLE consumer_group_offsets (
    id UUID PRIMARY KEY,
    group_id VARCHAR(255),         -- "analytics-processor"
    topic VARCHAR(255),            -- "auth.events"
    partition INTEGER,             -- Kafka partition (NULL for Redis)
    broker VARCHAR(50),            -- "kafka" | "redis"
    committed_offset VARCHAR(255), -- Offset or entry ID
    lag INTEGER,                   -- Messages behind
    last_heartbeat TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_consumer_group_topic ON consumer_group_offsets(group_id, topic, partition);
```

### event_dlq

Dead-letter queue for unprocessable events.

```sql
CREATE TABLE event_dlq (
    id UUID PRIMARY KEY,
    topic VARCHAR(255),
    original_offset VARCHAR(255),
    consumer_group_id VARCHAR(255),
    payload JSONB,                 -- Failed event
    error_reason TEXT,             -- Why it failed
    attempt_count INTEGER,
    moved_to_dlq_at TIMESTAMP,
    resolved BOOLEAN DEFAULT false,
    resolution_notes TEXT          -- Manual fix notes
);

CREATE INDEX idx_dlq_resolved ON event_dlq(resolved);
```

## Configuration

### Environment Variables

```bash
# Broker selection
KAFKA_ENABLED=true|false
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_COMPRESSION_TYPE=snappy   # snappy | gzip | lz4 | zstd

REDIS_STREAMS_ENABLED=true|false
REDIS_URL=redis://localhost:6379/0

# Relay configuration
OUTBOX_RELAY_ENABLED=true
OUTBOX_RELAY_BROKER=kafka|redis|auto   # auto = detect from env
OUTBOX_RELAY_POLL_INTERVAL_SECONDS=2
OUTBOX_RELAY_BATCH_SIZE=100

# Consumer groups
ANALYTICS_CONSUMER_GROUP=analytics-processor
WEBHOOK_CONSUMER_GROUP=webhook-dispatcher
```

### Schema Registration (at startup)

```python
# app/main.py
from app.infra.event_streaming.schemas import get_schema_registry, build_standard_schemas

async def lifespan(app: FastAPI):
    # Register standard schemas
    registry = get_schema_registry()
    for topic, schema in build_standard_schemas().items():
        registry.register(topic, schema)
    
    # Start outbox relay
    relay = build_kafka_relay(...)
    asyncio.create_task(relay.run_forever())
    
    yield
    
    # Cleanup
    await relay.broker.close()
```

## Testing

### Unit Tests

```python
# tests/unit/test_event_schemas.py
def test_schema_backward_compat():
    v1 = EventSchema(name="LoginEvent", version=1, fields={"user_id": "string"})
    v2 = EventSchema(name="LoginEvent", version=2,
                     fields={"user_id": "string", "mfa": "boolean"},
                     compatibility="BACKWARD")
    
    registry.register("auth.events", v1)
    registry.register("auth.events", v2)  # Should succeed
    
    # V1 data still valid
    assert registry.validate_event("auth.events", {"user_id": "123"})
```

### Integration Tests

```bash
# Requires Kafka running
docker compose -f infra/kafka-docker-compose.yml up -d

# Run tests
pytest tests/integration/test_event_streaming_kafka.py -v
```

### E2E Tests

```python
# tests/e2e/test_outbox_relay_e2e.py
async def test_outbox_to_kafka_flow():
    # 1. Write to outbox
    outbox.append(OutboxEntry(...))
    
    # 2. Run relay
    relay = build_kafka_relay(...)
    await relay.process_batch()
    
    # 3. Verify in Kafka
    consumer = ExactlyOnceConsumer(group_id="test")
    # ... consume and verify
```

## Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Publish latency | <10ms p99 | Kafka producer |
| Consumer lag | <100ms | Fresh data within 100ms |
| Throughput | 100K+ msgs/sec | 3-node cluster |
| Availability | 99.9% | 2x replication |
| Message size | <1MB typical | Recommend <100KB |
| Batch size | 100 messages | Relay batch_size tuning |

## Troubleshooting

### Consumer Lagging

```python
# Check lag
metrics = await consumer.get_metrics()
for m in metrics:
    if m.is_lagging(lag_threshold=1000):
        print(f"Lagging: {m.group_id} ({m.lag} msgs)")

# Solutions:
# 1. Scale consumers (partition_count = ideal consumer_count)
# 2. Optimize handler (reduce processing time)
# 3. Increase batch size
# 4. Check broker health (CPU, disk, network)
```

### DLQ Growing

```python
# Check DLQ
dlq_entries = db.query(EventDeadLetterQueue).filter(
    EventDeadLetterQueue.resolved == False
).limit(10)

for entry in dlq_entries:
    print(f"Topic: {entry.topic}, Error: {entry.error_reason}")
    # Fix root cause:
    # - Update schema if incompatible
    # - Fix downstream service
    # - Replay if transient
```

### Connection Failures

```python
# Kafka broker down
# → Messages accumulate in outbox
# → Relay retries with exponential backoff
# → No message loss (outbox is source of truth)

# Redis connection lost
# → Fallback to in-memory relay
# → Messages queued, published on reconnect

# Network partition
# → Use circuit breaker (Faz 3.2)
# → Fail-fast, prevent cascading failures
```

## References

- [Outbox Pattern](https://microservices.io/patterns/data/transactional-outbox.html)
- [Kafka Documentation](https://kafka.apache.org/)
- [Avro Schema Evolution](https://avro.apache.org/docs/current/spec.html#schema_evolution)
- [Exactly-Once Semantics](https://kafka.apache.org/documentation/#semantics)
- [Database Serialization](https://en.wikipedia.org/wiki/Snapshot_isolation)
