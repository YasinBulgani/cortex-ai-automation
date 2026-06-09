# Event Streaming Deployment Guide (Faz 3.5)

**Last Updated:** 2026-06-09  
**Version:** 1.0  
**Environments:** Development (Redis Streams), Staging (Kafka 3-node), Production (Kafka HA)

---

## Quick Start

### Development (Local, Redis)

```bash
# 1. Start infrastructure (already in docker-compose.yml)
docker compose up -d postgres redis

# 2. Run migrations
alembic upgrade head

# 3. Start backend with outbox relay
python -m uvicorn app.main:app --reload

# Relay runs in-memory (no separate process needed)
```

**Config (.env):**
```bash
KAFKA_ENABLED=false
REDIS_STREAMS_ENABLED=true
OUTBOX_RELAY_ENABLED=true
```

---

### Staging (Kafka Cluster)

```bash
# 1. Start Kafka cluster
docker compose -f infra/kafka-docker-compose.yml up -d

# 2. Start backend
docker compose up -d backend

# 3. Start outbox relay (separate container)
docker compose -f docker-compose.yml up -d outbox-relay

# 4. View Kafka UI
# http://localhost:8888
```

**Config (environment variables):**
```bash
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka-broker-1:9092,kafka-broker-2:9092,kafka-broker-3:9092
OUTBOX_RELAY_ENABLED=true
OUTBOX_RELAY_BROKER=kafka
OUTBOX_RELAY_POLL_INTERVAL_SECONDS=2
OUTBOX_RELAY_BATCH_SIZE=100
```

**docker-compose.yml additions:**
```yaml
services:
  outbox-relay:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: neurex_outbox_relay
    restart: unless-stopped
    command: python -m app.infra.event_streaming.outbox_relay_cli
    environment:
      DATABASE_URL: postgresql+psycopg2://...
      KAFKA_ENABLED: "true"
      KAFKA_BOOTSTRAP_SERVERS: kafka-broker-1:9092,kafka-broker-2:9092,kafka-broker-3:9092
      OUTBOX_RELAY_ENABLED: "true"
      OUTBOX_RELAY_BROKER: kafka
      OUTBOX_RELAY_POLL_INTERVAL_SECONDS: "2"
      OUTBOX_RELAY_BATCH_SIZE: "100"
    depends_on:
      postgres:
        condition: service_healthy
      kafka-broker-1:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import app.infra.event_streaming; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### Production (HA Kafka)

#### Infrastructure Setup

**1. Kafka Cluster (AWS / On-Premises)**

Option A: AWS MSK (Managed Streaming for Kafka)
```bash
# Terraform / CloudFormation
resource "aws_msk_cluster" "neurex" {
  cluster_name           = "neurex-events"
  kafka_version          = "3.5.0"
  number_of_broker_nodes = 3

  broker_node_group_info {
    instance_type   = "kafka.m5.large"
    client_subnets  = var.private_subnets
    security_groups = [aws_security_group.kafka.id]
    storage_info {
      ebs_storage_info {
        volume_size = 500  # GB
      }
    }
  }

  tags = {
    Environment = "production"
  }
}
```

Option B: Self-Hosted (Kubernetes)
```yaml
# Use Strimzi operator or Confluent Cloud
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: neurex
spec:
  kafka:
    version: 3.5.0
    replicas: 3
    resources:
      requests:
        memory: 2Gi
        cpu: 1000m
      limits:
        memory: 4Gi
        cpu: 2000m
    storage:
      type: persistent-claim
      size: 500Gi
    config:
      default.replication.factor: 2
      min.insync.replicas: 2
      log.retention.hours: 168  # 7 days
      log.compression.type: snappy
  zookeeper:
    replicas: 3
    resources:
      requests:
        memory: 1Gi
        cpu: 500m
      limits:
        memory: 2Gi
        cpu: 1000m
    storage:
      type: persistent-claim
      size: 100Gi
```

**2. Network Setup**

```bash
# Security groups / Firewall
- Kafka brokers: 9092 (internal), 9093 (external, TLS)
- Zookeeper: 2181 (internal only)
- Schema Registry: 8081 (internal)
- Kafka UI: 8080 (internal VPN/bastion)
- Backend: access via private network
```

**3. Monitoring**

```bash
# Install Prometheus + Kafka JMX exporter
# Metrics to track:
# - kafka.network.requestmetrics.requests_total
# - kafka.server.replicamanager.under_replicated_partitions
# - kafka.network.socketserver.accepted_connections_total
# - kafka.consumer.fetch_latency_avg
```

#### Kubernetes Deployment

**Helm Chart Values (neurex-events):**
```yaml
# values.yaml
replicaCount: 3

image:
  repository: neurex-backend
  tag: "3.5.0"
  pullPolicy: IfNotPresent

env:
  KAFKA_ENABLED: "true"
  KAFKA_BOOTSTRAP_SERVERS: "kafka-cluster:9092"
  OUTBOX_RELAY_ENABLED: "true"
  OUTBOX_RELAY_BROKER: "kafka"
  OUTBOX_RELAY_POLL_INTERVAL_SECONDS: "2"
  OUTBOX_RELAY_BATCH_SIZE: "100"

resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "1Gi"
    cpu: "500m"

affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values:
                  - outbox-relay
          topologyKey: kubernetes.io/hostname
```

**Service Deployment:**
```bash
# Deploy backend + outbox relay
helm install neurex-backend ./charts/backend \
  -f values-production.yaml \
  --namespace neurex --create-namespace

# Scale outbox relays
kubectl scale deployment outbox-relay --replicas=3 -n neurex
```

---

## Migration: Redis → Kafka

### Phase 1: Validation (Week 1)

**Goal:** Kafka runs in parallel, validates correctness

```bash
# 1. Deploy Kafka cluster
docker compose -f infra/kafka-docker-compose.yml up -d

# 2. Enable dual-write in outbox relay
OUTBOX_RELAY_BROKER=dual-write  # Publish to both Redis + Kafka

# 3. Monitor Kafka metrics
# - Consumer lag < 100ms
# - 0 errors in producer
# - All downstream systems healthy
```

### Phase 2: Switchover (Week 2)

```bash
# 1. Switch relay to Kafka-primary
OUTBOX_RELAY_BROKER=kafka

# 2. Keep Redis as fallback
# Consumers read from Kafka first, Redis if unavailable

# 3. Monitor:
# - All topics have events flowing
# - No lag increase
# - No DLQ growth
```

### Phase 3: Cleanup (Week 3)

```bash
# 1. Retire Redis Streams
# - Keep Redis for cache/rate-limiting
# - Delete XREAD consumer groups

# 2. Archive Redis Streams data (optional)
# - Export to S3/backup
# - for compliance/audit trail

# 3. Update documentation
```

---

## Topic Configuration

### Create Topics via Kafka UI

**http://localhost:8888** → "Topics" → "Create Topic"

Or via CLI:

```bash
docker exec neurex_kafka_1 kafka-topics \
  --create \
  --bootstrap-server localhost:9092 \
  --topic auth.events \
  --partitions 3 \
  --replication-factor 2 \
  --config retention.ms=604800000 \
  --config compression.type=snappy
```

### Topic Topology

| Topic | Partitions | Replication | Retention | Min ISR |
|-------|-----------|-------------|-----------|---------|
| auth.events | 3 | 2 | 7d | 2 |
| test_management.events | 3 | 2 | 14d | 2 |
| execution.events | 3 | 2 | 30d | 2 |
| defect.events | 3 | 2 | 30d | 2 |
| audit.events | 5 | 3 | 90d | 2 |
| *.dlq | 1 | 2 | 30d | 1 |

---

## Monitoring & Alerts

### Metrics Dashboard

**Prometheus Targets:**
```yaml
- job_name: kafka
  static_configs:
    - targets: ['kafka-exporter:9308']
    
- job_name: kafka-jmx
  static_configs:
    - targets: ['kafka-jmx:9999']
```

**Key Alerts:**

```yaml
# Consumer lag (PromQL)
- alert: KafkaConsumerLag
  expr: kafka_consumer_lag > 10000
  for: 5m
  annotations:
    summary: "Consumer {{ $labels.group }} lagging (lag={{ $value }})"

# Broker down
- alert: KafkaBrokerDown
  expr: kafka_brokers == 0
  for: 1m
  annotations:
    summary: "All Kafka brokers down!"

# Under-replicated
- alert: KafkaUnderReplicated
  expr: kafka_under_replicated_partitions > 0
  for: 10m
  annotations:
    summary: "{{ $value }} partitions under-replicated"
```

### Grafana Dashboards

- **Kafka Cluster Health** (partition/replica status)
- **Consumer Group Lag** (lag per group/topic)
- **Broker Performance** (throughput, latency)
- **Application Events** (custom: published/consumed/dlq)

### Logs

```bash
# Follow relay logs
docker logs -f neurex_outbox_relay

# Search for errors
docker logs neurex_outbox_relay | grep ERROR

# Kafka broker logs
docker exec neurex_kafka_1 tail -f /var/log/kafka/server.log
```

---

## Troubleshooting

### Issue: High Consumer Lag

```bash
# 1. Check broker health
kafka-broker-api-versions --bootstrap-server localhost:9092

# 2. Check partition distribution
kafka-topics --bootstrap-server localhost:9092 \
  --topic auth.events --describe

# 3. Check consumer group status
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group analytics-processor --describe

# 4. Scale consumer
kubectl scale deployment consumer-analytics --replicas=5 -n neurex

# 5. Monitor new lag
watch -n 2 'kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group analytics-processor --describe'
```

### Issue: Partition Rebalancing Loop

```bash
# 1. Check for zombie instances
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group webhook-dispatcher --members

# 2. Kill stuck processes
pkill -f "consumer_group_id=webhook-dispatcher"

# 3. Wait for rebalance (30-60s)
# 4. Restart service gracefully
```

### Issue: Message Duplication

```bash
# Root cause: Consumer not committing offsets before crash

# Check offset commit frequency
# In config: enable_auto_commit=False (manual)
# Ensure commit happens AFTER handler succeeds

# Fix: Add idempotency at application level
# Store processed event_id in Redis/DB
# Skip if already processed
```

### Issue: DLQ Growing

```bash
# 1. Check DLQ entries
SELECT * FROM event_dlq 
WHERE resolved = false 
ORDER BY moved_to_dlq_at DESC 
LIMIT 10;

# 2. Analyze error
# - Schema mismatch? → Update schema
# - Downstream error? → Fix service
# - Transient? → Retry

# 3. Replay from DLQ
INSERT INTO outbox (event_type, aggregate_id, payload, status)
SELECT ...
FROM event_dlq
WHERE id = '...' AND resolved = false;

UPDATE event_dlq SET resolved = true WHERE id = '...';
```

---

## Performance Tuning

### Producer Settings

```python
# backend/app/config.py
KAFKA_PRODUCER_BATCH_SIZE = 16384  # bytes
KAFKA_PRODUCER_LINGER_MS = 10      # delay for batching
KAFKA_PRODUCER_COMPRESSION = "snappy"
```

### Consumer Settings

```python
# Outbox relay
OUTBOX_RELAY_BATCH_SIZE = 100       # messages per fetch
OUTBOX_RELAY_POLL_INTERVAL = 2.0    # seconds
OUTBOX_RELAY_MAX_CONCURRENT = 10    # parallel publishes
```

### Broker Settings

```yaml
# docker-compose.yml
KAFKA_NUM_NETWORK_THREADS: 8
KAFKA_NUM_IO_THREADS: 8
KAFKA_SOCKET_SEND_BUFFER_BYTES: 102400
KAFKA_SOCKET_RECEIVE_BUFFER_BYTES: 102400
KAFKA_LOG_FLUSH_INTERVAL_MESSAGES: 10000
KAFKA_LOG_FLUSH_INTERVAL_MS: 1000
```

---

## Backup & Recovery

### Kafka Data Backup

```bash
# 1. Export to Avro (confluent-cli)
confluent kafka topic export \
  --topic auth.events \
  --output-format avro \
  --output-file auth.events.avro

# 2. Upload to S3
aws s3 cp auth.events.avro \
  s3://neurex-backups/kafka/$(date +%Y-%m-%d)/
```

### Recovery Procedure

```bash
# 1. Create new topic
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic auth.events.restored \
  --partitions 3 --replication-factor 2

# 2. Import data
confluent kafka topic import \
  --topic auth.events.restored \
  --input-format avro \
  --input-file auth.events.avro

# 3. Switch consumers
KAFKA_BOOTSTRAP_SERVERS=kafka-restored:9092
```

---

## Cost Optimization (AWS MSK)

| Component | Cost | Notes |
|-----------|------|-------|
| **MSK Cluster** | ~$300/month | 3 brokers (m5.large) |
| **Data Transfer** | ~$50/month | 100GB/month egress |
| **CloudWatch** | ~$20/month | Monitoring + logging |
| **S3 Backups** | ~$10/month | 1TB storage |
| **Total** | ~$380/month | For 1M+ events/day |

**Optimization:**
- Use smaller instance type (m5.large → t3.medium) if <1M events/day
- Enable auto-scaling for storage
- Use S3 Intelligent-Tiering for backups

---

## Production Checklist

- [ ] Kafka cluster deployed (3+ brokers)
- [ ] Zookeeper ensemble (3+ nodes)
- [ ] All topics created with correct partitions/replication
- [ ] Monitoring + alerting configured
- [ ] Outbox relay scaled (3+ replicas)
- [ ] Consumer groups tested
- [ ] DLQ monitoring enabled
- [ ] Backup strategy in place
- [ ] Runbook documented
- [ ] Team trained on operations
- [ ] Load tested (100K+ msgs/sec)
- [ ] Chaos testing (broker failures)
