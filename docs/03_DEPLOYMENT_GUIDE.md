# Neurex Deployment Guide

**Last Updated:** 2026-06-09  
**Target Platforms:** Docker, Kubernetes, AWS ECS  
**Status:** Production-Ready  
**Estimated Deployment Time:** 30-45 minutes

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment (Development)](#docker-deployment-development)
4. [Kubernetes Deployment (Production)](#kubernetes-deployment-production)
5. [AWS ECS Deployment](#aws-ecs-deployment)
6. [Database Migrations](#database-migrations)
7. [Secrets Management](#secrets-management)
8. [Health Checks & Monitoring](#health-checks--monitoring)
9. [Rollback Procedure](#rollback-procedure)
10. [Post-Deployment Verification](#post-deployment-verification)

---

## Pre-Deployment Checklist

Before deploying to **ANY** environment, complete this checklist:

### Code & Tests

- [ ] All tests pass: `make test-backend` (backend unit tests)
- [ ] All tests pass: `make test-smoke` (2-minute smoke suite)
- [ ] No type errors: `make type-check` (TypeScript)
- [ ] No lint errors: `make lint` (ruff + eslint)
- [ ] Code review completed and approved
- [ ] Changelog updated with breaking changes (if any)
- [ ] Git branch is clean: `git status` shows nothing

### Secrets & Security

- [ ] All secrets in `.env` or secret manager (never in code)
- [ ] JWT_SECRET is 64+ characters (production)
- [ ] DATABASE_URL points to correct environment
- [ ] SSL certificates valid and configured
- [ ] CORS_ORIGINS includes frontend domain only
- [ ] Rate limiting enabled in production
- [ ] IP whitelisting configured (if applicable)

### Infrastructure

- [ ] Database backups enabled and tested
- [ ] Redis persistence enabled (AOF/RDB)
- [ ] Disk space adequate (2GB minimum for logs + artifacts)
- [ ] Memory allocation: 4GB minimum (8GB recommended)
- [ ] Network connectivity verified (DNS, firewall rules)
- [ ] Load balancer health checks configured
- [ ] CDN configured (if applicable)

### Documentation

- [ ] Deployment plan documented
- [ ] Rollback plan documented
- [ ] Team notified (Slack, email)
- [ ] Maintenance window scheduled (if needed)
- [ ] Support team briefed on changes

---

## Environment Setup

### Prerequisites

```bash
# Required tools
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+ (for K8s deployments)
- kubectl 1.24+
- Helm 3.0+ (optional, for Helm charts)
- PostgreSQL client (psql) for direct DB access
- Python 3.11+ (for backend development)
- Node.js 18+ (for frontend development)
```

### Environment Files

Create `.env` file in project root:

```bash
# ── Application ────────────────────────────────────────────
ENV=production  # production, staging, development
APP_NAME=Neurex
DEBUG=false

# ── Database ───────────────────────────────────────────────
DATABASE_URL=postgresql+psycopg2://user:password@db.example.com:5432/neurex_db
# Read-replica (optional, Faz 3.1)
READ_REPLICA_URL=postgresql+psycopg2://user:password@db-read.example.com:5432/neurex_db
READ_REPLICA_ENABLED=true

# ── Redis ──────────────────────────────────────────────────
REDIS_URL=redis://user:password@redis.example.com:6379/0
REDIS_REQUIRED=true
RATE_LIMIT_REQUIRED=true

# ── Security ───────────────────────────────────────────────
JWT_SECRET=$(openssl rand -base64 64)  # 64+ chars
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CICD_REQUIRE_WEBHOOK_SECRETS=true
CORS_ORIGINS=https://app.neurex.ai,https://app-staging.neurex.ai

# ── Internal Keys ──────────────────────────────────────────
ENGINE_INTERNAL_KEY=$(openssl rand -base64 32)
GATEWAY_INTERNAL_KEY=$(openssl rand -base64 32)

# ── AI Gateway ─────────────────────────────────────────────
AI_GATEWAY_BASE_URL=http://ai-gateway:8080
AI_PROVIDER=ollama  # ollama, groq, gemini, openai
OLLAMA_BASE_URL=http://ollama:11434/v1
OLLAMA_MODEL_ANALYST=qwen2.5:14b
OLLAMA_MODEL_FAST=llama3.1:8b
OLLAMA_MODEL_CODER=qwen2.5-coder:7b

# ── Storage (S3/MinIO) ─────────────────────────────────────
ARTIFACT_STORAGE_BACKEND=s3  # s3 required for multi-instance
S3_BUCKET=neurex-artifacts
S3_ENDPOINT_URL=https://s3.amazonaws.com  # or MinIO
S3_ACCESS_KEY_ID=<aws-key>
S3_SECRET_ACCESS_KEY=<aws-secret>

# ── Logging & Monitoring ──────────────────────────────────
SENTRY_DSN=https://xxxxx@sentry.io/12345
LOG_LEVEL=INFO
RUNNING_IN_DOCKER=1

# ── Integrations ───────────────────────────────────────────
GITHUB_WEBHOOK_SECRET=<secret>
GITLAB_WEBHOOK_TOKEN=<token>
JIRA_API_KEY=<api-key>
N8N_CALLBACK_TOKEN=<token>

# ── Email (SendGrid) ───────────────────────────────────────
SENDGRID_API_KEY=<api-key>
SENDGRID_FROM_EMAIL=noreply@neurex.ai

# ── Trusted Proxy (behind load balancer) ──────────────────
TRUSTED_PROXY_IPS=10.0.0.0/8,172.16.0.0/12  # Load balancer IPs
```

### Generate Secrets (Secure)

```bash
#!/bin/bash
# secure_gen_secrets.sh

# Generate strong random secrets
JWT_SECRET=$(openssl rand -base64 64)
ENGINE_KEY=$(openssl rand -base64 32)
GATEWAY_KEY=$(openssl rand -base64 32)

# Store in secure secret manager (not .env)
# AWS Secrets Manager example:
aws secretsmanager create-secret --name neurex/prod/jwt-secret --secret-string "$JWT_SECRET"
aws secretsmanager create-secret --name neurex/prod/engine-key --secret-string "$ENGINE_KEY"
aws secretsmanager create-secret --name neurex/prod/gateway-key --secret-string "$GATEWAY_KEY"

echo "Secrets created in AWS Secrets Manager"
```

---

## Docker Deployment (Development)

### Quick Start (Full Stack)

```bash
# 1. Clone repository
git clone https://github.com/neurex/neurex.git
cd neurex

# 2. Create .env
cp .env.example .env
# Edit .env with your configuration

# 3. Start all services
docker compose up -d

# 4. Run migrations
docker compose exec backend alembic upgrade head

# 5. Seed data (optional)
docker compose exec backend python -m scripts.seed_demo_data

# 6. Verify health
curl http://localhost:8000/health
curl http://localhost:3000/health

# 7. Access application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Email: admin@example.com / admin123 (from seed)
```

### Service Health Checks

```bash
# Check all services
docker compose ps

# View logs (tail)
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres

# Health check endpoint
curl http://localhost:8000/health | jq

# Redis check
docker compose exec redis redis-cli -a neurex_dev_redis_2026 ping
```

### Stopping Services

```bash
# Stop all (keep data)
docker compose down

# Stop and remove volumes (full reset)
docker compose down -v

# Stop specific service
docker compose stop backend
```

---

## Kubernetes Deployment (Production)

### Prerequisites

```bash
# 1. Create namespace
kubectl create namespace neurex-prod

# 2. Create secrets
kubectl create secret generic neurex-secrets \
  --from-literal=jwt-secret=$(openssl rand -base64 64) \
  --from-literal=db-password=$(openssl rand -base64 32) \
  --from-literal=redis-password=$(openssl rand -base64 32) \
  --from-literal=engine-key=$(openssl rand -base64 32) \
  --from-literal=gateway-key=$(openssl rand -base64 32) \
  -n neurex-prod

# 3. Create image registry secret (for private images)
kubectl create secret docker-registry neurex-registry \
  --docker-server=registry.neurex.ai \
  --docker-username=<user> \
  --docker-password=<password> \
  -n neurex-prod
```

### Kubernetes Manifests

**deployment/backend.yaml:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neurex-backend
  namespace: neurex-prod
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: neurex-backend
  template:
    metadata:
      labels:
        app: neurex-backend
        version: "1.0.0"
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: neurex-backend
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: backend
        image: neurex/backend:1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        - name: metrics
          containerPort: 9090
          protocol: TCP
        env:
        - name: ENV
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: neurex-secrets
              key: db-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: neurex-secrets
              key: jwt-secret
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: neurex-secrets
              key: redis-url
        - name: ENGINE_INTERNAL_KEY
          valueFrom:
            secretKeyRef:
              name: neurex-secrets
              key: engine-key
        - name: GATEWAY_INTERNAL_KEY
          valueFrom:
            secretKeyRef:
              name: neurex-secrets
              key: gateway-key
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 2000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        volumeMounts:
        - name: artifacts
          mountPath: /app/data/artifacts
      volumes:
      - name: artifacts
        persistentVolumeClaim:
          claimName: neurex-artifacts-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: neurex-backend
  namespace: neurex-prod
spec:
  selector:
    app: neurex-backend
  type: ClusterIP
  ports:
  - name: http
    port: 80
    targetPort: 8000
  - name: metrics
    port: 9090
    targetPort: 9090
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: neurex-backend-hpa
  namespace: neurex-prod
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
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Deploy to Kubernetes

```bash
# 1. Apply PostgreSQL (managed service recommended)
# Using AWS RDS, Azure Database, or managed Postgres

# 2. Apply Redis
kubectl apply -f deployment/redis.yaml

# 3. Apply backend
kubectl apply -f deployment/backend.yaml

# 4. Apply frontend
kubectl apply -f deployment/frontend.yaml

# 5. Apply ingress
kubectl apply -f deployment/ingress.yaml

# 6. Verify deployment
kubectl get pods -n neurex-prod
kubectl get svc -n neurex-prod

# 7. Port forward for testing
kubectl port-forward -n neurex-prod svc/neurex-backend 8000:80
```

---

## AWS ECS Deployment

### ECR Repository Setup

```bash
# Create ECR repositories
aws ecr create-repository --repository-name neurex/backend
aws ecr create-repository --repository-name neurex/frontend
aws ecr create-repository --repository-name neurex/engine

# Build and push images
docker build -t neurex/backend:1.0.0 ./backend
docker tag neurex/backend:1.0.0 <account>.dkr.ecr.us-east-1.amazonaws.com/neurex/backend:1.0.0
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/neurex/backend:1.0.0
```

### ECS Task Definition

```json
{
  "family": "neurex-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "<account>.dkr.ecr.us-east-1.amazonaws.com/neurex/backend:1.0.0",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:neurex/db-url"
        },
        {
          "name": "JWT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:neurex/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/neurex-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole"
}
```

### Deploy ECS Service

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster neurex-prod \
  --service-name neurex-backend \
  --task-definition neurex-backend:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-123,subnet-456],securityGroups=[sg-789]}"

# Update existing service
aws ecs update-service \
  --cluster neurex-prod \
  --service neurex-backend \
  --force-new-deployment
```

---

## Database Migrations

### Pre-Deployment Migration Test

```bash
# 1. Test in staging first (critical!)
docker compose -f docker-compose.staging.yml up -d

# 2. Run migrations
docker compose -f docker-compose.staging.yml exec backend \
  alembic upgrade head

# 3. Verify schema
docker compose -f docker-compose.staging.yml exec backend \
  alembic current

# 4. Run test suite
docker compose -f docker-compose.staging.yml exec backend \
  pytest tests/ -v

# 5. Check for errors
docker compose -f docker-compose.staging.yml logs backend
```

### Production Migration

```bash
# 1. Backup database (CRITICAL!)
pg_dump \
  postgresql://user:password@prod-db.example.com/neurex_db \
  > backup-$(date +%Y%m%d-%H%M%S).sql

# 2. Scale down replicas (gradual rolling update)
# Kubernetes:
kubectl scale deployment neurex-backend --replicas=1 -n neurex-prod

# ECS:
aws ecs update-service \
  --cluster neurex-prod \
  --service neurex-backend \
  --desired-count 1

# 3. Run migrations
# Within container:
docker run --rm \
  -e DATABASE_URL=$DATABASE_URL \
  neurex/backend:1.0.0 \
  alembic upgrade head

# 4. Verify migration
alembic current
alembic history

# 5. Scale back up
kubectl scale deployment neurex-backend --replicas=3
aws ecs update-service --cluster neurex-prod --service neurex-backend --desired-count 3

# 6. Run smoke tests
make test-smoke
```

### Rolling Back a Migration

```bash
# 1. Identify previous revision
alembic history

# 2. Downgrade (if possible)
alembic downgrade -1

# 3. If no downgrade available, restore from backup
psql -h prod-db.example.com -U neurex_user -d neurex_db < backup.sql

# 4. Notify team
slack "#deployments" "Migration rolled back due to error. Investigating..."
```

---

## Secrets Management

### AWS Secrets Manager (Recommended)

```bash
# Store secrets
aws secretsmanager create-secret \
  --name neurex/prod/jwt-secret \
  --secret-string "$(openssl rand -base64 64)"

# Retrieve in application
import boto3
client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='neurex/prod/jwt-secret')
jwt_secret = response['SecretString']
```

### HashiCorp Vault

```bash
# Write secret
vault kv put secret/neurex/prod \
  jwt_secret="$(openssl rand -base64 64)" \
  db_password="$(openssl rand -base64 32)"

# Read secret in application
import hvac
client = hvac.Client(url='http://vault:8200')
secret = client.secrets.kv.read_secret_version(path='neurex/prod')
```

### Kubernetes Secrets

```bash
# Create sealed secret (encryption at rest)
kubectl create secret generic neurex-secrets \
  --from-literal=jwt-secret=... \
  --dry-run=client -o yaml | \
  kubeseal -f - > sealed-secrets.yaml

# Apply sealed secret
kubectl apply -f sealed-secrets.yaml
```

---

## Health Checks & Monitoring

### Liveness & Readiness Probes

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 5

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3
  timeoutSeconds: 3
```

### Metrics & Monitoring

```bash
# View Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics to monitor
- http_request_duration_seconds (API latency)
- database_query_duration_seconds (DB slow queries)
- redis_command_duration_seconds (Cache latency)
- rate_limiter_hits_total (Rate limit hits)
- ai_gateway_request_errors_total (AI service errors)
```

### CloudWatch Logs (AWS)

```bash
# Create log group
aws logs create-log-group --log-group-name /ecs/neurex-backend

# Query logs
aws logs filter-log-events \
  --log-group-name /ecs/neurex-backend \
  --filter-pattern "ERROR"
```

---

## Rollback Procedure

### If Deployment Fails

**Step 1: Identify the issue**
```bash
# Check pod status
kubectl get pods -n neurex-prod
kubectl describe pod <pod-name> -n neurex-prod

# Check logs
kubectl logs <pod-name> -n neurex-prod
```

**Step 2: Immediate rollback**
```bash
# Kubernetes rollback
kubectl rollout undo deployment/neurex-backend -n neurex-prod

# ECS rollback (previous task definition)
aws ecs update-service \
  --cluster neurex-prod \
  --service neurex-backend \
  --task-definition neurex-backend:2  # Previous version
```

**Step 3: Database rollback (if migration failed)**
```bash
# Restore from backup
pg_restore -h prod-db -U neurex_user -d neurex_db \
  --clean --if-exists backup.sql

# Or downgrade migration
docker run --rm -e DATABASE_URL=$DATABASE_URL \
  neurex/backend:previous-version \
  alembic downgrade -1
```

**Step 4: Communication**
```bash
# Notify team
slack "#deployments" ":warning: Deployment rolled back. Investigating root cause."
slack "#incidents" "Incident #123: Production deployment failed. Root cause: ..."
```

---

## Post-Deployment Verification

### Verification Checklist

```bash
# 1. Health checks
curl -f http://localhost/health || echo "FAILED"

# 2. API accessibility
curl -f http://localhost:8000/docs

# 3. Database connectivity
docker compose exec backend python -c "
  from app.infra.database import AsyncSessionLocal
  async def test(): 
    async with AsyncSessionLocal() as session:
      result = await session.execute('SELECT 1')
      return result.fetchone()
" || echo "DB check FAILED"

# 4. Authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  -f || echo "Auth FAILED"

# 5. Smoke tests
make test-smoke

# 6. Monitor error rates (first 5 minutes)
kubectl logs -n neurex-prod -l app=neurex-backend --tail=100 | grep ERROR
```

### Load Testing (Optional)

```bash
# Using k6
k6 run tests/load/baseline.js \
  --vus 10 \
  --duration 30s \
  --metric-out grafana
```

---

## Disaster Recovery

### Recovery Time Objective (RTO)

- **RTO:** 15 minutes (target)
- **RPO:** 5 minutes (data loss tolerance)

### Backup Frequency

- **Full backup:** Daily at 2 AM UTC
- **Incremental backups:** Every 6 hours
- **Transaction logs:** Continuous (WAL)

### Testing Backups

```bash
# Weekly restore test
# 1. Spin up staging environment
# 2. Restore from production backup
# 3. Run sanity checks
# 4. Delete test environment
```

---

**End of Deployment Guide**
