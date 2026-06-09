# Production Infrastructure Setup — Neurex AI Automation Platform

**Last Updated:** 2026-06-09  
**Timeline:** 10 days for 1 DevOps engineer  
**Status:** Complete infrastructure templates and documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Helm Chart Setup](#helm-chart-setup)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Log Aggregation](#log-aggregation)
7. [GitOps with ArgoCD](#gitops-with-argocd)
8. [Security Best Practices](#security-best-practices)
9. [Disaster Recovery](#disaster-recovery)
10. [Runbooks](#runbooks)

---

## Overview

This document provides complete infrastructure setup for deploying Neurex AI Automation Platform to production on Kubernetes. It covers:

- **Kubernetes manifests** with resource limits, health checks, and auto-scaling
- **Helm charts** for templated deployments across environments
- **Prometheus & Grafana** for monitoring and alerting
- **Loki + ELK integration** for log aggregation
- **ArgoCD** for GitOps-based continuous deployment
- **Security hardening** with RBAC, network policies, and pod security

### Timeline Breakdown (10 days)

```
Day 1-2: K8s manifests + Helm chart setup (32 hours)
Day 3-4: Monitoring infrastructure (16 hours)
Day 5-6: Log aggregation + centralization (16 hours)
Day 7-8: ArgoCD setup + GitOps workflow (16 hours)
Day 9-10: Security audit + disaster recovery drills (20 hours)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Production Kubernetes Cluster                 │
│                        (EKS / GKE / AKS)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Neurex Namespace                       │  │
│  │                                                            │  │
│  │  Frontend    Backend    AI Gateway    Engine              │  │
│  │    (2)       (2-6)        (2-8)         (1)               │  │
│  │   Next.js   FastAPI      FastAPI       Flask              │  │
│  │   3000      8000          8080         5001               │  │
│  │                                                            │  │
│  │  [Services] ─────→ [Ingress] ────→ Load Balancer         │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Stateful Services                            │  │
│  │                                                            │  │
│  │  PostgreSQL (50Gi)     Redis (10Gi)                       │  │
│  │     (Primary)           (Standalone)                       │  │
│  │   Automated Backups    Key-Value Store                    │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Observability Stack                            │  │
│  │                                                            │  │
│  │  Prometheus    Grafana     Loki      AlertManager         │  │
│  │    (50Gi)      (10Gi)      (50Gi)                         │  │
│  │   Metrics     Dashboards   Logs      Alerting             │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            GitOps (ArgoCD)                                │  │
│  │                                                            │  │
│  │  Continuous Deployment    Self-Healing    Rollbacks       │  │
│  │  Git as Source of Truth   Auto-Sync      Notifications    │  │
│  │                                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

                              External
                          │
                    ┌─────┴──────┐
                    │             │
            [Datadog]     [GitHub] (GitOps)
             APM/Logs     Webhooks
```

---

## Kubernetes Deployment

### Prerequisites

```bash
# Kubernetes cluster (v1.25+)
kubectl version --client

# Required tools
helm version          # v3.10+
kubectl apply plugin

# Storage classes
kubectl get storageclass

# Ingress controller (NGINX)
kubectl get ingressclass
```

### Initial Setup

```bash
# 1. Create namespace
kubectl apply -f infra/k8s/namespace.yaml

# 2. Create secrets (replace with actual values)
kubectl create secret generic neurex-secrets \
  --from-literal=database-url=postgresql://neurex:CHANGEME@postgres:5432/neurex_prod \
  --from-literal=jwt-secret=$(openssl rand -base64 64) \
  --from-literal=engine-internal-key=$(openssl rand -hex 32) \
  -n neurex

# 3. Apply base manifests
kubectl apply -f infra/k8s/deployment.yaml
kubectl apply -f infra/k8s/service.yaml
kubectl apply -f infra/k8s/ingress.yaml

# 4. Verify deployments
kubectl get deployments -n neurex
kubectl get pods -n neurex
kubectl get svc -n neurex
```

### Core Deployments

#### Backend (FastAPI)
- **Replicas:** 2-6 (HPA based on CPU/memory)
- **Resource Limits:** 250m CPU / 256Mi memory (request), 1000m CPU / 1Gi (limit)
- **Health Checks:** /health (liveness), /ready (readiness)
- **Database:** PostgreSQL with pooling (SQLAlchemy)
- **Cache:** Redis connection pooling

#### Frontend (Next.js)
- **Replicas:** 2-4 (HPA)
- **Resource Limits:** 100m CPU / 128Mi memory (request), 500m CPU / 512Mi (limit)
- **Static Assets:** Immutable cache (next.config.js headers)
- **Build:** Optimized for production (SWC compiler)

#### Engine (Flask)
- **Replicas:** 1 (stateful, persistent screenshots/reports)
- **Resource Limits:** 500m CPU / 512Mi memory (request), 2000m CPU / 2Gi (limit)
- **Persistent Volumes:** 
  - Engine Data: 10Gi
  - Screenshots: 5Gi
- **Headless Mode:** For Kubernetes environments

#### AI Gateway (FastAPI)
- **Replicas:** 2-8 (HPA, high-variance workloads)
- **Model Providers:** Ollama → vLLM → Groq → Gemini
- **Timeout:** 30 seconds (configurable)
- **Rate Limiting:** 100 req/min per user

### Configuration Management

**ConfigMaps:**
```yaml
neurex-config
├── log_level: info
├── cors_origins: https://bgtest.dev
├── feature_flags: {...}
└── model_routing: {...}
```

**Secrets:**
```yaml
neurex-secrets
├── database-url
├── jwt-secret
├── engine-internal-key
├── ai-provider-keys
└── external-integrations
```

---

## Helm Chart Setup

### Chart Structure

```
infra/helm/neurex-platform/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default values
├── values-dev.yaml         # Dev overrides
├── values-staging.yaml     # Staging overrides
├── values-prod.yaml        # Production overrides
└── templates/
    ├── namespace.yaml
    ├── backend-deployment.yaml
    ├── frontend-deployment.yaml
    ├── engine-deployment.yaml
    ├── ai-gateway-deployment.yaml
    ├── services.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── serviceaccount.yaml
    ├── rolebinding.yaml
    ├── networkpolicy.yaml
    ├── pdb.yaml
    └── hpa.yaml
```

### Helm Installation

```bash
# Add dependencies
helm dependency update infra/helm/neurex-platform

# Dry-run validation
helm template neurex infra/helm/neurex-platform \
  -f infra/helm/neurex-platform/values-prod.yaml \
  --namespace neurex

# Install
helm install neurex infra/helm/neurex-platform \
  -f infra/helm/neurex-platform/values-prod.yaml \
  -n neurex \
  --create-namespace

# Verify
helm status neurex -n neurex
helm list -n neurex

# Upgrade
helm upgrade neurex infra/helm/neurex-platform \
  -f infra/helm/neurex-platform/values-prod.yaml \
  -n neurex

# Rollback
helm rollback neurex 1 -n neurex
```

### Values Overrides

**Production (values-prod.yaml):**
```yaml
global:
  domain: bgtest.dev
  environment: production

backend:
  replicaCount: 4
  resources:
    limits:
      cpu: 1000m
      memory: 1Gi

frontend:
  replicaCount: 3

engine:
  persistence:
    size:
      data: 50Gi        # Larger in prod
      screenshots: 20Gi

postgres:
  primary:
    persistence:
      size: 100Gi       # Larger replicated storage
    replication:
      enabled: true

prometheus:
  retention: 30d        # Longer history
  storage:
    size: 100Gi

grafana:
  replicas: 2           # HA
  persistence:
    size: 20Gi
```

---

## Monitoring & Alerting

### Prometheus Setup

**Configuration:**
```bash
# Deploy Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace

# Apply alert rules
kubectl apply -f infra/k8s/prometheus-rules.yaml

# Access Prometheus
kubectl port-forward svc/prometheus-operated -n monitoring 9090:9090
# http://localhost:9090
```

**Scrape Targets:**
- Backend (8000/metrics)
- Engine (5001/metrics)
- AI Gateway (8080/metrics)
- PostgreSQL (postgres-exporter:9187)
- Redis (redis-exporter:9121)
- Nginx Ingress (9113)
- OTel Collector (8888)

### Alert Rules

**Critical Alerts:**
```
- BackendDown (5m)
- EngineDown (2m)
- AIGatewayDown (5m)
- PostgreSQLDown (2m)
- RedisDown (2m)
- DiskSpaceCritical (95%, 5m)
- CriticalMemoryUsage (95%, 5m)
- PodCrashLooping
- CertificateExpired
```

**Warning Alerts:**
```
- HighCPUUsage (85%, 10m)
- HighMemoryUsage (85%, 10m)
- APIHighLatency (P95 > 1s, 10m)
- APIHighErrorRate (>5%, 5m)
- PostgreSQLSlowQueries (>1s avg, 10m)
- RedisHighMemory (85%, 5m)
- DiskSpaceWarning (80%, 15m)
```

### Grafana Dashboards

**Pre-built Dashboards:**

1. **System Overview** (`dashboard-system.json`)
   - Cluster CPU/Memory
   - Pod count by namespace
   - Node health

2. **Neurex Application** (`dashboard-neurex.json`)
   - Request rate (req/s)
   - Error rate (5xx, 4xx)
   - Latency (P50, P95, P99)
   - Database connections
   - Cache hit ratio

3. **Engine Performance** (`dashboard-engine.json`)
   - Queue depth
   - Execution duration (percentiles)
   - Pass/fail ratio
   - Screenshot storage usage

4. **Infrastructure** (`dashboard-infra.json`)
   - Disk usage
   - Network I/O
   - CPU throttling events
   - OOM incidents

5. **AI Gateway** (`dashboard-ai.json`)
   - Provider latency by model
   - Error rate by provider
   - Token usage
   - Cost estimation

**Custom Dashboard Creation:**
```bash
# Export existing dashboard
curl -H "Authorization: Bearer $GRAFANA_TOKEN" \
  http://grafana:3000/api/dashboards/db/neurex-app \
  | jq '.dashboard' > neurex-dashboard.json

# Import to another Grafana
curl -X POST -H "Content-Type: application/json" \
  -d @neurex-dashboard.json \
  http://grafana:3000/api/dashboards/db
```

---

## Log Aggregation

### Loki Setup

**Configuration:**
```bash
# Deploy Loki Stack
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  -n logging \
  --create-namespace \
  -f infra/logging/loki-values.yaml

# Verify
kubectl get pods -n logging
kubectl logs -f deployment/loki -n logging
```

**Log Labels:**
```
job:         Service name (backend, engine, frontend)
pod:         Pod name
namespace:   Kubernetes namespace
instance:    Pod hostname
level:       Log level (info, warning, error, critical)
environment: Production/staging/dev
```

**Query Examples:**
```
# All errors
{level="error"} | json

# Backend API latency
{job="backend"} | json | response_time > 1000

# Engine test failures
{job="engine"} | json | status="failed"

# Database slow queries
{job="backend"} | json | query_duration > 5000
```

### Log Retention & Cleanup

**Retention Policy:**
```yaml
logs:
  retention:
    days: 30
    cold_storage:
      days: 90
      location: s3://neurex-logs/archive/
```

**S3 Archival:**
```bash
# Configure S3 backend
aws s3 mb s3://neurex-logs
aws s3api put-bucket-versioning \
  --bucket neurex-logs \
  --versioning-configuration Status=Enabled

# IAM Policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:*"],
      "Resource": "arn:aws:s3:::neurex-logs/*"
    }
  ]
}
```

### Log Aggregation Tools

**Option 1: Loki (Recommended)**
- Lightweight, efficient
- Grafana native integration
- Label-based indexing
- 30-day retention

**Option 2: ELK Stack (Advanced)**
```bash
# Elasticsearch
helm install elasticsearch elastic/elasticsearch \
  -n logging

# Logstash
helm install logstash elastic/logstash \
  -n logging

# Kibana
helm install kibana elastic/kibana \
  -n logging
```

**Option 3: Datadog (SaaS)**
```bash
# Agent installation
kubectl create namespace datadog
helm install datadog datadog/datadog \
  -n datadog \
  --set datadog.apiKey=$DD_API_KEY \
  --set datadog.appKey=$DD_APP_KEY
```

### Log Queries (Loki)

```
# Request latency percentiles
{job="backend"} | json | __error__="" | unwrap duration_ms | quantile_over_time(0.95, [5m])

# Error rate by endpoint
{job="backend"} | json | status >= 400 | group_without() (count_over_time([1m]))

# Pod restart events
{pod=~"neurex-.*"} | "restarted" | count(count_over_time([15m]))

# Database connection pool
{job="backend"} | json | unwrap db_pool_size | avg(avg_over_time([5m]))
```

---

## GitOps with ArgoCD

### ArgoCD Installation

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Or using Helm
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd \
  -n argocd \
  --create-namespace

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port-forward for access
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Change default password
argocd account update-password \
  --server localhost:8080 \
  --account admin \
  --new-password <new-password>
```

### ArgoCD Application Configuration

**neurex-application.yaml:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: neurex-platform
  namespace: argocd
spec:
  project: neurex-projects
  source:
    repoURL: https://github.com/neurex-ai/neurex-platform
    targetRevision: main
    path: infra/helm/neurex-platform
    helm:
      releaseName: neurex
      values: |
        global:
          environment: production
  destination:
    server: https://kubernetes.default.svc
    namespace: neurex
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
```

### Deployment Workflow

```
1. Developer commits to main branch
2. GitHub webhook triggers ArgoCD
3. ArgoCD syncs from Git
4. Helm templates rendered
5. kubectl apply automatically
6. Pods updated (rolling deployment)
7. Health checks verified
8. Notifications sent (Slack/email)
```

### Manual Sync

```bash
# Sync application
argocd app sync neurex-platform

# Sync with dry-run
argocd app sync neurex-platform --dry-run

# Sync specific resource
argocd app sync neurex-platform --resource apps:Deployment:backend

# Watch sync progress
argocd app wait neurex-platform --timeout 300

# Refresh from Git
argocd app refresh neurex-platform
```

### Rollback

```bash
# View history
argocd app history neurex-platform

# Rollback to previous sync
argocd app rollback neurex-platform

# Rollback to specific revision
argocd app rollback neurex-platform 2
```

### GitOps Best Practices

1. **Source of Truth:** Git repository is authoritative
2. **Declarative:** All infrastructure defined in YAML
3. **Automated:** No manual `kubectl apply`
4. **Audit Trail:** All changes tracked in Git history
5. **Notifications:** Slack/email on sync failure
6. **Secrets:** Use ExternalSecrets or sealed-secrets
7. **Branching:** main→production, staging→staging

---

## Security Best Practices

### RBAC Configuration

```yaml
# Service Account with minimal permissions
apiVersion: v1
kind: ServiceAccount
metadata:
  name: neurex-app
  namespace: neurex

---
# Role for pod operations
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: neurex-app
  namespace: neurex
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]  # Only read, no write

---
# Bind role to service account
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: neurex-app
  namespace: neurex
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: neurex-app
subjects:
  - kind: ServiceAccount
    name: neurex-app
    namespace: neurex
```

### Network Policies

```yaml
# Deny all ingress by default
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: neurex
spec:
  podSelector: {}
  policyTypes:
    - Ingress

---
# Allow ingress only from nginx-ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-ingress
  namespace: neurex
spec:
  podSelector:
    matchLabels:
      app: neurex-backend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
```

### Pod Security Policy / Pod Security Standards

```yaml
# Pod Security Standard (PSS)
apiVersion: v1
kind: Namespace
metadata:
  name: neurex
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

---
# Security Context
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
  capabilities:
    drop: ["ALL"]
```

### Secrets Management

**Option 1: Kubernetes Secrets**
```bash
# Create secret
kubectl create secret generic neurex-db \
  --from-literal=password=$DB_PASSWORD \
  -n neurex

# Mount as volume
volumeMounts:
  - name: secrets
    mountPath: /var/run/secrets
    readOnly: true

volumes:
  - name: secrets
    secret:
      secretName: neurex-db
```

**Option 2: ExternalSecrets (Recommended)**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets
  namespace: neurex
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: neurex-app

---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: neurex-db-secret
  namespace: neurex
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: neurex-db
  data:
    - secretKey: password
      remoteRef:
        key: neurex/db/password
```

### Image Security

```bash
# Use private registry
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=$GITHUB_USERNAME \
  --docker-password=$GITHUB_TOKEN \
  -n neurex

# Reference in pod spec
imagePullSecrets:
  - name: regcred

# Image signing (Cosign)
cosign sign --key cosign.key ghcr.io/neurex-ai/neurex-backend:latest

# Verify signature
cosign verify --key cosign.pub ghcr.io/neurex-ai/neurex-backend:latest
```

---

## Disaster Recovery

### Backup Strategy

**Database Backups:**
```bash
# PostgreSQL automated backups
helm install pg-backup postgres-backup-api/pg-backup \
  -n neurex \
  --set postgresql.hostname=postgres \
  --set s3.bucket=neurex-backups

# Daily automated backups to S3
# Retention: 30 days (daily), 1 year (monthly)
```

**Persistent Volume Snapshots:**
```bash
# Create VolumeSnapshot
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: engine-data-snapshot
  namespace: neurex
spec:
  volumeSnapshotClassName: csi-snapshot-class
  source:
    persistentVolumeClaimName: engine-data-pvc

---
# Restore from snapshot
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: engine-data-restored
  namespace: neurex
spec:
  storageClassName: fast-ssd
  dataSource:
    name: engine-data-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

**Etcd Backups:**
```bash
# For managed K8s (EKS, GKE, AKS), automated etcd backups included
# For self-managed clusters:
etcdctl snapshot save backup-$(date +%Y%m%d).db

# S3 upload
aws s3 cp backup-*.db s3://neurex-backups/etcd/
```

### Disaster Recovery Procedures

**RTO (Recovery Time Objective):** 1 hour  
**RPO (Recovery Point Objective):** 15 minutes

**Procedure 1: Pod Failure**
- Automatic: ReplicaSet creates new pod (30s)
- Manual: `kubectl delete pod <pod-name>`
- Verification: `kubectl get pods -w`

**Procedure 2: Node Failure**
- Automatic: Pods evicted and rescheduled (5m)
- Manual: `kubectl cordon <node>; kubectl drain <node> --ignore-daemonsets`
- Fix: Replace node, rejoin cluster

**Procedure 3: Database Corruption**
- Detection: Health check failure, slow queries
- Recovery:
  ```bash
  # Restore from backup
  pg_restore -d neurex < backup-20260609.sql
  
  # Verify data integrity
  psql -d neurex -c "SELECT COUNT(*) FROM users;"
  
  # Re-run migrations if needed
  alembic upgrade head
  ```

**Procedure 4: Cluster Failure (Full)**
- Restore from saved manifests
- Re-apply Helm releases
- Restore persistent volumes from snapshots
- Verify DNS, TLS certificates

---

## Runbooks

### Alert Response Procedures

#### 🔴 BackendDown (Critical)

**Detection:** 5 minutes without /health response

**Steps:**
1. Check pod status: `kubectl describe pod neurex-backend-* -n neurex`
2. View logs: `kubectl logs -f deployment/neurex-backend -n neurex`
3. Check database: `psql -h postgres -U neurex -d neurex -c "SELECT 1"`
4. Restart pod: `kubectl rollout restart deployment/neurex-backend -n neurex`
5. Wait for readiness: `kubectl rollout status deployment/neurex-backend -n neurex`
6. Verify: `curl -k https://bgtest.dev/api/health`

#### 🟠 HighMemoryUsage (Warning)

**Detection:** Memory > 85% for 10 minutes

**Steps:**
1. Identify heavy pod: `kubectl top pods -n neurex --sort-by=memory`
2. Check OOM kills: `kubectl describe pod <pod> | grep OOMKilled`
3. Review logs for memory leaks: `kubectl logs <pod>`
4. Increase limits (if safe): Edit deployment memory request/limit
5. Scale up replicas: `kubectl scale deployment neurex-backend --replicas=4 -n neurex`
6. Monitor: `kubectl top pod <pod> --containers`

#### 🟠 APIHighErrorRate (Warning)

**Detection:** 5xx errors > 5% for 5 minutes

**Steps:**
1. Check error logs: `curl -X GET http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~%225..%22}[5m])`
2. Identify failing endpoint: `kubectl logs -n neurex -l app=neurex-backend --tail=100 | grep ERROR`
3. Check dependencies: Database, Redis, AI Gateway connectivity
4. Roll back if recent deployment: `helm rollback neurex -n neurex`
5. Manual restart if needed: `kubectl rollout restart deployment/neurex-backend -n neurex`

#### 🟠 PostgreSQLSlowQueries (Warning)

**Detection:** Average query duration > 1 second

**Steps:**
1. Enable query logging: `ALTER DATABASE neurex SET log_min_duration_statement = 1000;`
2. Identify slow queries: `SELECT query FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;`
3. Analyze query plan: `EXPLAIN ANALYZE SELECT ...;`
4. Add indexes if needed: `CREATE INDEX idx_name ON table(column);`
5. Check connection pool: `SELECT count(*) FROM pg_stat_activity;`
6. Restart backend if connections high: `kubectl rollout restart deployment/neurex-backend -n neurex`

#### 🔴 DiskSpaceCritical (Critical)

**Detection:** Free space < 5%

**Steps:**
1. Check usage: `kubectl exec -n neurex <pod> -- df -h`
2. Identify large files/logs: `kubectl exec <pod> -- du -sh /* | sort -h`
3. Clean old logs: `kubectl exec <pod> -- find /var/log -mtime +30 -delete`
4. Expand PVC: 
   ```bash
   kubectl patch pvc engine-data-pvc -n neurex \
     -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'
   ```
4. Delete old data (if safe): Archive old test runs, delete old engine screenshots

---

## Scaling Strategies

### Horizontal Pod Autoscaler (HPA)

**Backend Scaling (CPU-based):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: neurex-backend-hpa
  namespace: neurex
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: neurex-backend
  minReplicas: 2
  maxReplicas: 6
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70  # Scale up at 70% CPU
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80  # Scale up at 80% memory
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 50  # Scale down by 50% max
          periodSeconds: 15
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100  # Double capacity
          periodSeconds: 15
        - type: Pods
          value: 2  # Add 2 pods
          periodSeconds: 15
      selectPolicy: Max  # Use policy that scales up most
```

**Custom Metrics Scaling (Request-based):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: neurex-ai-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: neurex-ai-gateway
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"  # 1000 req/s per pod
```

### Vertical Pod Autoscaler (VPA)

```bash
# Install VPA
helm repo add fairwinds-stable https://charts.fairwinds.com/stable
helm install vpa fairwinds-stable/vpa \
  -n kube-system

# Configure for backend
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: neurex-backend-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: neurex-backend
  updatePolicy:
    updateMode: "Auto"  # Auto-scale without restart (if possible)
  resourcePolicy:
    containerPolicies:
      - containerName: backend
        minAllowed:
          cpu: 100m
          memory: 128Mi
        maxAllowed:
          cpu: 2000m
          memory: 2Gi
```

### Cluster Autoscaler

```bash
# EKS
eksctl create nodegroup --cluster=neurex \
  --name=neurex-ng \
  --nodes-min=2 \
  --nodes-max=10 \
  --node-type=t3.large

# GKE
gcloud container clusters update neurex \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10 \
  --zone=us-central1-a
```

---

## Maintenance & Upgrades

### Kubernetes Upgrades

```bash
# Check current version
kubectl version --short

# Plan upgrade (check compatibility)
# - Backend: Python version compatibility
# - Frontend: Node version compatibility

# Upgrade cluster (managed service)
# AWS EKS: aws eks update-cluster-version --name neurex --kubernetes-version 1.28
# GKE: gcloud container clusters upgrade neurex --cluster-version 1.28

# Verify upgrade
kubectl version --short
kubectl get nodes
```

### Application Updates

```bash
# Update Helm values
helm repo update

# Upgrade release
helm upgrade neurex infra/helm/neurex-platform \
  -f infra/helm/neurex-platform/values-prod.yaml \
  -n neurex \
  --wait

# Monitor rollout
kubectl rollout status deployment/neurex-backend -n neurex

# Rollback if needed
helm rollback neurex -n neurex
```

### Certificate Renewal

```bash
# Let's Encrypt certificates auto-renew (cert-manager handles)
# Verify cert expiry
kubectl get certificate -n neurex

# Manual renewal if needed
kubectl delete secret neurex-tls -n neurex
kubectl delete challenge neurex-* -n neurex
# cert-manager will recreate automatically
```

---

## Cost Optimization

### Resource Recommendations

| Component | CPU Request | CPU Limit | Memory Req | Memory Limit |
|-----------|-------------|-----------|-----------|--------------|
| Backend | 250m | 1000m | 256Mi | 1Gi |
| Frontend | 100m | 500m | 128Mi | 512Mi |
| Engine | 500m | 2000m | 512Mi | 2Gi |
| AI Gateway | 250m | 1000m | 256Mi | 1Gi |
| PostgreSQL | 500m | 2000m | 512Mi | 2Gi |
| Redis | 100m | 500m | 128Mi | 512Mi |

### Cost Saving Strategies

1. **Spot/Preemptible Instances:** Save 70% on compute
2. **Reserved Instances:** 40% savings for stable workloads
3. **Right-sizing:** Match resources to actual usage
4. **Vertical Pod Autoscaler:** Optimize resource requests
5. **Pod Disruption Budgets:** Minimize interruptions on spot instances

---

## Appendix

### Useful Commands

```bash
# Cluster info
kubectl cluster-info
kubectl get nodes -o wide
kubectl describe node <node>

# Pod debugging
kubectl exec -it <pod> -- /bin/bash
kubectl logs -f <pod> --previous  # Crashed pod logs
kubectl port-forward svc/<service> <local>:<remote>

# Resource usage
kubectl top nodes
kubectl top pods -n neurex

# Events
kubectl get events -n neurex --sort-by='.lastTimestamp'

# Helm
helm repo update
helm search repo neurex
helm values neurex -n neurex
helm get notes neurex -n neurex

# ArgoCD
argocd app list
argocd app logs neurex-platform --kind Application
argocd repo list
```

### References

- Kubernetes Documentation: https://kubernetes.io/docs/
- Helm Charts: https://artifacthub.io/
- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- ArgoCD Documentation: https://argo-cd.readthedocs.io/
- Loki Documentation: https://grafana.com/docs/loki/

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Owner:** DevOps Team  
**Status:** Production Ready
