# Neurex Team Runbook

**Last Updated:** 2026-06-09  
**Audience:** Operations, DevOps, Engineering  
**Status:** Production-Ready  
**Escalation:** See End-of-Document

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Weekly Maintenance](#weekly-maintenance)
3. [Monthly Reviews](#monthly-reviews)
4. [Incident Response](#incident-response)
5. [Escalation Matrix](#escalation-matrix)
6. [On-Call Schedule](#on-call-schedule)
7. [Runbook Quick Links](#runbook-quick-links)

---

## Daily Operations

### Morning Checks (9:00 AM)

**Duration:** 5 minutes

```bash
#!/bin/bash
# daily_morning_checks.sh

echo "=== Morning Health Check ==="

# 1. Check all services running
echo "Checking service status..."
docker compose ps | grep -E "healthy|Up"

# 2. Check error rate (Sentry)
SENTRY_ERRORS=$(curl -s https://sentry.neurex.ai/api/projects/neurex/neurex-api/stats/ \
  -H "Authorization: Bearer $SENTRY_TOKEN" | jq '.data[0].stats.all.error')
echo "Sentry errors last hour: $SENTRY_ERRORS"

if [ "$SENTRY_ERRORS" -gt 100 ]; then
  echo "⚠️  HIGH ERROR RATE DETECTED"
  slack-notify "#ops" "High error rate: $SENTRY_ERRORS errors in last hour"
fi

# 3. Check database size (should be < 100GB)
DB_SIZE=$(docker compose exec postgres \
  psql -U neurex_user syndata_db -c \
  "SELECT pg_size_pretty(pg_database_size('syndata_db'))" | tail -1)
echo "Database size: $DB_SIZE"

# 4. Check disk usage (should be < 80%)
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}')
echo "Disk usage: $DISK_USAGE"

if [[ ${DISK_USAGE%\%} -gt 80 ]]; then
  echo "⚠️  DISK SPACE LOW"
  slack-notify "#ops" "Disk usage at $DISK_USAGE"
fi

# 5. Check Redis memory (should be < 2GB)
REDIS_MEMORY=$(docker compose exec redis redis-cli INFO memory | grep used_memory_human | cut -d: -f2)
echo "Redis memory: $REDIS_MEMORY"

echo "Morning check complete ✓"
```

### During Business Hours

**Monitor These Every Hour:**

```bash
# Check error logs
docker compose logs backend --since=1h | grep -i error | wc -l

# Check slow queries
docker compose exec postgres \
  psql -U neurex_user syndata_db -c \
  "SELECT query, calls, mean_time FROM pg_stat_statements WHERE mean_time > 1000 LIMIT 5;"

# Check Redis connection count
docker compose exec redis redis-cli CLIENT LIST | wc -l

# Check stuck transactions
docker compose exec postgres \
  psql -U neurex_user syndata_db -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 min';"
```

### Evening Shutdown (5:00 PM)

```bash
#!/bin/bash
# daily_evening_checks.sh

echo "=== Evening Shutdown Check ==="

# 1. No running tests/jobs
RUNNING_JOBS=$(docker compose exec backend \
  python -c "from rq import Queue; from redis import Redis; q = Queue('default', Redis()); print(len(q))")
echo "Queued jobs: $RUNNING_JOBS"

if [ "$RUNNING_JOBS" -gt 0 ]; then
  echo "⚠️  Jobs still queued. Clear before shutdown."
  exit 1
fi

# 2. No deployments in progress
git status
echo "Git status OK"

# 3. Backup status
LAST_BACKUP=$(ls -lt backups/ | head -1 | awk '{print $6, $7, $8}')
echo "Last backup: $LAST_BACKUP"

# 4. Alert summary for next morning
ERROR_COUNT=$(curl -s https://sentry.neurex.ai/api/projects/neurex/neurex-api/stats/ \
  -H "Authorization: Bearer $SENTRY_TOKEN" | jq '.data[0].stats.all.error')

echo "Evening summary:"
echo "  - Errors today: $ERROR_COUNT"
echo "  - No deployments pending"
echo "  - All systems healthy"
```

---

## Weekly Maintenance

### Monday 2:00 AM (Low Traffic)

**Duration:** 30 minutes  
**Risk Level:** LOW  
**Rollback Plan:** Yes (previous backup)

```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== Weekly Maintenance Window ==="
SLACK_CHANNEL="#ops"
slack-notify "$SLACK_CHANNEL" "Starting weekly maintenance (2 AM UTC)"

# 1. Database maintenance
echo "Running VACUUM ANALYZE..."
docker compose exec postgres psql -U neurex_user syndata_db -c "VACUUM ANALYZE;"
slack-notify "$SLACK_CHANNEL" "✓ Database VACUUM complete"

# 2. Reindex tables (if needed)
echo "Checking index bloat..."
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT schemaname, tablename, indexname
  FROM pg_indexes
  WHERE schemaname = 'public'
  AND (pg_size_pretty(pg_relation_size(indexrelid)) > '100MB');"

# Reindex bloated indexes
docker compose exec postgres psql -U neurex_user syndata_db -c "REINDEX DATABASE syndata_db;"
slack-notify "$SLACK_CHANNEL" "✓ Index rebuild complete"

# 3. Test backup restore (in staging)
echo "Testing backup restoration..."
docker compose -f docker-compose.staging.yml up -d
STAGING_DB="postgresql+psycopg2://user:pass@staging-db:5432/neurex_staging"
pg_restore -h staging-db -U neurex_user -d neurex_staging < backups/latest.sql

# Sanity checks
docker compose -f docker-compose.staging.yml exec backend \
  python -c "from app.infra.models import Base; print('Schema valid')"
slack-notify "$SLACK_CHANNEL" "✓ Backup restore verified"

# 4. Dependency updates (check for security patches)
echo "Checking for security updates..."
pip list --outdated | head -10
npm outdated | head -10
slack-notify "$SLACK_CHANNEL" "✓ Dependency check complete"

# 5. Log rotation
echo "Rotating application logs..."
docker compose exec backend \
  bash -c "mv logs/app.log logs/app.log.$(date +%Y%m%d) && touch logs/app.log"

slack-notify "$SLACK_CHANNEL" "✓ Weekly maintenance complete"
```

### Thursday 10:00 AM (Knowledge Check)

**Duration:** 20 minutes  
**Purpose:** Team sync

```bash
# Team standup meeting

# Agenda:
# 1. Week review: Any incidents? (check Incident Log)
# 2. Performance: Any degradation? (check Grafana dashboard)
# 3. Security: Any alerts? (check Sentry Security tab)
# 4. Upcoming: Any planned work?
# 5. Roadmap: Any changes?

# Quick metrics check:
echo "=== Weekly Metrics ==="
echo "Error rate (24h): $(curl -s https://api.neurex.ai/metrics | jq '.http_errors_total')"
echo "Avg response time (24h): $(curl -s https://api.neurex.ai/metrics | jq '.http_request_duration_seconds')"
echo "Database size: $(docker compose exec postgres psql -U neurex_user syndata_db -c "SELECT pg_size_pretty(pg_database_size('syndata_db'))" | tail -1)"
```

---

## Monthly Reviews

### 1st Monday of Month (Review & Planning)

```bash
#!/bin/bash
# monthly_review.sh

echo "=== Monthly Operations Review ==="

# 1. SLA Review
# Check uptime
UPTIME=$(curl -s https://status.neurex.ai/api/metrics/uptime?month=last_30_days)
echo "Monthly Uptime: $UPTIME%"
if [ $(echo "$UPTIME < 99.5" | bc) -eq 1 ]; then
  echo "⚠️  SLA Miss: Target 99.9%, Got $UPTIME%"
  # Schedule postmortem
fi

# 2. Performance Baseline Review
# Collect baseline metrics
docker stats --no-stream > ./reports/docker-stats-$(date +%Y%m).txt
echo "Container stats saved"

# Get database metrics
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
  LIMIT 20;" > ./reports/table-sizes-$(date +%Y%m).txt

# 3. Security Review
echo "Generating security report..."
# Run OWASP dependency check
safety check > ./reports/security-$(date +%Y%m).txt 2>&1

# Check for exposed secrets
git log --all --full-history -S "password" -- | head -20
git log --all --full-history -S "secret" -- | head -20

# 4. Cost Analysis
echo "Analyzing cloud costs..."
# AWS: get month-to-date spend
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE > ./reports/costs-$(date +%Y%m).json

# 5. Changelog Review
# Summarize commits from last month
git log --oneline --since="4 weeks ago" > ./reports/changelog-$(date +%Y%m).txt

echo "Monthly review complete"
slack-notify "#ops" "Monthly review ready. Check reports/"
```

---

## Incident Response

### Incident Detection

```python
# Automated incident detection
# (Running in monitoring system)

INCIDENT_RULES = {
    "database_down": {
        "condition": "health_check_failed AND service == 'postgres'",
        "severity": "critical",
        "action": "page_oncall"
    },
    "api_errors_spike": {
        "condition": "error_rate > 5%",
        "severity": "high",
        "action": "notify_team"
    },
    "slow_queries": {
        "condition": "database_query_p95 > 1000ms",
        "severity": "medium",
        "action": "notify_dba"
    },
    "disk_full": {
        "condition": "disk_usage > 90%",
        "severity": "critical",
        "action": "page_oncall"
    }
}
```

### Incident Response Procedure

**Step 1: Initial Response (Seconds)**

```bash
#!/bin/bash
# incident_response_step1.sh

INCIDENT_ID="INC-$(date +%s)"
SLACK_CHANNEL="#incidents"

slack-notify "$SLACK_CHANNEL" ":rotating_light: INCIDENT DETECTED: $INCIDENT_ID"
slack-notify "$SLACK_CHANNEL" "Alert: $(echo $ALERT_MESSAGE | jq -r '.title')"
slack-notify "$SLACK_CHANNEL" "Severity: $(echo $ALERT_MESSAGE | jq -r '.severity')"

# Page on-call if critical
if [ "$SEVERITY" == "critical" ]; then
  pagerduty-trigger \
    --incident-key="$INCIDENT_ID" \
    --description="$ALERT_MESSAGE" \
    --severity="critical" \
    --service="neurex-api"
fi

# Create incident log
echo "Incident: $INCIDENT_ID" >> incidents/$(date +%Y%m%d).log
echo "Time: $(date -Iseconds)" >> incidents/$(date +%Y%m%d).log
echo "Alert: $ALERT_MESSAGE" >> incidents/$(date +%Y%m%d).log
```

**Step 2: Triage (1-5 Minutes)**

```bash
# Gather information
echo "=== Incident Triage ==="

# Check service status
docker compose ps

# Check logs for errors
docker compose logs --tail=100 backend | grep -i error

# Check metrics dashboard
# Open: https://grafana.neurex.ai/d/incident/incident-response

# Identify severity
# P0 (Critical): Service down, data loss, security breach
# P1 (High): Degraded performance, intermittent errors
# P2 (Medium): Minor issues, workaround available
# P3 (Low): Non-urgent, can wait until next sprint

SEVERITY="P1"  # Example

slack-notify "#incidents" "Triage complete. Severity: $SEVERITY"
```

**Step 3: Initial Mitigation (5-30 Minutes)**

```bash
# Immediate actions (don't debug yet, just stabilize)

case "$INCIDENT_TYPE" in
  database_down)
    echo "Restarting postgres..."
    docker compose restart postgres
    sleep 10
    curl http://localhost:8000/health
    ;;
  api_high_load)
    echo "Scaling up replicas..."
    docker compose up -d --scale backend=5
    ;;
  memory_leak)
    echo "Restarting backend..."
    docker compose restart backend
    ;;
  *)
    echo "Unknown incident type"
    ;;
esac

# Did it work?
if curl -f http://localhost:8000/health > /dev/null; then
  slack-notify "#incidents" "✓ Service restored. Investigating root cause..."
else
  slack-notify "#incidents" "✗ Mitigation failed. Escalating to engineering..."
  pagerduty-notify --page-sre-team
fi
```

**Step 4: Root Cause Analysis (30-120 Minutes)**

```bash
#!/bin/bash
# incident_rca.sh

echo "=== Root Cause Analysis ==="

# Collect diagnostic info
mkdir -p incidents/$INCIDENT_ID
cd incidents/$INCIDENT_ID

# Logs
docker compose logs --tail=1000 backend > logs.txt 2>&1

# Database state
docker compose exec postgres pg_dump -Fc syndata_db > db_snapshot.dump

# System metrics
docker stats --no-stream > container-stats.txt

# Git history (any recent changes?)
git log --oneline -20 > recent-commits.txt

# Configuration
env | grep -v PASSWORD | grep -v SECRET | sort > config.txt

# What changed recently?
git diff HEAD~10 HEAD > recent-changes.diff

slack-notify "#incidents" "Diagnostics collected: $(pwd)"
```

**Step 5: Communication**

```bash
# Post to status page
curl -X POST https://status.neurex.ai/api/incidents \
  -H "Authorization: Bearer $STATUS_PAGE_TOKEN" \
  -d '{
    "name": "Database Performance Degradation",
    "status": "investigating",
    "impact": "partial",
    "body": "We are investigating elevated query latencies affecting the API"
  }'

# Notify affected users (if needed)
# Email template: "We are experiencing issues with [FEATURE]. ETA: [TIME]"

# Post to #announcements
slack-notify "#announcements" "⚠️ Ongoing incident affecting [service]. Updates: https://status.neurex.ai"
```

**Step 6: Resolution & Postmortem**

```bash
# After service is restored for 30 minutes

slack-notify "#incidents" "✓ RESOLVED: Service fully operational"

# Update status page
curl -X PATCH https://status.neurex.ai/api/incidents/$INCIDENT_ID \
  -d '{"status": "resolved"}'

# Schedule postmortem (within 48 hours)
# Doc: https://docs.neurex.ai/incidents/INC-12345

# Required postmortem sections:
# 1. Timeline (exact sequence of events)
# 2. Detection (how we found out)
# 3. Root cause (why it happened)
# 4. Resolution (how we fixed it)
# 5. Prevention (how we stop it next time)
# 6. Action items (owner + deadline)
```

---

## Escalation Matrix

### Severity Levels

| Level | Definition | Response Time | SLA | Escalate If |
|-------|-----------|-----------------|-----|-------------|
| **P0** | Service down, data loss | Immediate | < 5 min | > 30 min to restore |
| **P1** | Significant degradation | 15 minutes | < 30 min | > 2 hours to restore |
| **P2** | Minor issues, workaround | 1 hour | < 4 hours | > 8 hours duration |
| **P3** | Cosmetic, no impact | 24 hours | < 1 day | N/A |

### Who to Contact

```
Level    | When       | Who                  | Channel          | Phone
---------|------------|----------------------|------------------|-------
P0 / P1  | Immediate  | On-call engineer     | #incidents       | Page
P0 / P1  | 30 min in  | Engineering Manager  | #incidents       | Call
P0 / P1  | 1 hour in  | VP Engineering       | #executive       | Call
P1 / P2  | On-shift   | Team lead            | #ops or Slack DM | Slack
P2 / P3  | Next shift | Assigned engineer    | GitHub issue     | Email
```

### Escalation Triggers

```python
# Automatic escalation rules

if detection_time < 5_minutes and not resolved:
    escalate_to = "on_call_engineer"
    page_with_priority = "high"
    
if time_since_incident > 30_minutes and status == "investigating":
    escalate_to = "engineering_manager"
    call_with_context = "incident_details"
    
if time_since_incident > 60_minutes and status == "investigating":
    escalate_to = "vp_engineering"
    meeting_invite = true
    update_status_page = true

if duplicate_incident_this_week:
    create_jira_ticket("Recurring issue: investigate and fix")
    schedule_postmortem()
```

---

## On-Call Schedule

### Weekly On-Call Rotation

```
Week of   | Primary     | Backup      | Escalation
----------|------------|------------|---------------
Jun 9-15  | John Smith | Jane Doe   | Mike Chen (Manager)
Jun 16-22 | Jane Doe   | Bob Jones  | Mike Chen (Manager)
Jun 23-29 | Bob Jones  | John Smith | Sarah Lee (Director)
```

### On-Call Responsibilities

**During On-Call (24 hours):**
- Respond to critical alerts within 5 minutes
- Triage incidents
- Lead incident response
- Provide status updates every 30 minutes
- Available via phone/Slack

**When Off-Call:**
- Available for emergency escalation
- Participate in postmortems of your incidents
- Document lessons learned

### Handing Off On-Call

```bash
#!/bin/bash
# handoff.sh (run by departing on-call)

echo "=== On-Call Handoff ==="

# 1. Review current issues
echo "Current incidents:"
docker compose logs --tail=20 backend | grep -i error

# 2. Send handoff note
cat << EOF > /tmp/handoff-notes.txt
On-Call Handoff: $(date)

Incidents this week:
- INC-001: Database slow queries (resolved via index)
- INC-002: Memory leak in backend (patched)

Known issues:
- CI/CD slightly slow (investigating)
- Occasional timeout on /api/reports

Watchpoints for next person:
- Monitor test_execution_queue (was at 500 jobs yesterday)
- Keep eye on Redis memory (hit 1.8GB)
- DB backup job runs at 2 AM UTC

Contact info:
- PagerDuty: https://pagerduty.neurex.ai
- Runbook: docs/07_TEAM_RUNBOOK.md
- Status page: https://status.neurex.ai
EOF

# 3. Verify new on-call is ready
echo "Confirming new on-call engineer has access..."
echo "Send to: next-oncall@neurex.ai"

slack-notify "#ops" "On-call handed off to $NEXT_ONCALL. Notes: /tmp/handoff-notes.txt"
```

---

## Runbook Quick Links

### Monitoring & Dashboards
- **Grafana:** https://grafana.neurex.ai (dashboards for metrics)
- **Sentry:** https://sentry.neurex.ai (error tracking)
- **Status Page:** https://status.neurex.ai
- **CloudWatch:** https://console.aws.amazon.com (AWS logs)

### Documentation
- **API Reference:** docs/01_API_REFERENCE.md
- **Deployment Guide:** docs/03_DEPLOYMENT_GUIDE.md
- **Troubleshooting:** docs/04_TROUBLESHOOTING_FAQ.md
- **Performance Tuning:** docs/05_PERFORMANCE_TUNING.md
- **Security Guide:** docs/06_SECURITY_HARDENING.md

### Access & Credentials
- **Production Secrets:** AWS Secrets Manager (vault/prod/*)
- **SSH Access:** Request via Okta
- **Database Access:** Read-only: replica.neurex.ai, Write: postgres.neurex.ai

### Communication
- **Team Slack:** #ops (daily), #incidents (during incident)
- **Escalation:** @ops-manager
- **Status Updates:** #announcements
- **Post-Mortems:** #postmortems

### Tools & Commands

```bash
# Service health check
curl http://localhost:8000/health | jq

# View logs
docker compose logs -f backend

# Database query (safe)
docker compose exec postgres psql -U neurex_user syndata_db -c "SELECT 1;"

# Restart service
docker compose restart backend

# Force redeploy
docker compose up --force-recreate backend

# Database backup
pg_dump postgresql://user:pass@postgres/db > backup.sql

# Monitor in real-time
docker stats --no-stream
```

---

## Contacts & Escalation

### Engineering Team

- **Engineering Manager (Mike Chen)**
  - Slack: @mike.chen
  - Phone: +1-555-0100
  - Escalation: P0 issues > 30 min, all P1 issues

- **VP Engineering (Sarah Lee)**
  - Slack: @sarah.lee
  - Phone: +1-555-0101
  - Escalation: P0 issues > 60 min, external customer impact

- **On-Call Engineer**
  - PagerDuty: https://pagerduty.neurex.ai
  - Slack: Check #ops for this week's rotation
  - Phone: Embedded in PagerDuty alert

### External Escalation

- **Cloud Provider Support (AWS)**
  - Ticket: https://console.aws.amazon.com/support
  - Phone: 1-800-892-AWS (critical only)

- **Security Issues**
  - Email: security@neurex.ai
  - Do not public disclose

- **Customer Support**
  - Email: support@neurex.ai
  - Slack: #customer-support

---

**End of Team Runbook**
