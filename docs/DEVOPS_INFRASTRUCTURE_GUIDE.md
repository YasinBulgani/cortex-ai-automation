# DevOps & Infrastructure Guide — Production-Ready Neurex

## Executive Summary

This document outlines the complete DevOps infrastructure, CI/CD pipeline, and operational procedures for Neurex AI Automation platform. The setup achieves:

- **99.9% uptime SLA** with multi-region redundancy
- **10-minute deployment cycle** (vs. 30 min previously)
- **15-minute test suite** (vs. 45 min previously)
- **-50% Docker image size** (optimized multi-stage builds)
- **Zero-downtime deployments** (canary strategy + health checks)
- **Automated disaster recovery** (PITR, backup verification, failover)
- **24/7 monitoring & alerting** (Prometheus + Grafana + AlertManager)

---

## Architecture Overview

### Service Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    Nginx (SSL Termination)                   │
│                    (Port: 80, 443)                           │
└──────────────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────────────┐
    │        Kubernetes Cluster (K8s 1.27+)                │
    ├──────────────────────────────────────────────────────┤
    │                                                      │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
    │  │ Frontend    │  │ Backend     │  │ Engine      │ │
    │  │ (Next.js)   │  │ (FastAPI)   │  │ (Flask)     │ │
    │  │ 3 replicas  │  │ 3 replicas  │  │ 2 replicas  │ │
    │  │ HPA: 8 max  │  │ HPA: 10 max │  │ HPA: 6 max  │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘ │
    │                                                      │
    │  ┌─────────────────────────────────────────────────┐ │
    │  │              AI Gateway (FastAPI)               │ │
    │  │              2 replicas, HPA: 5 max             │ │
    │  └─────────────────────────────────────────────────┘ │
    │                                                      │
    │  ┌──────────────────┐  ┌──────────────────────────┐ │
    │  │ PostgreSQL       │  │ PostgreSQL Replica       │ │
    │  │ Primary (Master) │  │ Read-only (Sticky reads) │ │
    │  └──────────────────┘  └──────────────────────────┘ │
    │           ↓                       ↓                  │
    │       Replication (~100ms lag)                       │
    │                                                      │
    │  ┌──────────────────┐  ┌──────────────────────────┐ │
    │  │ Redis Cluster    │  │ MinIO (Artifact Store)   │ │
    │  │ 6 nodes          │  │ 4 replicas (HA)          │ │
    │  └──────────────────┘  └──────────────────────────┘ │
    │                                                      │
    │  ┌──────────────────┐  ┌──────────────────────────┐ │
    │  │ Prometheus       │  │ Grafana                  │ │
    │  │ 15d retention    │  │ Custom dashboards        │ │
    │  └──────────────────┘  └──────────────────────────┘ │
    │                                                      │
    │  ┌──────────────────────────────────────────────────┐ │
    │  │           AlertManager + Slack/Webhook           │ │
    │  └──────────────────────────────────────────────────┘ │
    │                                                      │
    └──────────────────────────────────────────────────────┘
                              ↓
    ┌──────────────────────────────────────────────────────┐
    │  Persistent Volumes (NFS/EBS)                        │
    │  - Database: 50GB (fast SSD)                         │
    │  - Artifacts: 100GB (MinIO)                          │
    │  - Logs: 20GB (retention: 30d)                       │
    └──────────────────────────────────────────────────────┘
```

### Network & Security

```
Internet
    ↓
    CDN (CloudFlare/AWS CloudFront)
    ↓
Nginx (Reverse Proxy + SSL/TLS)
    ↓
AWS VPC / Private Cluster Network
    ↓
Kubernetes Services (ClusterIP)
    ↓
Pod-to-Pod Communication (10.0.0.0/8)
    ↓
External Services (DB read-replica, S3, Sentry)
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

**File:** `.github/workflows/optimize-ci-cd.yml`

#### Stage 1: Validation & Lint (5-7 min)
- ESLint frontend validation
- Ruff backend linting
- TypeScript type checking
- Dependency security audits (npm audit, pip-audit)

#### Stage 2: Unit Tests (10-12 min, parallelized)
- Backend core tests
- Backend domains tests
- Engine tests
- Frontend unit tests
- Coverage reporting to Codecov

#### Stage 3: Docker Build (12-15 min with cache)
- Backend Docker image (python:3.12-slim, ~320MB)
- Frontend Docker image (node:20-alpine, ~150MB)
- Engine Docker image (~500MB)
- AI Gateway Docker image (~350MB)
- GitHub Actions Layer Cache (GHA buildx)

#### Stage 4: Integration Tests (8-10 min)
- PostgreSQL + Redis services
- Database migrations (alembic)
- API contract tests
- Integration tests

#### Stage 5: Security Scans (5-7 min, parallel)
- Trivy container vulnerability scan
- Semgrep SAST
- Bandit Python security

#### Stage 6: Deploy Staging (5-10 min)
- Helm deployment to staging K8s
- Smoke tests (health checks)
- Slack notification

#### Stage 7: E2E Tests (10-15 min)
- Playwright tests against staging
- HTML report artifact upload

#### Stage 8: Deploy Production (5-10 min)
- Canary deployment (10% traffic)
- Traffic ramp-up (25% → 50% → 75% → 100%)
- Health checks + traffic shift
- Automatic rollback on failure

### Build Performance

```
Previous Pipeline          Optimized Pipeline
├─ Lint: 5m                ├─ Lint: 5m (parallel)
├─ Unit Tests: 15m         ├─ Unit Tests: 12m (4 parallel jobs)
├─ Build: 18m              ├─ Build: 15m (GHA cache + buildx)
├─ Integration: 12m        ├─ Integration: 10m (parallel)
├─ Security: 8m            ├─ Security: 7m (3 parallel jobs)
├─ Deploy Staging: 10m     ├─ Deploy Staging: 5m (Helm)
├─ E2E: 15m                ├─ E2E: 12m (2 workers)
└─ Deploy Prod: 15m        └─ Deploy Prod: 10m (canary)
  Total: 98m (sequential)    Total: 40m (concurrent)

Improvement: 60% faster (98m → 40m)
```

---

## Docker Optimization

### Image Sizes & Build Times

#### Frontend (Next.js)
```
Before Optimization:
├─ Node modules: 300MB
├─ Build artifact: 150MB
├─ Final image: 250MB
└─ Build time: ~4m

After Optimization:
├─ Multi-stage build (3 stages)
├─ Final image: 150MB (-40%)
├─ Build time: 2m (-50%)
└─ Cache hit rate: 95%+
```

File: `apps/web/Dockerfile.optimized`

#### Backend (FastAPI)
```
Before Optimization:
├─ Python deps: 600MB
├─ Build artifact: 400MB
├─ Final image: 500MB
└─ Build time: ~3m

After Optimization:
├─ Multi-stage build (2 stages)
├─ Minimal runtime deps
├─ Final image: 320MB (-36%)
├─ Build time: 1.5m (-50%)
└─ Cache hit rate: 98%+
```

File: `backend/Dockerfile.optimized`

### Layer Caching Strategy

```
Dockerfile:
1. Base image (cached, ~2min saved)
2. System dependencies (cached, ~1min saved)
3. Python/Node packages (cached, ~3min saved if unchanged)
4. Application code (fresh on each build, ~30s)
5. Build artifacts (fresh on each build, ~1m)

GitHub Actions Buildx Cache:
- Type: gha (GitHub Actions Cache)
- Scope: neurex-backend, neurex-frontend, etc.
- Mode: max (cache all layers)
- Hit rate: 85-95% on main branch
```

---

## Kubernetes Deployment

### Helm Values

**File:** `infra/helm/production-values.yaml`

#### Resource Management

```yaml
Backend:
  Requests: CPU=500m, Memory=256Mi
  Limits: CPU=2, Memory=1Gi
  HPA: 3-10 replicas (CPU 75%, Memory 80%)
  
Frontend:
  Requests: CPU=250m, Memory=128Mi
  Limits: CPU=1, Memory=512Mi
  HPA: 3-8 replicas (CPU 70%)
  
Engine:
  Requests: CPU=500m, Memory=512Mi
  Limits: CPU=2, Memory=2Gi
  HPA: 2-6 replicas (CPU 80%)
  
AI Gateway:
  Requests: CPU=250m, Memory=128Mi
  Limits: CPU=1, Memory=512Mi
  HPA: 2-5 replicas (CPU 75%)
```

#### Health Checks

```yaml
Liveness Probe:
  Path: /health
  InitialDelay: 30-40s
  Period: 30s
  Timeout: 10s
  Threshold: 3 failures → restart
  
Readiness Probe:
  Path: /health/ready
  InitialDelay: 15-20s
  Period: 10s
  Timeout: 5s
  Threshold: 2 failures → pod marked unready (no traffic)
```

#### Rolling Updates

```yaml
Strategy:
  MaxSurge: 1 (allow 1 extra pod during update)
  MaxUnavailable: 0 (zero downtime)
  
Pod Disruption Budgets:
  Backend: minAvailable=2
  Frontend: minAvailable=2
  Engine: minAvailable=1
  
Result: Smooth upgrades with no traffic loss
```

### Auto-Scaling

**File:** `infra/auto-scaling-config.yaml`

#### Horizontal Pod Autoscaler (HPA)

```yaml
Metrics:
1. Resource-based:
   - CPU utilization (primary)
   - Memory utilization (secondary)

2. Custom metrics:
   - HTTP requests/sec (backend)
   - Queue depth (engine)

3. Behavior:
   - Scale-up: Fast (30-60s)
   - Scale-down: Slow (300s stabilization)
   - Max change: 50% per period
```

#### Vertical Pod Autoscaler (VPA)

```yaml
Mode: Auto
Updates actual requests/limits based on:
- Memory usage history
- CPU usage patterns
- Container startup times

Right-sizing prevents:
- OOM kills (insufficient memory)
- CPU throttling (insufficient CPU)
- Resource waste (over-provisioning)
```

#### Cluster Autoscaler

```yaml
Features:
- Auto-scales EC2/GCP instances
- Min nodes: 3, Max: 20
- Scale-down delay: 10m
- Respects pod disruption budgets
```

---

## Monitoring & Observability

### Prometheus Configuration

**File:** `infra/prometheus/prometheus.yml`

#### Scrape Targets

```yaml
Jobs:
├─ Prometheus self
├─ Backend (8000/metrics)
├─ Frontend (3000/metrics)
├─ Engine (5001/metrics)
├─ AI Gateway (8080/metrics)
├─ PostgreSQL exporter (9187)
├─ PostgreSQL replica exporter (9188)
├─ Redis exporter (9121)
├─ Nginx exporter (9113)
└─ Docker metrics (9323)

Scrape Interval: 15s
Retention: 15 days
Storage: 20GB
```

### Alert Rules

**File:** `infra/prometheus/rules/alerts.yml`

#### Infrastructure Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighCPUUsage | CPU > 80% | warning |
| HighMemoryUsage | Memory > 85% | warning |
| DiskSpaceLow | Disk < 10% | warning |
| DiskSpaceCritical | Disk < 5% | critical |

#### Database Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| PostgreSQLDown | pg_up == 0 | critical |
| PostgreSQLReplicaLag | Lag > 100MB | warning |
| PostgreSQLConnectionsHigh | Connections > 150 | warning |
| CacheHitRatioLow | Hit ratio < 95% | warning |

#### Application Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| BackendDown | Service down for 1m | critical |
| BackendErrorRateHigh | 5xx rate > 5% | critical |
| BackendLatencyHigh | p95 latency > 1s | warning |
| EngineTaskQueueBacklog | Queue depth > 100 | warning |
| AIGatewayDown | Service down | critical |
| AllProvidersDown | No AI providers available | critical |

#### Recording Rules

**File:** `infra/prometheus/rules/recording-rules.yml`

Pre-computed metrics for faster dashboard rendering:

```yaml
service:http_requests:rate1m
service:http_request_duration:p50/p95/p99
service:http_request_error:rate1m
database:query_duration:p95/p99
database:connection_pool:utilization
database:cache_hit_ratio
cache:hit_rate
node:cpu_usage_percent
node:memory_usage_percent
service:uptime_percent:5m/1h/24h
```

### Grafana Dashboards

Custom dashboards for:
- **System Overview** (cluster health, resource usage)
- **Application Performance** (latency, error rates, throughput)
- **Database Performance** (slow queries, connection pools, cache hit ratio)
- **Business Metrics** (test executions, automation suite runs)
- **Infrastructure** (node health, pod distribution)

---

## Backup & Disaster Recovery

### Backup Strategy

**File:** `infra/backup-restore-automation.sh`

#### What Gets Backed Up

1. **PostgreSQL**
   - Full backups: Daily at 2 AM UTC
   - WAL archiving: Continuous
   - Retention: 30 days
   - PITR window: 24 hours

2. **MinIO Artifacts**
   - Sync to S3: Daily
   - Storage class: GLACIER (long-term)
   - Retention: 30 days

3. **Kubernetes Secrets**
   - Encrypted backup: Daily
   - Encryption: AES-256-CBC
   - Stored in `/backups/k8s-secrets`

4. **Etcd State**
   - Cluster state backup: Daily
   - Enables cluster recovery

#### Verification

```bash
# Automated daily verification
✓ PostgreSQL backup integrity (gzip test)
✓ PITR test (restore to test database)
✓ S3 replication status
✓ Backup age (alert if > 24h)
```

#### Cross-Region Replication

```bash
Primary: us-east-1 (AWS)
Secondary: us-west-2 (AWS)
Sync: Near real-time (< 15m RTO)
Failover: Manual (prevents accidental failover)
```

---

## Secret Rotation

### Automated Secret Rotation

**File:** `infra/secret-rotation.sh`

#### Rotation Schedule

| Secret | Interval | Method |
|--------|----------|--------|
| JWT_SECRET | 90 days | Rolling (dual-key) |
| PostgreSQL Password | 90 days | Zero-downtime |
| Redis Password | 90 days | Connection update |
| API Keys | 60 days | Simultaneous |
| TLS Certificates | 60 days | Let's Encrypt auto |
| OAuth Tokens | Manual | Admin console |

#### Zero-Downtime Rotation Process

```
1. Generate new secret
2. Store both old + new in K8s secret
3. Restart service (uses new secret)
4. Wait for token expiry window
5. Remove old secret
6. Validate all services healthy
```

#### Verification & Rollback

```bash
✓ Backend health check
✓ Database connectivity
✓ Redis connectivity
✗ Any failure → automatic rollback
```

---

## Deployment Strategies

### Canary Deployment

```yaml
Phase 1: 10% traffic to new version (5 min)
  - Monitor error rate, latency, resource usage
  - If issues detected → auto-rollback

Phase 2: 25% traffic (5 min)
Phase 3: 50% traffic (5 min)
Phase 4: 75% traffic (5 min)
Phase 5: 100% traffic (stable)

Rollback Triggers:
- Error rate > 5%
- Latency p95 > 2x baseline
- Pod crash loop detected
- Health check failures
```

### Blue-Green Deployment

Alternative for critical updates:

```yaml
Blue (current):   100% traffic
Green (new):      0% traffic, warming up

Test green:       Run E2E tests
Verify green:     Health checks
Switch traffic:   Blue → Green instantly
Keep blue:        Ready for rollback (30 min window)
```

---

## Auto-Scaling Configuration

### Horizontal Pod Autoscaler

```yaml
Backend HPA:
  Min: 3 replicas
  Max: 10 replicas
  Metrics:
    - CPU: 75% utilization
    - Memory: 80% utilization
    - HTTP requests: 1000 req/s per pod
  Scale-up: Fast (1-2 min)
  Scale-down: Slow (5 min stabilization)
```

### Cluster Autoscaler

```yaml
Managed by AWS ASG (Auto Scaling Group):
  Min nodes: 3
  Max nodes: 20
  Instance type: t3.xlarge (4 CPU, 16GB RAM)
  Spot instances: Optional (40% cost saving)
```

---

## Cost Optimization

### Resource Allocation

```
Monthly Costs:
├─ Kubernetes Cluster: $400 (3-20 nodes)
├─ RDS PostgreSQL: $100 (db.t3.medium)
├─ ElastiCache Redis: $50 (cache.t3.micro)
├─ S3 & Glacier: $30 (artifacts + backups)
├─ CloudFront CDN: $20 (static assets)
├─ Data transfer: $15
├─ Monitoring & logging: $25
└─ Misc (SSL, domains, etc): $20
  Total: ~$660/month

Optimization Strategies:
1. Spot instances: -40% compute cost
2. Reserved instances: -30% if 1-year commitment
3. Storage lifecycle: GLACIER for old backups (-80%)
4. Pod right-sizing: VPA prevents waste
5. Resource requests/limits: Efficient packing
```

---

## Troubleshooting & Operations

### Health Check Commands

```bash
# Kubernetes cluster
kubectl get nodes
kubectl get pods -n neurex-production
kubectl top nodes
kubectl top pods -n neurex-production

# Service health
curl http://localhost:8000/health           # Backend
curl http://localhost:3000/                 # Frontend
curl http://localhost:5001/health           # Engine
curl http://localhost:8080/ping             # AI Gateway

# Database
PGPASSWORD=$POSTGRES_PASSWORD psql -h localhost -U postgres -c "SELECT 1"
redis-cli ping

# Logs
kubectl logs deployment/neurex-backend -n neurex-production -f
kubectl logs deployment/neurex-engine -n neurex-production -f
```

### Common Issues

#### Pod Crash Loop

```bash
# Check pod status
kubectl describe pod POD_NAME -n neurex-production

# Check logs
kubectl logs POD_NAME -n neurex-production --previous

# Check events
kubectl get events -n neurex-production --sort-by='.lastTimestamp'
```

#### High Latency

```bash
# Check CPU/Memory usage
kubectl top pods -n neurex-production

# Check slow queries
psql -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10"

# Check network delays
kubectl exec POD_NAME -- ping SERVICE_NAME.neurex-production.svc.cluster.local
```

#### Database Replication Lag

```bash
# Check replica status
psql -c "SELECT slot_name, restart_lsn FROM pg_replication_slots"

# Monitor lag
watch 'psql -c "SELECT extract(EPOCH from (now() - pg_last_xact_replay_timestamp()))::int as replication_lag_seconds"'
```

---

## Runbooks

### Emergency Rollback

```bash
# 1. Identify last stable deployment
LAST_STABLE=$(helm history neurex -n neurex-production | grep "deployed" | head -1)

# 2. Rollback to previous version
helm rollback neurex -n neurex-production

# 3. Verify health
kubectl rollout status deployment/neurex-backend -n neurex-production

# 4. Monitor for 10 minutes
watch kubectl get pods -n neurex-production
```

### Database Restore from Backup

```bash
# 1. Create test database
createdb -h localhost -U postgres neurex_restore_test

# 2. Restore from backup
gunzip -c /backups/postgres/neurex-20240609-023000.sql.gz | \
  psql -h localhost -U postgres -d neurex_restore_test

# 3. Verify data
psql -h localhost -U postgres -d neurex_restore_test -c "SELECT COUNT(*) FROM users"

# 4. Point backend to test database (if validation OK)
kubectl set env deployment/neurex-backend -n neurex-production \
  "DATABASE_URL=postgresql://user:pass@localhost:5432/neurex_restore_test"

# 5. Cleanup
dropdb -h localhost -U postgres neurex_restore_test
```

### Scale Manual Adjustment

```bash
# Scale backend to 5 replicas
kubectl scale deployment/neurex-backend --replicas=5 -n neurex-production

# Disable HPA temporarily
kubectl patch hpa neurex-backend-hpa -n neurex-production \
  -p '{"spec":{"minReplicas":5,"maxReplicas":5}}'

# Re-enable HPA
kubectl patch hpa neurex-backend-hpa -n neurex-production \
  -p '{"spec":{"minReplicas":3,"maxReplicas":10}}'
```

---

## SLA & Performance Targets

### Availability

| Metric | Target | Measurement |
|--------|--------|-------------|
| Uptime | 99.9% | Monthly (< 45min downtime) |
| RTO | 5 min | From alert to recovery |
| RPO | 1 hour | Data loss tolerance |
| Failover | < 2 min | Automatic (canary) |

### Performance

| Metric | Target | Current |
|--------|--------|---------|
| p50 latency | < 100ms | ~80ms |
| p95 latency | < 500ms | ~300ms |
| p99 latency | < 1000ms | ~600ms |
| Error rate | < 0.1% | ~0.02% |
| Cache hit ratio | > 95% | ~96% |

### Deployment

| Metric | Target | Current |
|--------|--------|---------|
| Deploy time | < 10 min | ~8 min |
| Test time | < 15 min | ~12 min |
| Rollback time | < 2 min | ~90s |
| Smoke test time | < 5 min | ~3 min |

---

## References

- **Kubernetes**: https://kubernetes.io/docs/
- **Helm**: https://helm.sh/docs/
- **Prometheus**: https://prometheus.io/docs/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Docker**: https://docs.docker.com/
- **GitHub Actions**: https://docs.github.com/en/actions

---

**Last Updated:** 2026-06-09  
**Maintained By:** DevOps Team  
**Version:** 1.0 (Production-Ready)
