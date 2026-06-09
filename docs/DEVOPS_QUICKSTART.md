# DevOps Infrastructure — Quick Start Guide

## 1. Immediate Actions (Today)

### Deploy GitHub Actions Pipeline
```bash
# Copy optimized workflow
cp .github/workflows/optimize-ci-cd.yml .github/workflows/

# Verify workflow syntax
gh workflow view optimize-ci-cd.yml

# Trigger test run
git push origin main
```

### Update Docker Images
```bash
# Backup current Dockerfiles
cp backend/Dockerfile backend/Dockerfile.old
cp apps/web/Dockerfile apps/web/Dockerfile.old

# Use optimized versions (staging first!)
cp backend/Dockerfile.optimized backend/Dockerfile
cp apps/web/Dockerfile.optimized apps/web/Dockerfile

# Test build locally
docker build -f backend/Dockerfile backend/ --tag neurex-backend:test
docker build -f apps/web/Dockerfile apps/web/ --tag neurex-frontend:test
```

### Setup Prometheus Monitoring
```bash
# Create config directories
mkdir -p infra/prometheus/rules

# Copy config files
cp infra/prometheus/prometheus.yml docker-compose.prod.yml  # Reference it
cp infra/prometheus/rules/alerts.yml docker-compose.prod.yml

# Restart monitoring stack
docker compose -f docker-compose.prod.yml up -d prometheus alertmanager grafana
```

---

## 2. This Week

### Apply Helm Chart
```bash
# Install Helm (if not already installed)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Create namespace
kubectl create namespace neurex-production
kubectl create namespace neurex-staging

# Add Helm repo (update with your actual repo)
helm repo add neurex-repo <YOUR_HELM_REPO_URL>
helm repo update

# Deploy to staging first
helm install neurex neurex-repo/neurex \
  -n neurex-staging \
  -f infra/helm/production-values.yaml

# Verify deployment
kubectl rollout status deployment/neurex-backend -n neurex-staging
```

### Enable Auto-Scaling
```bash
# Install Metrics Server (if not present)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Apply auto-scaling config
kubectl apply -f infra/auto-scaling-config.yaml

# Verify HPAs are working
kubectl get hpa -n neurex-production
kubectl top pods -n neurex-production
```

### Setup Backup Automation
```bash
# Make scripts executable
chmod +x infra/backup-restore-automation.sh
chmod +x infra/secret-rotation.sh

# Create backup directory
mkdir -p /backups/postgres /backups/artifacts /backups/k8s-secrets /backups/etcd

# Test backup script locally
bash infra/backup-restore-automation.sh

# Schedule daily backups via cron
0 2 * * * /path/to/infra/backup-restore-automation.sh >> /var/log/neurex-backup.log 2>&1
```

---

## 3. Next Week

### Configure Monitoring Alerts
```bash
# Verify AlertManager is running
kubectl get deployment alertmanager -n neurex-production

# Update AlertManager config with Slack webhook
kubectl set env deployment/alertmanager -n neurex-production \
  "ALERTMANAGER_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Test alert by triggering a dummy alert
kubectl exec -it deployment/prometheus -n neurex-production -- \
  curl -X POST http://localhost:9093/api/v1/alerts \
  -d '[{"labels":{"alertname":"TestAlert"}}]'
```

### Enable Secret Rotation
```bash
# Run first rotation manually
bash infra/secret-rotation.sh

# Schedule quarterly rotations
0 2 1 * * /path/to/infra/secret-rotation.sh >> /var/log/neurex-secret-rotation.log 2>&1

# Verify secrets in Kubernetes
kubectl get secrets neurex-secrets -n neurex-production -o yaml
```

### Setup Cross-Region Backup
```bash
# Configure S3 cross-region replication
aws s3api put-bucket-replication \
  --bucket neurex-backups-prod \
  --replication-configuration file://infra/s3-replication.json

# Verify replication status
aws s3api get-bucket-replication --bucket neurex-backups-prod
```

---

## 4. Testing & Validation

### Validate CI/CD Pipeline
```bash
# Create test branch
git checkout -b test/devops-improvements

# Make dummy change
echo "# Test" >> README.md

# Push and watch Actions
git add README.md
git commit -m "test: CI/CD pipeline validation"
git push origin test/devops-improvements

# Monitor workflow
gh run list --workflow=optimize-ci-cd.yml --state all
gh run view <RUN_ID>
```

### Test Deployment
```bash
# Deploy to staging
helm upgrade neurex neurex-repo/neurex \
  -n neurex-staging \
  -f infra/helm/staging-values.yaml

# Watch rollout
kubectl rollout status deployment/neurex-backend -n neurex-staging

# Run smoke tests
curl https://staging.neurex.ai/api/v1/health
curl https://staging.neurex.ai/
```

### Test Backup & Recovery
```bash
# Create backup
bash infra/backup-restore-automation.sh

# Verify backup
ls -lh /backups/postgres/

# Test restore
gunzip -c /backups/postgres/latest.sql.gz | \
  psql -h localhost -U postgres -d neurex_test

# Cleanup test database
dropdb -h localhost -U postgres neurex_test
```

### Test Auto-Scaling
```bash
# Generate load on backend
ab -n 10000 -c 100 http://localhost:8000/health

# Watch pods scale up
watch kubectl get pods -n neurex-production

# Wait for scale-down
# (takes ~5-10 min)
watch kubectl get pods -n neurex-production
```

---

## 5. Production Deployment

### Pre-Deployment Checklist
- [ ] All tests passing in CI/CD
- [ ] Staging deployment successful
- [ ] E2E tests green against staging
- [ ] Monitoring dashboards working
- [ ] Alert rules validated
- [ ] Backup tested & verified
- [ ] Rollback plan documented
- [ ] Team notified of deployment window

### Deploy to Production
```bash
# Create production namespace (if new)
kubectl create namespace neurex-production

# Deploy with Helm
helm upgrade --install neurex neurex-repo/neurex \
  -n neurex-production \
  -f infra/helm/production-values.yaml \
  --set image.tag=<VERSION> \
  --timeout 10m \
  --wait

# Monitor deployment
kubectl rollout status deployment/neurex-backend -n neurex-production
kubectl rollout status deployment/neurex-frontend -n neurex-production

# Verify health
curl https://app.neurex.ai/api/v1/health
```

### Post-Deployment Validation
```bash
# Check all pods running
kubectl get pods -n neurex-production

# Verify HPA status
kubectl get hpa -n neurex-production

# Check metrics collection
kubectl exec -it deployment/prometheus -n neurex-production -- \
  curl -s http://localhost:9090/api/v1/query?query=up | jq

# Monitor error rates
kubectl logs deployment/neurex-backend -n neurex-production -f --tail=100
```

---

## 6. Ongoing Operations

### Daily Checks
```bash
# Pod status
kubectl get pods -n neurex-production

# Node status
kubectl get nodes

# PVC status
kubectl get pvc -n neurex-production

# Check backup completion
ls -lt /backups/postgres/ | head -1
```

### Weekly Tasks
```bash
# Review monitoring dashboards
# Navigate to Grafana: https://app.neurex.ai/grafana

# Check alert history
# Navigate to AlertManager: https://app.neurex.ai/alertmanager

# Review deployment history
helm history neurex -n neurex-production
```

### Monthly Tasks
```bash
# Review cost metrics
kubectl top nodes
kubectl top pods -n neurex-production

# Review backup retention
du -sh /backups

# Plan auto-scaling adjustments if needed
```

---

## 7. Common Troubleshooting

### Pod not starting?
```bash
# Check pod events
kubectl describe pod POD_NAME -n neurex-production

# Check logs
kubectl logs POD_NAME -n neurex-production --previous

# Check resource constraints
kubectl top pod POD_NAME -n neurex-production
```

### Database not responding?
```bash
# Check DB pod
kubectl get pod -n neurex-production -l app=postgres

# Check logs
kubectl logs deployment/postgres -n neurex-production

# Test connection from pod
kubectl exec -it deployment/neurex-backend -n neurex-production -- \
  psql -h postgres -U postgres -d neurex -c "SELECT 1"
```

### High latency?
```bash
# Check slow queries
kubectl exec deployment/postgres -n neurex-production -- \
  psql -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10"

# Check cache hit ratio
kubectl exec deployment/redis -n neurex-production -- redis-cli INFO stats

# Check pod resource usage
kubectl top pods -n neurex-production --sort-by=memory
```

### Deployment stuck?
```bash
# Check rollout status
kubectl rollout status deployment/neurex-backend -n neurex-production

# Rollback if needed
kubectl rollout undo deployment/neurex-backend -n neurex-production

# Or via Helm
helm rollback neurex -n neurex-production
```

---

## 8. Environment Variables

Required secrets in Kubernetes:

```bash
kubectl create secret generic neurex-secrets \
  --from-literal=JWT_SECRET=<random-32-chars> \
  --from-literal=POSTGRES_PASSWORD=<strong-password> \
  --from-literal=REDIS_PASSWORD=<random-32-chars> \
  --from-literal=ENGINE_INTERNAL_KEY=<random-32-chars> \
  --from-literal=GATEWAY_INTERNAL_KEY=<random-32-chars> \
  --from-literal=MINIO_ROOT_PASSWORD=<strong-password> \
  -n neurex-production
```

Required GitHub Actions secrets:

```
KUBECONFIG_STAGING       (base64-encoded kubeconfig)
KUBECONFIG_PRODUCTION    (base64-encoded kubeconfig)
HELM_REPO_URL            (Helm chart repository URL)
SLACK_WEBHOOK            (Slack notification webhook)
```

---

## 9. Key Metrics to Monitor

### Availability
- Pod restart count (should be 0)
- Uptime percentage (target: 99.9%)
- Health check pass rate (target: 100%)

### Performance
- Request latency p95/p99 (target: < 500ms/1000ms)
- Error rate (target: < 0.1%)
- Throughput (req/sec)

### Resource Utilization
- CPU usage per pod (target: 50-75%)
- Memory usage per pod (target: 60-80%)
- Disk I/O (should be low)

### Infrastructure
- Node count (should match HPA requirements)
- PVC usage (should have headroom)
- Network latency (< 10ms intra-cluster)

---

## 10. Contact & Support

### Documentation
- **Full Guide:** `docs/DEVOPS_INFRASTRUCTURE_GUIDE.md`
- **All Fixes:** `docs/DEVOPS_60_FIXES_SUMMARY.md`
- **Troubleshooting:** See section 7 above

### Emergency Contacts
- **On-Call:** Rotating daily (see team calendar)
- **Escalation:** DevOps Lead > VP Engineering
- **Critical Issues:** #incident-response Slack channel

### Learning Resources
- Kubernetes: https://kubernetes.io/docs/
- Helm: https://helm.sh/docs/
- Prometheus: https://prometheus.io/docs/
- Docker: https://docs.docker.com/

---

**Last Updated:** 2026-06-09  
**Maintained By:** DevOps Team  
**Status:** ✅ Production-Ready
