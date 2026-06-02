# Incident Response Runbook

**Maintainer:** Platform Team  
**Last Updated:** 2026-05-27  
**Applies to:** Neurex QA Platform (backend, engine, frontend, infrastructure)

---

## 1. Severity Levels

| Level | Name | Description | Response Time | Example |
|-------|------|-------------|---------------|---------|
| **P0** | Complete Outage | System is entirely unavailable; no users can access the platform | Immediate (< 5 min) | Backend API returns 503 for all requests; database is unreachable |
| **P1** | Critical Degradation | Core functionality is broken for most users; workaround not available | < 15 min | AI test generation fails; engine cannot run tests; login broken |
| **P2** | Partial Issue | A subset of users or features is impacted; workaround may exist | < 1 hour | Single route returns errors; one integration broken; slowness in non-critical flow |
| **P3** | Minor Bug | Cosmetic or low-impact issue; functionality intact | Next business day | UI misalignment; non-critical endpoint returns wrong status code |

---

## 2. First Response Checklist

### Within 5 Minutes
- [ ] Acknowledge the incident in the team channel (`#incidents`)
- [ ] Assign an incident commander (IC) — the first responder owns it until handoff
- [ ] Determine severity level (P0–P3) based on impact scope
- [ ] Check system health endpoints:
  ```bash
  curl http://localhost:8000/api/health       # Backend
  curl http://localhost:5001/health           # Engine
  curl http://localhost:3000/api/health       # Frontend (if applicable)
  ```
- [ ] Run quick container status check:
  ```bash
  docker compose ps
  docker compose logs --tail=50 backend
  docker compose logs --tail=50 engine
  ```
- [ ] If P0 or P1: notify stakeholders immediately

### Within 15 Minutes
- [ ] Identify the failing component (backend / engine / database / redis / frontend)
- [ ] Check recent deployments or config changes:
  ```bash
  git log --oneline -20
  git diff HEAD~1 HEAD -- docker-compose.yml .env
  ```
- [ ] Review error logs for root cause clues:
  ```bash
  docker compose logs --tail=200 backend 2>&1 | grep -i "error\|critical\|exception"
  docker compose logs --tail=200 engine  2>&1 | grep -i "error\|critical\|exception"
  ```
- [ ] If P0: begin rollback evaluation (see Section 4)
- [ ] Update incident channel with preliminary findings

### Within 30 Minutes
- [ ] Apply fix or initiate rollback
- [ ] Verify recovery by re-running health checks and a smoke test suite
- [ ] Confirm no cascading failures in dependent services (redis, postgres, AI gateway)
- [ ] Update status page / stakeholder communication
- [ ] Schedule post-incident review (PIR) if P0 or P1

---

## 3. Common Issues & Fixes

### 3.1 Backend API Down

**Symptoms:** All `/api/*` endpoints return 502/503; frontend shows "Cannot connect to server".

**Diagnosis:**
```bash
docker compose ps                          # Check container state
docker compose logs --tail=100 backend    # Look for startup errors
```

**Fix:**
```bash
# Restart backend container
docker compose restart backend

# If restart fails, rebuild:
docker compose up -d --build backend

# Verify recovery:
curl -s http://localhost:8000/api/health | jq .
```

**Escalate if:** Container crashes in a restart loop (exit code non-zero repeatedly). Check for missing environment variables or broken imports.

---

### 3.2 Database Connection Failed

**Symptoms:** Backend logs show `sqlalchemy.exc.OperationalError: could not connect to server`; health endpoint returns `{"db": "error"}`.

**Diagnosis:**
```bash
docker compose ps postgres                      # Check postgres container status
docker compose logs --tail=50 postgres          # Look for startup or OOM errors
docker compose exec postgres psql -U neurex -c "SELECT 1;"  # Test direct connection
```

**Check connection string:**
```bash
# Verify DATABASE_URL in environment
docker compose exec backend env | grep DATABASE_URL
# Expected: postgresql://neurex:password@postgres:5432/neurex_db
```

**Fix:**
```bash
# Restart postgres (if container is stopped or unhealthy)
docker compose restart postgres

# Wait for healthy state, then restart backend to reconnect
sleep 5 && docker compose restart backend

# Verify:
curl -s http://localhost:8000/api/health | jq .db
```

**Escalate if:** Postgres data directory is corrupted or disk is full (`df -h`).

---

### 3.3 Engine Not Responding

**Symptoms:** AI test generation hangs; backend logs show `ConnectionRefusedError` on port 5001; `/api/engine/health` returns error.

**Diagnosis:**
```bash
docker compose ps engine
docker compose logs --tail=100 engine
curl -s http://localhost:5001/health
```

**Fix:**
```bash
# Restart engine container
docker compose restart engine

# If engine fails to start, check for port conflicts:
lsof -i :5001

# Force recreate if needed:
docker compose up -d --force-recreate engine

# Verify:
curl -s http://localhost:5001/health | jq .
```

**Note:** Engine exposes port `127.0.0.1:5001:5001` — it is only accessible from localhost by design (see `docker-compose.yml`).

---

### 3.4 Redis Unavailable

**Symptoms:** LLM rate limiter errors in logs; session/cache operations fail; backend logs show `redis.exceptions.ConnectionError`.

**Diagnosis:**
```bash
docker compose ps redis
docker compose logs --tail=50 redis
docker compose exec redis redis-cli ping      # Should return PONG
```

**Fix:**
```bash
# Restart redis
docker compose restart redis

# Verify backend reconnects (redis client auto-reconnects on next request):
docker compose logs --tail=20 backend | grep -i redis
```

**Fallback:** The LLM rate limiter (`backend/app/services/llm_gateway.py`) has a fallback path that skips rate limiting when Redis is unavailable. Confirm fallback is active in logs:
```
[WARNING] Redis unavailable — rate limiter operating in bypass mode
```
This is acceptable for short outages (< 5 min). For extended Redis downtime, enforce manual throttling or pause AI generation endpoints.

---

### 3.5 AI Gateway Timeout

**Symptoms:** AI-dependent endpoints (test generation, scenario creation, sifir-bilgi pipeline) time out or return 504; engine logs show `openai.Timeout` or `httpx.ReadTimeout`.

**Diagnosis:**
```bash
# Check API key is set
docker compose exec backend env | grep OPENAI_API_KEY

# Check AI gateway logs
docker compose logs --tail=100 backend | grep -i "openai\|timeout\|gateway"

# Test connectivity to provider
docker compose exec backend curl -s --max-time 5 https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq .error
```

**Fix — Verify API Key:**
```bash
# If key is missing or wrong, update .env and restart backend
# Edit .env: OPENAI_API_KEY=sk-...
docker compose up -d --env-file .env backend
```

**Fix — Try Fallback Provider:**
```bash
# Switch to fallback provider in .env (e.g., Anthropic, Azure OpenAI)
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
docker compose up -d --env-file .env backend
```

**Escalate if:** Provider reports a major outage (check status.openai.com). In this case, disable AI endpoints temporarily and communicate ETA to users.

---

## 4. Rollback Procedure

### 4.1 Code Rollback (Git Revert)

```bash
# Identify the bad commit
git log --oneline -10

# Option A: Revert a specific commit (creates new commit, safe for shared branches)
git revert <commit-sha> --no-edit
git push origin main

# Option B: Reset to last known-good tag (use only on feature branch or after team agreement)
git reset --hard <known-good-tag-or-sha>
git push --force-with-lease origin <branch-name>
```

### 4.2 Container Rollback (Previous Docker Image)

```bash
# Stop current containers
docker compose down

# Edit docker-compose.yml to pin previous image tag
# image: neurex-backend:v0.5.1  (instead of :latest)

# Bring up with pinned image
docker compose up -d

# Verify all services healthy
docker compose ps
```

### 4.3 Database Migration Rollback

```bash
# Check current migration revision
docker compose exec backend alembic current

# Roll back one revision
docker compose exec backend alembic downgrade -1

# Roll back to a specific revision
docker compose exec backend alembic downgrade <revision-id>

# Verify schema is in expected state
docker compose exec backend alembic current
```

**Before rolling back migrations:** Always take a database backup first:
```bash
docker compose exec postgres pg_dump -U neurex neurex_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## 5. Escalation Path

| Condition | Contact | Channel |
|-----------|---------|---------|
| P0 — complete outage | On-call engineer + Team lead | `#incidents` + direct message |
| P0 lasting > 30 min | Engineering manager | Direct call |
| Database corruption / data loss risk | Senior backend engineer + DBA | `#incidents` + direct call |
| Security incident (unauthorized access, data breach) | Security lead + Engineering manager | Separate secure channel |
| AI provider outage (external) | Product manager (for user communication) | `#incidents` |
| P1 — no progress after 1 hour | Team lead | `#incidents` |
| P2/P3 — no progress after 1 business day | Team lead | `#incidents` |

**On-Call Rotation:** Check the shared calendar or PagerDuty for current on-call assignments.

---

## 6. Post-Incident Template

Use this template within 24 hours of resolving a P0 or P1 incident. Post it in `#post-incident-reviews`.

```markdown
## Post-Incident Review — [Short Title]

**Date:** YYYY-MM-DD  
**Severity:** P0 / P1  
**Duration:** HH:MM (detection to resolution)  
**Incident Commander:** [Name]  
**Participants:** [Names]

---

### Summary
One-paragraph plain-language description of what happened and its impact.

---

### Root Cause
The technical root cause of the incident.

Example: A missing index on `test_runs.project_id` caused a full table scan that
locked the database under load after the project count exceeded 500.

---

### Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | Incident detected (monitoring alert / user report) |
| HH:MM | IC assigned; severity declared P0 |
| HH:MM | Root cause identified |
| HH:MM | Fix applied |
| HH:MM | Service restored; monitoring confirmed stable |
| HH:MM | Incident closed |

---

### What Went Well
- …

### What Could Be Improved
- …

---

### Fix Applied
Description of the immediate fix (code change, config update, restart, rollback).

**PR / Commit:** [link]

---

### Prevention Actions

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Add monitoring alert for X | @engineer | YYYY-MM-DD | Open |
| Write regression test for this scenario | @qa | YYYY-MM-DD | Open |
| Document runbook entry for this issue | @ic | YYYY-MM-DD | Open |

---

### Lessons Learned
Key takeaways for the team.
```
