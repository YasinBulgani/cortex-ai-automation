# CI/CD Test Automation Reference

## Quick Commands

```bash
# Run full test pipeline
make test-automation

# Run individual stages
make test-unit-ci        # Backend + Engine unit tests
make test-api-ci         # API contract + integration
make test-ui-ci          # Frontend TypeScript + ESLint + Jest + E2E
make test-smoke-ci       # Quick sanity check
```

## Pipeline Overview

| Stage | Time | Tests | Status |
|-------|------|-------|--------|
| Unit | 3 min | Backend pytest + Engine tests | REQUIRED |
| API | 5 min | Contract + Integration | REQUIRED |
| Frontend | 5 min | TypeScript + ESLint + Jest | REQUIRED |
| E2E | 10 min | Playwright (2 shards) | REQUIRED |
| Smoke | 3 min | Quick checks (PR only) | OPTIONAL |

## Local Setup

```bash
# Start services
make docker-up

# Terminal 1: Backend
cd backend && python -m uvicorn app.main:app --port 8000

# Terminal 2: Frontend
cd apps/web && npm run dev

# Terminal 3: Tests
make test-automation
```

## Coverage Requirements

- **Backend**: Minimum 70% line coverage
- Check locally: `cd backend && python -m pytest tests/unit/ --cov=app --cov-report=term-missing`

## Test Markers

```python
@pytest.mark.smoke              # Fast sanity check
@pytest.mark.ai                 # Requires LLM (skip in CI)
@pytest.mark.slow               # Long-running (skip in CI)
@pytest.mark.requires_db        # Needs Postgres (skip in unit)
@pytest.mark.requires_redis     # Needs Redis (skip in unit)
```

## GitHub Secrets

Required:
- `SLACK_WEBHOOK_URL`: Slack incoming webhook for notifications

Optional:
- `SENTRY_DSN`: Error tracking
- `CODECOV_TOKEN`: Coverage upload

## Common Issues

### "Backend not ready"
```bash
# Check backend health
curl http://localhost:8000/health
```

### "Coverage < 70%"
```bash
# See missing coverage
cd backend && python -m pytest tests/unit/ \
  --cov=app \
  --cov-report=term-missing
```

### "Playwright timeout"
- Increase timeout in workflow file
- Check Node.js version (need 20+)

## Files

- `.github/workflows/test-automation.yml` - Main workflow
- `.github/SLACK_SETUP_GUIDE.md` - Slack configuration
- `Makefile` - Local test commands

---

**Last Updated**: 2026-06-09
