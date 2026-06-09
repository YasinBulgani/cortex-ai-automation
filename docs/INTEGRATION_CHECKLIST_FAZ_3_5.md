# Faz 3.5 Event Streaming — Integration Checklist

**Target:** Production-ready event streaming with Kafka/Redis foundation  
**Scope:** Event broker, schema registry, exactly-once consumers, outbox relay  
**Timeline:** 1-2 weeks for full integration

---

## Pre-Integration Setup

- [ ] Review architecture diagram (FAZ_3_5_IMPLEMENTATION_SUMMARY.md)
- [ ] Read deployment guide (EVENT_STREAMING_DEPLOYMENT.md)
- [ ] Install dependencies: `aiokafka`, `redis`
- [ ] Ensure database connectivity (migration target)
- [ ] Staging environment available

---

## Phase 1: Database & Infrastructure (Day 1)

### Database Migration
- [ ] Review migration file: `alembic/versions/20260609_event_streaming_tables.py`
- [ ] Test locally: `alembic upgrade head`
- [ ] Verify tables created:
  ```sql
  SELECT * FROM information_schema.tables 
  WHERE table_name LIKE 'stream_%' OR table_name LIKE 'consumer_%' OR table_name = 'event_dlq';
  ```
- [ ] Verify indices created: `SELECT * FROM pg_indexes WHERE tablename LIKE 'stream_%';`

### Kafka Cluster (Staging/Prod only)
- [ ] Start Kafka cluster: `docker compose -f infra/kafka-docker-compose.yml up -d`
- [ ] Verify health: `docker compose -f infra/kafka-docker-compose.yml logs kafka-broker-1 | grep started`
- [ ] Access Kafka UI: http://localhost:8888
- [ ] Verify all 3 brokers healthy
- [ ] Test topic creation (via UI)

### Development (Redis only)
- [ ] Verify Redis running: `docker compose logs redis`
- [ ] Test connectivity: `redis-cli ping`

---

## Phase 2: Core Modules (Day 1-2)

### Module Review & Testing
- [ ] Review `broker.py`:
  - [ ] `KafkaBroker` class (publish, create_topic)
  - [ ] `RedisBroker` class (publish, close)
  - [ ] `build_broker` factory function
  
- [ ] Review `consumer.py`:
  - [ ] `ConsumerMessage` dataclass
  - [ ] `ExactlyOnceConsumer` (exactly-once semantics)
  - [ ] `RedisStreamConsumer` (consumer groups)
  
- [ ] Review `schemas.py`:
  - [ ] `EventSchema` (definition)
  - [ ] `SchemaRegistry` (versioning, validation)
  - [ ] Standard schemas (auth, test_management, execution, defect, audit)
  
- [ ] Review `models.py`:
  - [ ] SQLAlchemy models (stream_events, dlq, metrics)
  - [ ] Database relationships
  
- [ ] Review `outbox_relay_kafka.py`:
  - [ ] `OutboxRelayKafka` class (exactly-once relay)
  - [ ] Topic mapping logic
  - [ ] Atomic fetch + mark pattern

### Unit Tests
- [ ] Run schema validation tests:
  ```bash
  pytest tests/unit/test_event_schemas.py -v
  ```
  - [ ] Backward compatibility checks
  - [ ] Schema validation
  - [ ] Avro/Protobuf exports

---

## Phase 3: Integration Tests (Day 2-3)

### Kafka Integration (requires Docker)
- [ ] Start Kafka: `docker compose -f infra/kafka-docker-compose.yml up -d`
- [ ] Run integration tests:
  ```bash
  pytest tests/integration/test_event_streaming_kafka.py::TestKafkaBroker -v
  ```
  - [ ] Test single message publish
  - [ ] Test partition key ordering
  - [ ] Test idempotent producer
  - [ ] Test topic creation

- [ ] Consumer tests:
  ```bash
  pytest tests/integration/test_event_streaming_kafka.py::TestExactlyOnceConsumer -v
  ```
  - [ ] Test subscribe
  - [ ] Test consume
  - [ ] Test metrics

- [ ] Outbox relay tests:
  ```bash
  pytest tests/integration/test_event_streaming_kafka.py::TestOutboxRelayKafka -v
  ```
  - [ ] Test entry publishing
  - [ ] Test topic mapping

### Redis Integration (requires Redis)
- [ ] Verify Redis running
- [ ] Test RedisBroker:
  ```python
  async def test_redis_broker():
      broker = RedisBroker("redis://localhost:6379/0")
      msg_id = await broker.publish("test", {"data": "test"})
      assert msg_id is not None
      await broker.close()
  ```

---

## Phase 4: Application Integration (Day 3-4)

### Configuration Setup
- [ ] Create/update `.env`:
  ```bash
  # Development
  KAFKA_ENABLED=false
  REDIS_STREAMS_ENABLED=true
  OUTBOX_RELAY_ENABLED=true
  
  # Staging/Production
  KAFKA_ENABLED=true
  KAFKA_BOOTSTRAP_SERVERS=localhost:9092
  OUTBOX_RELAY_BROKER=kafka
  ```

- [ ] Update `app/config.py`:
  ```python
  # Add to Settings class
  kafka_enabled: bool = False
  kafka_bootstrap_servers: str = "localhost:9092"
  outbox_relay_broker: str = "auto"
  outbox_relay_poll_interval: float = 2.0
  outbox_relay_batch_size: int = 100
  ```

### Application Startup (app/main.py)
- [ ] Register standard schemas on startup:
  ```python
  @app.lifespan
  async def lifespan(app: FastAPI):
      # Register schemas
      registry = get_schema_registry()
      for topic, schema in build_standard_schemas().items():
          registry.register(topic, schema)
      
      # Start relay
      relay = build_kafka_relay(...) if settings.kafka_enabled else None
      if relay:
          relay_task = asyncio.create_task(relay.run_forever())
      
      yield
      
      # Cleanup
      if relay:
          relay_task.cancel()
          await relay.broker.close()
  ```

- [ ] Test startup: `python -m uvicorn app.main:app --reload`
- [ ] Verify no startup errors
- [ ] Verify schema registration in logs

### Outbox Table Integration
- [ ] Verify `outbox` table created (from Faz 3.0)
- [ ] Verify outbox entries structure:
  ```sql
  SELECT * FROM outbox LIMIT 1;
  ```
- [ ] Test outbox write in existing domain service:
  ```python
  # In any domain service
  outbox_repo.append(OutboxEntry(
      event_type="auth.user_created",
      aggregate_id=user.id,
      payload={"email": user.email}
  ))
  ```

---

## Phase 5: Relay & Consumer Startup (Day 4-5)

### Outbox Relay Service
- [ ] Start relay (in-process for dev):
  ```bash
  # Already running in app.main lifespan
  python -m uvicorn app.main:app --reload
  ```
  
- [ ] Or as standalone CLI (for Docker):
  ```bash
  python -m app.infra.event_streaming.outbox_relay_cli
  ```
  
- [ ] Verify relay logs:
  ```bash
  # Should see: "Outbox relay starting"
  # Should see: "Event published to Kafka" (or Redis)
  ```

- [ ] Monitor relay health:
  ```python
  # Health endpoint
  curl http://localhost:8000/health
  ```

### Create Standard Consumer
- [ ] Create analytics consumer service:
  ```python
  # app/services/analytics/consumer.py
  from app.infra.event_streaming import ExactlyOnceConsumer
  
  async def run_analytics_consumer():
      consumer = ExactlyOnceConsumer(
          group_id="analytics-processor",
          bootstrap_servers="kafka-broker-1:9092"
      )
      await consumer.subscribe(["auth.events", "test_management.events"])
      
      async def handler(msg):
          if msg.topic == "auth.events":
              analytics_db.record_login(msg.value)
      
      await consumer.consume(handler)
  
  if __name__ == "__main__":
      asyncio.run(run_analytics_consumer())
  ```

- [ ] Test consumer in Docker:
  ```bash
  # Option 1: In existing backend service
  # Option 2: Separate container (future)
  docker compose up -d analytics-consumer
  ```

---

## Phase 6: End-to-End Testing (Day 5)

### Manual Event Flow
- [ ] Trigger domain event (e.g., user creation):
  ```bash
  curl -X POST http://localhost:8000/api/v1/users \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"email": "test@example.com", "name": "Test User"}'
  ```

- [ ] Verify in database:
  ```sql
  -- Check outbox table
  SELECT * FROM outbox WHERE status = 'pending' LIMIT 5;
  
  -- Should see pending entry
  ```

- [ ] Wait 2-5 seconds (relay poll interval)

- [ ] Verify published to Kafka:
  ```sql
  -- Check stream_events table
  SELECT * FROM stream_events WHERE status = 'published' ORDER BY created_at DESC LIMIT 5;
  
  -- Should see published entry
  ```

- [ ] Or in Kafka UI:
  - [ ] Go to http://localhost:8888
  - [ ] Select cluster "neurex"
  - [ ] Topics → auth.events
  - [ ] Messages → should see new event

### Consumer Processing
- [ ] Verify consumer group offset committed:
  ```bash
  docker exec neurex_kafka_1 kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group analytics-processor \
    --describe
  
  # Should show: TOPIC, PARTITION, CURRENT-OFFSET, LOG-END-OFFSET, LAG, ...
  ```

- [ ] Verify downstream system updated:
  ```sql
  -- If analytics consumer, check analytics table
  SELECT * FROM analytics_events WHERE event_type = 'auth.user_created';
  ```

- [ ] Monitor lag:
  ```bash
  # Should be < 100ms (near 0 typically)
  docker exec neurex_kafka_1 kafka-consumer-groups \
    --bootstrap-server localhost:9092 \
    --group analytics-processor \
    --describe | grep LAG
  ```

---

## Phase 7: Performance & Monitoring (Day 5-6)

### Metrics Collection
- [ ] Check consumer metrics:
  ```python
  async def check_metrics():
      consumer = ExactlyOnceConsumer(group_id="analytics-processor")
      metrics = await consumer.get_metrics()
      for m in metrics:
          print(f"Topic: {m.topic}, Lag: {m.lag}, Rate: {m.processing_rate}")
  ```

- [ ] Monitor relay performance:
  ```python
  # In relay logs, should see:
  # "Processing 100 outbox entries"
  # "Event published to Kafka (topic=auth.events, msg_id=...)"
  ```

### Alerting Setup
- [ ] Configure Prometheus scrape targets (if monitoring stack):
  ```yaml
  - job_name: kafka_exporter
    static_configs:
      - targets: ['kafka-exporter:9308']
  ```

- [ ] Set up alerts:
  - [ ] Consumer lag > 10K messages
  - [ ] Relay error rate > 1%
  - [ ] Broker down
  - [ ] DLQ growing

### Kafka UI Verification
- [ ] http://localhost:8888 → Check:
  - [ ] All 3 brokers healthy
  - [ ] Topics auto-created with correct partitions
  - [ ] Messages flowing through topics
  - [ ] Consumer groups registered
  - [ ] No under-replicated partitions

---

## Phase 8: Docker & Production Setup (Day 6-7)

### Docker Compose Updates
- [ ] Update main `docker-compose.yml`:
  ```yaml
  services:
    outbox-relay:
      build:
        context: ./backend
      command: python -m app.infra.event_streaming.outbox_relay_cli
      environment:
        KAFKA_ENABLED: "true"
        KAFKA_BOOTSTRAP_SERVERS: kafka-broker-1:9092
      depends_on:
        - postgres
        - kafka-broker-1
  ```

- [ ] Update `docker-compose.yml` backend service:
  ```yaml
  backend:
    environment:
      KAFKA_ENABLED: "true"
      KAFKA_BOOTSTRAP_SERVERS: kafka-broker-1:9092
      OUTBOX_RELAY_ENABLED: "true"
  ```

- [ ] Test Docker build:
  ```bash
  docker compose build
  docker compose up -d
  ```

### Kubernetes (if applicable)
- [ ] Update Helm values: `kafka_enabled=true`
- [ ] Deploy: `helm install neurex ./charts`
- [ ] Verify pods running: `kubectl get pods -n neurex`
- [ ] Check logs: `kubectl logs -f deployment/outbox-relay -n neurex`

---

## Phase 9: Documentation & Training (Day 7)

### Documentation Review
- [ ] Read FAZ_3_5_EVENT_STREAMING.md (3000+ lines)
  - [ ] Topic configuration section
  - [ ] Schema evolution examples
  - [ ] Usage patterns
  - [ ] Troubleshooting

- [ ] Read EVENT_STREAMING_DEPLOYMENT.md (2000+ lines)
  - [ ] Staging setup
  - [ ] Production setup
  - [ ] Migration path
  - [ ] Monitoring

- [ ] Review code documentation:
  - [ ] `backend/app/infra/event_streaming/README.md`
  - [ ] Inline code comments

### Team Training
- [ ] Architecture overview (30 min)
  - [ ] Event flow diagram
  - [ ] Broker selection
  - [ ] Consumer groups

- [ ] Developer guide (1 hour)
  - [ ] Publishing events (via outbox)
  - [ ] Creating consumers
  - [ ] Schema validation
  - [ ] Testing

- [ ] Operations guide (1 hour)
  - [ ] Monitoring
  - [ ] Alerts
  - [ ] Troubleshooting
  - [ ] Scaling

- [ ] Create team runbooks:
  - [ ] Consumer lag incident response
  - [ ] DLQ processing
  - [ ] Broker failover
  - [ ] Data recovery

---

## Phase 10: Validation & Sign-Off (Day 7+)

### Functional Testing
- [ ] All 15+ integration tests passing:
  ```bash
  pytest tests/integration/test_event_streaming_kafka.py -v
  ```

- [ ] End-to-end scenarios working:
  - [ ] User creation event → published → consumed → analytics updated
  - [ ] Test execution event → published → consumed → dashboard updated
  - [ ] Defect event → published → webhook sent

- [ ] Error handling:
  - [ ] Failed event → DLQ
  - [ ] Consumer crash → rebalance
  - [ ] Broker down → failover

### Performance Validation
- [ ] Load test (100K msgs/sec):
  ```bash
  pytest tests/load/test_event_streaming_load.py -v
  ```
  - [ ] Latency p99 < 10ms
  - [ ] Consumer lag < 100ms
  - [ ] 0 message loss

- [ ] Chaos testing (broker failure):
  ```bash
  # Kill broker
  docker kill neurex_kafka_2
  
  # Verify:
  # - Events still published
  # - Consumer rebalances
  # - No data loss
  
  # Restart
  docker start neurex_kafka_2
  ```

### Sign-Off Criteria
- [ ] All tests passing (unit + integration)
- [ ] Performance targets met
- [ ] Monitoring + alerting configured
- [ ] Documentation complete
- [ ] Team trained
- [ ] No critical issues open
- [ ] Code reviewed + approved

**Ready for production deployment.**

---

## Post-Integration Checklist

### Day 1-2 (Production)
- [ ] Monitor metrics closely
- [ ] Verify no increased error rate
- [ ] Check DLQ is empty
- [ ] Confirm all consumers subscribed
- [ ] Verify no cascading failures

### Day 3-7 (Production Stabilization)
- [ ] Collect performance metrics
- [ ] Document any issues encountered
- [ ] Fine-tune batch sizes/intervals
- [ ] Optimize consumer groups
- [ ] Plan next improvements

### Ongoing
- [ ] Weekly metrics review
- [ ] Monthly performance analysis
- [ ] Track migration to Faz 3.6 (event sourcing)
- [ ] Maintain documentation

---

## Support Resources

- **Architecture:** FAZ_3_5_IMPLEMENTATION_SUMMARY.md
- **Deployment:** EVENT_STREAMING_DEPLOYMENT.md
- **API Reference:** backend/app/infra/event_streaming/README.md
- **Code:** backend/app/infra/event_streaming/*.py
- **Tests:** backend/tests/integration/test_event_streaming_kafka.py
- **Docker:** infra/kafka-docker-compose.yml, docker-compose.yml

---

**Estimated Total Time: 5-7 days for full integration**

Good luck! 🚀
