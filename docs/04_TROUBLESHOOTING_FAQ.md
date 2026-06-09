# Neurex Troubleshooting Guide & FAQ

**Last Updated:** 2026-06-09  
**Purpose:** Self-serve troubleshooting for common issues  
**Status:** Comprehensive (30+ scenarios)

---

## Table of Contents

1. [Startup Issues](#startup-issues)
2. [Database Issues](#database-issues)
3. [API & Authentication](#api--authentication)
4. [Performance & Timeouts](#performance--timeouts)
5. [Test Execution Issues](#test-execution-issues)
6. [AI Gateway Issues](#ai-gateway-issues)
7. [Webhook & Integration Issues](#webhook--integration-issues)
8. [Container & Docker Issues](#container--docker-issues)
9. [Memory & Resource Issues](#memory--resource-issues)
10. [Error Code Reference](#error-code-reference)

---

## Startup Issues

### Backend Container Fails to Start

**Symptom:**
```
neurex_backend exited with code 1
```

**Solution:**

```bash
# 1. Check logs
docker compose logs backend

# Look for common errors:

# A. Missing environment variables
# Error: "JWT_SECRET env var not found"
# Fix: Set JWT_SECRET in .env file
# export JWT_SECRET=$(openssl rand -base64 64)

# B. Database connection refused
# Error: "postgresql://neurex_user:***@postgres:5432/syndata_db"
# Fix: Ensure postgres service is running
docker compose up postgres -d
docker compose exec postgres pg_isready

# C. Invalid DATABASE_URL format
# Error: "Invalid connection string"
# Example formats:
# postgresql://user:pass@host:5432/dbname        (psycopg2)
# postgresql+asyncpg://user:pass@host:5432/dbname (async)

# D. Redis not available
# Error: "Redis connection refused on 6379"
# Fix: Start Redis
docker compose up redis -d

# 2. Full restart
docker compose down -v  # Remove volumes (clean state)
docker compose up -d postgres redis
docker compose up -d backend

# 3. Check health
curl http://localhost:8000/health
```

---

### Frontend Won't Load

**Symptom:** Blank screen, console errors

**Solution:**

```bash
# 1. Check frontend is running
docker compose logs frontend

# 2. Verify API proxy configuration
# Check next.config.mjs for rewrites:
grep -A 5 "rewrites" next.config.mjs

# 3. Clear Next.js cache
docker compose exec frontend rm -rf .next
docker compose down
docker compose up frontend -d

# 4. Check network connectivity
docker network ls
docker network inspect neurex_default  # Verify services connected

# 5. Test API connectivity from frontend container
docker compose exec frontend curl -I http://backend:8000/health
```

---

### Migrations Fail on Startup

**Symptom:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'head'
```

**Solution:**

```bash
# 1. Check migration status
docker compose exec backend alembic current
docker compose exec backend alembic history

# 2. If HEAD is missing or corrupted
# Reset to known good state
docker compose exec backend alembic downgrade base
docker compose exec backend alembic upgrade head

# 3. If specific migration fails
# Identify which migration:
docker compose logs backend | grep "FAILED"

# Skip it (after investigation)
docker compose exec backend alembic upgrade +1

# 4. Verify schema after migration
docker compose exec backend python -c "
  from app.infra.models import Base
  print('Models loaded successfully')
"
```

---

## Database Issues

### Slow Query Performance

**Symptom:** API requests hang, database CPU at 100%

**Solution:**

```bash
# 1. Check for slow queries
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT query, calls, mean_time, max_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# 2. Identify missing indexes
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT schemaname, tablename, indexname
  FROM pg_indexes
  WHERE schemaname = 'public'
  ORDER BY tablename;
"

# 3. Check table statistics
VACUUM ANALYZE;

# 4. Monitor real-time queries
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT pid, usename, application_name, query, query_start
  FROM pg_stat_activity
  WHERE state = 'active'
  ORDER BY query_start;
"

# 5. Kill long-running queries (if needed)
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE query_start < NOW() - INTERVAL '10 minutes';
"

# 6. Connection pool exhaustion
# Check max connections
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT count(*) FROM pg_stat_activity;
"
# If maxed out, increase pool in backend app/infra/database.py
```

---

### "ERROR: duplicate key value violates unique constraint"

**Symptom:**
```
IntegrityError: duplicate key value violates unique constraint
```

**Common Causes:**

```bash
# 1. Unique constraint violation
# Example: Duplicate email in users table
# Error: "duplicate key value violates unique constraint "
#        "idx_users_tenant_email""

# Fix: Check for duplicates
SELECT email, COUNT(*) as count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

# Remove duplicates (keep latest)
DELETE FROM users
WHERE id NOT IN (
  SELECT MAX(id)
  FROM users
  GROUP BY email
);

# 2. User signup during RLS context mismatch
# During signup, tenant_id not set correctly
# Check app/domains/auth/service.py line ~150
# Ensure: user.tenant_id = str(organization_id)

# 3. Webhook event idempotency
# Webhook fired twice
# Check webhook_logs for duplicates
SELECT url, event_type, COUNT(*)
FROM webhook_logs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY url, event_type
HAVING COUNT(*) > 1;
```

---

### "ERROR: current transaction is aborted"

**Symptom:**
```
InternalServerError: current transaction is aborted
```

**Solution:**

```bash
# 1. Previous query in transaction failed
# The entire transaction is now invalid
# Backend usually rolls back automatically

# 2. Check for constraint violations
# The failed query violated a constraint
# Look in logs:
docker compose logs backend | grep "constraint\|violates"

# 3. If stuck, reset connections
docker compose restart backend

# 4. Verify database consistency
docker compose exec postgres psql -U neurex_user syndata_db -c "
  REINDEX DATABASE syndata_db;
  VACUUM FULL ANALYZE;
"
```

---

### Connection Pool Exhaustion

**Symptom:**
```
QueuePool limit exceeded. Request queue size reached 10
```

**Solution:**

```bash
# 1. Identify connection hogs
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT application_name, COUNT(*) as connections
  FROM pg_stat_activity
  GROUP BY application_name
  ORDER BY connections DESC;
"

# 2. Check for idle connections
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT * FROM pg_stat_activity
  WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '5 minutes';
"

# 3. Terminate idle connections
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '5 minutes';
"

# 4. Increase pool size (backend/app/infra/database.py)
# sqlalchemy.pool.QueuePool(
#    pool_size=20,  # Increase from default 10
#    max_overflow=40
# )

# 5. Restart backend service
docker compose restart backend
```

---

## API & Authentication

### "401 Unauthorized — Invalid token"

**Symptom:**
```json
{
  "detail": "Invalid authentication credentials",
  "error_code": "AUTHENTICATION_FAILED"
}
```

**Solution:**

```bash
# 1. Token is expired
# Access tokens expire after 30 minutes
# Solution: Call /auth/refresh with refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer $REFRESH_TOKEN"

# 2. Token format incorrect
# Must be: Authorization: Bearer <token>
# (not: Authorization: <token>)

# 3. JWT_SECRET mismatch
# Backend JWT_SECRET changed after token generation
# Solution: Re-login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password"
  }' | jq '.access_token'

# 4. Decode token to debug
# Install: pip install pyjwt
python -c "
  import jwt
  import sys
  token = '$ACCESS_TOKEN'
  try:
    payload = jwt.decode(token, options={'verify_signature': False})
    print('Payload:', payload)
    print('Sub:', payload.get('sub'))
    print('Org:', payload.get('org'))
  except Exception as e:
    print('Error:', e)
"

# 5. Check token expiration
python -c "
  import jwt
  from datetime import datetime
  token = '$ACCESS_TOKEN'
  payload = jwt.decode(token, options={'verify_signature': False})
  exp = datetime.fromtimestamp(payload['exp'])
  print(f'Token expires at {exp}')
  print(f'Is expired: {exp < datetime.utcnow()}')
"
```

---

### "403 Forbidden — Permission Denied"

**Symptom:**
```json
{
  "detail": "Insufficient permissions",
  "error_code": "PERMISSION_DENIED"
}
```

**Solution:**

```bash
# 1. Check user role
docker compose exec backend python -c "
  from sqlalchemy import text
  from app.infra.database import AsyncSessionLocal
  
  async def check_role():
    async with AsyncSessionLocal() as session:
      result = await session.execute(
        text('SELECT role, permissions FROM users WHERE id = :uid'),
        {'uid': 'user-uuid-here'}
      )
      print(result.fetchone())
  
  import asyncio
  asyncio.run(check_role())
"

# 2. Check if user is deleted/inactive
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT id, email, is_active, deleted_at
  FROM users
  WHERE email = 'user@example.com';
"

# 3. Verify RLS context
# User must be in the same tenant as the resource
# Check that all IDs match:
SELECT DISTINCT tenant_id FROM test_cases WHERE id = 'case-id';
SELECT tenant_id FROM users WHERE id = 'user-id';
# They must match!

# 4. Check specific permission requirement
# Look at endpoint in backend code
grep -r "require_permission" backend/app/domains/<domain>/router.py
# Then check user's role has that permission
```

---

### "422 Unprocessable Entity — Validation Error"

**Symptom:**
```json
{
  "detail": [
    {
      "loc": ["body", "priority"],
      "msg": "value is not a valid enumeration member; permitted: 'critical', 'high', 'medium', 'low'",
      "type": "type_error.enum"
    }
  ]
}
```

**Solution:**

```bash
# 1. Check enum values
# Error says priority must be one of: critical, high, medium, low
# You sent: CRITICAL (uppercase)
# Fix: Use lowercase

curl -X POST http://localhost:8000/api/v1/test-cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test",
    "priority": "critical"  # <- lowercase!
  }'

# 2. Check required fields
# Error: "field required"
# Check schema in backend/app/domains/<domain>/schemas.py
# Add missing required fields

# 3. Type mismatch
# Error: "value is not a valid integer"
# You sent string instead of int
# Fix: Use correct type

# 4. Validate request before sending
python -c "
  import requests
  import json
  
  payload = {
    'title': 'Test',
    'priority': 'invalid'  # <- Will fail
  }
  
  response = requests.post(
    'http://localhost:8000/api/v1/test-cases',
    json=payload,
    headers={'Authorization': f'Bearer {token}'}
  )
  print(json.dumps(response.json(), indent=2))
"
```

---

## Performance & Timeouts

### Requests Timing Out

**Symptom:** Request takes > 30 seconds

**Solution:**

```bash
# 1. Check database performance
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT query, mean_time, calls
  FROM pg_stat_statements
  WHERE query LIKE '%test_cases%'
  ORDER BY mean_time DESC;
"

# 2. Check Redis connectivity
docker compose exec backend redis-cli -u redis://localhost:6379 PING

# 3. Check AI Gateway responsiveness
curl -m 5 http://ai-gateway:8080/health

# 4. Monitor request in real-time
# In one terminal, stream logs
docker compose logs -f backend

# In another, make request
curl -X GET 'http://localhost:8000/api/v1/test-cases?limit=100' \
  -H "Authorization: Bearer $TOKEN"

# 5. Check application-level timeouts
# backend/app/config.py
grep -n "timeout\|deadline" backend/app/config.py

# Increase if needed:
# QUERY_DEADLINE_SECONDS = 30  (increase to 60)
```

---

### High Memory Usage

**Symptom:** Container runs out of memory

**Solution:**

```bash
# 1. Check memory usage
docker stats neurex_backend

# If memory grows unbounded:
# Likely memory leak in:
# - SQLAlchemy session not closed
# - Cache not evicting old data
# - Thread leak in thread pool

# 2. Identify memory leaks
docker compose exec backend python -c "
  import tracemalloc
  tracemalloc.start()
  
  # Run suspicious code here
  from app.domains.test_management import service
  
  current, peak = tracemalloc.get_traced_memory()
  print(f'Current: {current / 1024 / 1024:.2f}MB')
  print(f'Peak: {peak / 1024 / 1024:.2f}MB')
"

# 3. Increase memory limit
docker compose.yml:
# services:
#   backend:
#     deploy:
#       resources:
#         limits:
#           memory: 4G  # Increase from 2G
```

---

### AI Gateway Timeouts

**Symptom:**
```json
{
  "error": "timeout",
  "detail": "AI Gateway did not respond within 30s"
}
```

**Solution:**

```bash
# 1. Check AI Gateway health
curl http://ai-gateway:8080/health

# 2. Check if Ollama is running
curl http://host.docker.internal:11434/api/tags

# 3. Check active requests
docker logs ai-gateway | grep "request\|error" | tail -20

# 4. Increase timeout in config
backend/app/config.py:
# AI_GATEWAY_TIMEOUT_SECONDS = 60  (increase from 30)

# 5. Check model availability
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5:14b",
    "prompt": "test"
  }'

# If model not found, pull it:
ollama pull qwen2.5:14b
```

---

## Test Execution Issues

### Test Run Stuck in "Running" State

**Symptom:**
```
Test run shows "running" for > 2 hours
```

**Solution:**

```bash
# 1. Check if process actually running
docker compose exec backend python -c "
  from sqlalchemy import text
  from app.infra.database import AsyncSessionLocal
  
  async def check_run():
    async with AsyncSessionLocal() as session:
      result = await session.execute(
        text('SELECT id, status, started_at FROM test_runs WHERE status = :st'),
        {'st': 'running'}
      )
      for row in result:
        print(f'Run {row.id}: {row.status} since {row.started_at}')
  
  import asyncio
  asyncio.run(check_run())
"

# 2. Check RQ job status (if using RQ for execution)
docker compose exec redis redis-cli -a neurex_dev_redis_2026 \
  HGETALL "rq:job:job-id-here"

# 3. Force completion
docker compose exec backend python -c "
  from sqlalchemy import text, update
  from app.infra.models import TestRun
  from app.infra.database import AsyncSessionLocal
  from datetime import datetime
  
  async def mark_complete():
    async with AsyncSessionLocal() as session:
      await session.execute(
        update(TestRun)
        .where(TestRun.id == 'run-id-here')
        .values(
          status='completed',
          completed_at=datetime.utcnow()
        )
      )
      await session.commit()
  
  import asyncio
  asyncio.run(mark_complete())
"

# 4. Check engine logs (if using engine)
docker compose logs engine | grep "run-id-here" | tail -50
```

---

### Test Results Show 0% Pass Rate

**Symptom:**
```
Run Summary: 0/100 passed (0%)
```

**Solution:**

```bash
# 1. Check test run results
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT test_case_id, status, error_message
  FROM test_run_results
  WHERE test_run_id = 'run-id-here'
  LIMIT 5;
"

# 2. Common error: All tests marked as failed
# Check error_message column
# Likely errors:
# - "Test agent not found"
# - "Timeout waiting for agent"
# - "Locator mismatch"

# 3. If agent issue:
curl http://localhost:8000/api/v1/agents | jq '.data[] | {id, status}'

# 4. If locator issue:
# Check app/domains/agents/service.py
# Locator strategy might not match target app

# 5. If timeout:
# Increase execution timeout
# backend/app/config.py:
# TEST_EXECUTION_TIMEOUT_SECONDS = 120  (increase from 60)
```

---

## AI Gateway Issues

### AI Gateway Connection Refused

**Symptom:**
```
ConnectionError: [Errno 111] Connection refused (ai-gateway:8080)
```

**Solution:**

```bash
# 1. Check if service is running
docker compose ps ai-gateway

# 2. Verify network connectivity
docker compose exec backend \
  ping -c 3 ai-gateway

# 3. Check logs
docker compose logs ai-gateway

# 4. Restart AI Gateway
docker compose restart ai-gateway

# 5. If not in docker-compose.yml, add it
# See: docker-compose.yml services.ai-gateway section
# Should be built from: ai-gateway/Dockerfile
```

---

### "Invalid LLM response" / Structured Output Failed

**Symptom:**
```json
{
  "error": "ai_error",
  "detail": "LLM response did not match expected schema"
}
```

**Solution:**

```bash
# 1. Check which provider returned invalid response
docker compose logs ai-gateway | grep "response\|error" | tail -10

# 2. Test provider directly
curl -X POST http://ai-gateway:8080/v1/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Generate a test case",
    "model": "qwen2.5:14b",
    "temperature": 0.7
  }'

# 3. Check Ollama model quality
ollama pull qwen2.5:14b
ollama list  # Verify model present

# 4. Reduce structured output requirements
# If using task_type=ANALYST, response schema might be too strict
# backend/app/domains/ai/schemas.py
# Reduce number of required fields

# 5. Add response fallback
backend/app/config.py:
# AI_STRUCTURED_OUTPUT_FAIL_CLOSED = False
# (allows returning unstructured response on schema failure)
```

---

## Webhook & Integration Issues

### Webhook Delivery Failed

**Symptom:**
```json
{
  "status": "failed",
  "http_status": 404,
  "error": "Not found"
}
```

**Solution:**

```bash
# 1. Check webhook URL is reachable
curl -X POST https://your-domain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# 2. Check webhook logs
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT webhook_id, event_type, response_status, error_message
  FROM webhook_logs
  WHERE webhook_id = 'webhook-id-here'
  ORDER BY delivered_at DESC
  LIMIT 5;
"

# 3. Verify webhook secret
# Neurex signs webhook with HMAC-SHA256
# Check signature in webhook header: X-Webhook-Signature
python -c "
  import hmac
  import hashlib
  
  secret = 'your-webhook-secret'
  payload = '{...}'
  
  expected_sig = hmac.new(
    secret.encode(),
    payload.encode(),
    hashlib.sha256
  ).hexdigest()
  
  print(f'Expected: {expected_sig}')
  print(f'Received: {received_sig}')
"

# 4. If endpoint returns auth error
# Check webhook secret matches
curl http://localhost:8000/api/v1/webhooks/webhook-id-here \
  -H "Authorization: Bearer $TOKEN" | jq '.secret'

# 5. Retry failed webhooks
curl -X POST http://localhost:8000/api/v1/webhooks/webhook-id-here/retry \
  -H "Authorization: Bearer $TOKEN"
```

---

### Jira Sync Not Working

**Symptom:**
```
Defect not synced to Jira
```

**Solution:**

```bash
# 1. Check Jira integration exists
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT id, jira_instance_url, jira_project_key, sync_enabled
  FROM jira_integrations
  WHERE project_id = 'project-id-here';
"

# 2. Test Jira API key
curl -X GET https://your-instance.atlassian.net/rest/api/3/project \
  -u "email@example.com:api-key"

# 3. Check sync logs
docker compose logs backend | grep -i jira

# 4. Verify webhook from Jira
# Jira should POST to: /api/v1/jira/webhook
# Check if request was received:
docker compose exec postgres psql -U neurex_user syndata_db -c "
  SELECT * FROM webhook_logs
  WHERE event_type LIKE 'jira%'
  ORDER BY delivered_at DESC
  LIMIT 5;
"

# 5. Manually trigger sync
curl -X POST http://localhost:8000/api/v1/jira/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": "proj-123"}'
```

---

## Container & Docker Issues

### "Cannot connect to Docker daemon"

**Symptom:**
```
error during connect: this error may indicate the Docker daemon is not running
```

**Solution:**

```bash
# 1. Start Docker daemon
# macOS
open /Applications/Docker.app

# Linux
sudo systemctl start docker

# 2. Check daemon status
docker ps

# 3. If permission denied
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# 4. Reset Docker (nuclear option)
docker system prune -a --volumes
docker compose build --no-cache
```

---

### Out of Disk Space

**Symptom:**
```
docker: Error response from daemon: mkdir /var/lib/docker/overlay2: no space left on device
```

**Solution:**

```bash
# 1. Check disk usage
df -h

# 2. Clean up Docker artifacts
docker system prune -a --volumes
# Removes: stopped containers, dangling images, volumes

# 3. Check image sizes
docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}"

# 4. Remove large images
docker rmi neurex/backend:old-version

# 5. Check Docker data directory
du -sh /var/lib/docker/

# 6. Move Docker data to larger disk (if available)
# Stop Docker, move /var/lib/docker to new location
# See: https://docs.docker.com/config/daemon/
```

---

## Memory & Resource Issues

### "Cannot allocate memory" Errors

**Symptom:**
```
PostgreSQL: ERROR: cannot allocate memory
```

**Solution:**

```bash
# 1. Check system memory
free -h

# 2. Check swap usage
swapon --show

# 3. Increase Docker memory limit
# Docker Desktop: Preferences → Resources → Memory
# Set to 8GB if available

# 4. Reduce PostgreSQL buffer pool
docker compose.yml:
# environment:
#   POSTGRES_INIT_ARGS: "-c shared_buffers=256MB"

# 5. Limit backend memory
docker compose.yml:
# services:
#   backend:
#     deploy:
#       resources:
#         limits:
#           memory: 2G
#         reservations:
#           memory: 1G
```

---

### "Cannot kill running container" on Windows

**Symptom:**
```
Error response from daemon: Cannot kill container: OCI runtime error
```

**Solution:**

```bash
# 1. Force stop
docker stop -t 0 container-name

# 2. Remove
docker rm -f container-name

# 3. Reset Docker daemon (if stuck)
# Docker Desktop → Troubleshoot → Reset
```

---

## Error Code Reference

### HTTP Status Codes

| Code | Message | Likely Cause | Fix |
|------|---------|--------------|-----|
| 400 | Bad Request | Malformed JSON or invalid parameters | Check request format |
| 401 | Unauthorized | Missing/invalid JWT token | Re-login, refresh token |
| 403 | Forbidden | Insufficient permissions (RBAC) | Verify user role for resource |
| 404 | Not Found | Resource doesn't exist | Check resource ID |
| 409 | Conflict | Duplicate resource (e.g., email) | Use different value |
| 422 | Unprocessable Entity | Schema validation failed | Check enum values, types |
| 429 | Too Many Requests | Rate limit exceeded | Backoff and retry |
| 500 | Internal Server Error | Backend bug | Check logs, contact support |
| 503 | Service Unavailable | Database/Redis down | Restart services |

---

### Application Error Codes

| Code | Message | Cause | Resolution |
|------|---------|-------|------------|
| AUTHENTICATION_FAILED | Invalid credentials | Wrong email/password | Verify credentials |
| PERMISSION_DENIED | Insufficient permissions | User lacks required role | Contact admin for permission |
| RATE_LIMIT_EXCEEDED | Too many requests | Rate limit hit | Backoff exponentially |
| VALIDATION_ERROR | Input validation failed | Invalid input format | Check API documentation |
| EXTERNAL_SERVICE_ERROR | External service down | AI Gateway, Jira, etc. | Retry, check service status |
| DATABASE_ERROR | Database operation failed | Connection lost or constraint violation | Retry, check database |
| TENANT_ISOLATION_ERROR | Cross-tenant access attempt | RLS violation | Verify tenant_id |

---

### PostgreSQL Error Codes

| Code | Error | Cause | Fix |
|------|-------|-------|-----|
| 23505 | unique_violation | Duplicate key | Check for duplicates, use ON CONFLICT |
| 23503 | foreign_key_violation | Invalid foreign key reference | Verify referenced row exists |
| 23502 | not_null_violation | NULL value in NOT NULL column | Provide required field |
| 57014 | query_canceled | Query timeout | Increase timeout, optimize query |
| 08006 | connection_failure | Connection dropped | Restart service, check network |

---

## Support Escalation

### When to Contact Support

**Scope of this guide:** 95% of common issues

**When to escalate:**
1. Issue not found in troubleshooting guide
2. Multiple services failing simultaneously
3. Data corruption suspected
4. Security incident
5. Custom integration not working

### Escalation Process

```bash
# 1. Gather diagnostic info
mkdir neurex-diagnostics
cd neurex-diagnostics

# Container status
docker compose ps > container-status.txt

# Recent logs (all services)
docker compose logs --tail=1000 > logs.txt

# Database schema
docker compose exec postgres pg_dump -s neurex_db > schema.sql

# Configuration (sanitized)
env | grep -v PASSWORD | grep -v SECRET | grep -v KEY > env.txt

# Create support ticket with these files
```

### Contact

- **Documentation:** https://docs.neurex.ai
- **Issues:** https://github.com/neurex/neurex/issues
- **Email:** support@neurex.ai
- **Slack:** #support (workspace members)

---

**End of Troubleshooting Guide**
