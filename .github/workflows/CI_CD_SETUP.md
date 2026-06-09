# CI/CD Test Automation Pipeline Setup

## Overview

Cortex AI Automation'ın GitHub Actions tabanlı test otomasyonu sistemi.

**Workflow File**: `.github/workflows/test-automation.yml`

## Pipeline Stages

### Stage 1: Unit Tests (3 min)
- Backend: pytest (70% coverage minimum)
- Engine: Flask unit tests
- Services: PostgreSQL + Redis

### Stage 2: API Tests (5 min)
- Contract tests (OpenAPI compliance)
- Integration tests (endpoint functionality)

### Stage 3: Frontend Tests (5 min)
- TypeScript type checking
- ESLint linting
- Jest unit tests
- Next.js build verification

### Stage 4: E2E Tests (10 min)
- Playwright (2 shards parallel)
- Full stack integration

### Stage 5: Test Summary
- Aggregate results
- Slack notifications

## Local Testing

```bash
# Unit tests
make test-unit-ci

# API tests
make test-api-ci

# Frontend + E2E
make test-ui-ci

# Everything
make test-automation
```

## Slack Setup

1. Create Slack app at api.slack.com
2. Enable Incoming Webhooks
3. Add webhook URL to GitHub Secrets as `SLACK_WEBHOOK_URL`

See `.github/SLACK_SETUP_GUIDE.md` for detailed steps.

## Configuration

- **Coverage Threshold**: 70% (backend unit tests)
- **Artifact Retention**: 14 days
- **Concurrency**: Max 4 jobs (E2E shards)
- **Total Time**: ~15-20 minutes

## Troubleshooting

### Test Timeouts
- Increase timeout in workflow
- Reduce parallel shards
- Check service health

### Slack Notifications Not Working
- Verify `SLACK_WEBHOOK_URL` secret exists
- Test webhook with curl
- Check channel permissions

## Documentation

- **CI_CD_REFERENCE.md**: Quick reference for developers
- **SLACK_SETUP_GUIDE.md**: Slack configuration
- **test-automation.yml**: Workflow definition

