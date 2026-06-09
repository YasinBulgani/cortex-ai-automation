# CI/CD Test Automation Quick Reference

## GitHub Actions Workflow

**File**: `.github/workflows/test-automation.yml`

### Triggers
- Push to: `main`, `develop`, `feature/qa-system-bootstrap`
- Pull Requests to: `main`, `develop`
- Path filters: `backend/`, `apps/web/`, `e2e/`, `engine/`

### Pipeline Stages

| Stage | Duration | Tests | Artifacts |
|-------|----------|-------|-----------|
| Unit Tests | 3 min | pytest (Backend + Engine) | coverage.xml |
| API Tests | 5 min | contract + integration | JUnit XML |
| Frontend | 5 min | TypeScript + ESLint + Jest | coverage/ |
| E2E Tests | 10 min | Playwright (2 shards) | HTML report + XML |
| Smoke Tests | 3 min | Quick sanity (PR only) | - |
| Summary | 2 min | Slack notification | - |

**Total**: ~15-20 minutes (E2E parallel with others)

## Local Execution

### Quick Tests

```bash
# Unit tests only
make test-unit-ci

# API tests (requires running backend)
make test-api-ci

# Frontend tests
make test-ui-ci

# Smoke tests
make test-smoke-ci

# All tests
make test-automation
```

### Full Setup

```bash
# Start infrastructure
make docker-up

# Start backend (terminal 1)
cd backend && python -m uvicorn app.main:app --port 8000

# Start frontend (terminal 2)
cd apps/web && npm run dev

# Run tests (terminal 3)
make test-automation
```

## Test Markers

Use these pytest markers to categorize tests:

```python
@pytest.mark.smoke        # Quick sanity (included in PR checks)
@pytest.mark.ai           # Requires LLM (skipped in CI)
@pytest.mark.slow         # Long-running (skipped in CI)
@pytest.mark.requires_db  # Requires Postgres (skipped in unit)
@pytest.mark.requires_redis  # Requires Redis (skipped in unit)
```

### Marker Usage

```python
import pytest

@pytest.mark.smoke
def test_login_flow():
    """Smoke test - quick feedback"""
    assert True

@pytest.mark.ai
@pytest.mark.slow
def test_ai_generation():
    """Requires LLM and takes time - skip in CI"""
    assert True
```

## Coverage Requirements

**Minimum**: 70% line coverage (backend unit tests)

Check coverage locally:

```bash
cd backend && python -m pytest tests/unit/ \
  --cov=app \
  --cov-report=html:../reports/coverage \
  --cov-report=term-missing
```

View the HTML report:

```bash
open reports/coverage/index.html  # macOS
xdg-open reports/coverage/index.html  # Linux
```

## Slack Notifications

### Setup
1. Create Slack app at [api.slack.com](https://api.slack.com)
2. Enable Incoming Webhooks
3. Add webhook URL as GitHub secret: `SLACK_WEBHOOK_URL`

See `.github/SLACK_SETUP_GUIDE.md` for detailed instructions.

### Example Notification

```
🔴 Test Pipeline Failed

Branch: feature/qa-system-bootstrap
Commit: a1b2c3d...
Author: @developer

Unit Tests: ✓ pass
API Tests: ✓ pass
Frontend Tests: ✗ fail (ESLint)
E2E Tests: ⏳ skipped

[View Run]
```

## GitHub Actions Secrets

Add these repository secrets:

| Secret | Value | Required |
|--------|-------|----------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook | Yes |
| `SENTRY_DSN` | Sentry error tracking | Optional |
| `CODECOV_TOKEN` | Code coverage upload | Optional |

**Location**: Repository → Settings → Secrets and variables → Actions

## Artifact Retention

| Artifact | Retention | Location |
|----------|-----------|----------|
| Coverage (Backend) | 14 days | `backend/coverage.xml` |
| Coverage (Jest) | 14 days | `apps/web/coverage/` |
| Playwright Report | 14 days | `playwright-report/` |
| Test Results (XML) | 14 days | `test-results/` |

Download from: Actions → Workflow Run → Artifacts

## Common Issues

### Timeout: "Frontend not ready"
```
Error: Timeout waiting for frontend on port 3000
```

**Fix**: Check Next.js build
```bash
cd apps/web && npm run build
```

### Timeout: "Database connection refused"
```
postgresql://postgres:postgres@localhost:5432/test_db: connection refused
```

**Fix**: Ensure PostgreSQL service is healthy
```bash
docker ps -a | grep postgres
docker logs <postgres-container>
```

### Flaky E2E Tests
- Reduce parallel shards: `--shard=1/1`
- Increase timeout: `--timeout=60s`
- Add explicit waits instead of sleeps

### Slack notification not received
1. Verify `SLACK_WEBHOOK_URL` secret exists
2. Test webhook manually:
   ```bash
   curl -X POST "$WEBHOOK_URL" \
     -H 'Content-Type: application/json' \
     -d '{"text":"Test"}'
   ```
3. Check channel has the Slack app added

## Viewing Results

### GitHub Actions UI
1. Go to **Actions** tab
2. Select **Test Automation Pipeline**
3. Click the workflow run
4. View logs and artifacts

### Local HTML Reports

```bash
# Open Playwright report
open playwright-report/index.html

# Open Jest coverage
open apps/web/coverage/index.html

# Open Backend coverage
open reports/backend-coverage/index.html
```

## Advanced Customization

### Skip Workflow for Certain Commits

In commit message:
```
git commit -m "docs: update README [skip ci]"
```

### Run Specific Job Only

Edit `.github/workflows/test-automation.yml` temporarily:

```yaml
on:
  push:
    branches: [main]
  
# Or trigger manually via GitHub UI
```

### Increase Test Timeouts

In `.github/workflows/test-automation.yml`:

```yaml
jobs:
  e2e-tests:
    timeout-minutes: 30  # Increase from 25
```

## Performance Tips

1. **Use caching**:
   ```yaml
   - uses: actions/cache@v4
     with:
       path: ~/.npm
       key: npm-${{ hashFiles('package-lock.json') }}
   ```

2. **Parallel jobs**: E2E tests already use 2 shards
   - Add more shards: `matrix: { shard: [1, 2, 3, 4] }`

3. **Fail fast**: Set in job
   ```yaml
   strategy:
     fail-fast: true
   ```

4. **Conditional steps**:
   ```yaml
   - name: Run slow tests
     if: github.ref == 'refs/heads/main'
   ```

## Integration with Other Tools

### Code Coverage Upload to Codecov

```yaml
- uses: codecov/codecov-action@v3
  with:
    files: ./backend/coverage.xml
```

### Upload to S3

```yaml
- name: Upload reports to S3
  run: |
    aws s3 cp reports/ s3://bucket-name/ --recursive
```

### Merge Artifacts

```bash
# After test runs, merge Playwright shards
npx playwright merge-reports ./test-results
```

## Monitoring Dashboard

Create a GitHub Actions dashboard to monitor:

1. **Run duration trends** → Identify performance regressions
2. **Failure rates** → Track flakiness
3. **Coverage trends** → Monitor code quality
4. **Job timing** → Optimize bottlenecks

Use GitHub GraphQL API:

```graphql
query {
  repository(owner: "org", name: "repo") {
    workflowRuns(first: 10, name: "Test Automation Pipeline") {
      edges {
        node {
          name
          status
          conclusion
          durationMinutes
          createdAt
        }
      }
    }
  }
}
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/)
- [jest Documentation](https://jestjs.io/)
- [Slack Webhooks](https://api.slack.com/messaging/webhooks)

---

**Updated**: 2026-06-09
**Status**: Production
**Owner**: Cortex AI Team
