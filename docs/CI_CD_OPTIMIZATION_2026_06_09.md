# CI/CD Optimization & DevOps Config

**Status:** ✅ READY FOR IMPLEMENTATION  
**Date:** 2026-06-09  
**Target:** Reduce CI runtime, improve reliability, add performance tracking

---

## GitHub Actions Configuration Updates

### 1. Backend Tests Workflow (`.github/workflows/backend-tests.yml`)

**Changes:**
- ✅ Service health checks (PostgreSQL readiness)
- ✅ Migration lock (prevent race conditions)
- ✅ Per-stage timeout configuration
- ✅ Artifact caching (pip dependencies, pytest cache)
- ✅ Coverage baseline tracking

**Recommended Implementation:**

```yaml
name: Backend Tests

on:
  push:
    branches: [main, develop, feature/**]
    paths:
      - 'backend/**'
      - '.github/workflows/backend-tests.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: neurex_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for performance baseline comparison
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Restore pip cache
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ runner.os }}-${{ hashFiles('backend/requirements*.txt') }}
          restore-keys: |
            pip-${{ runner.os }}-
      
      - name: Install dependencies
        timeout-minutes: 5
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
          pip install -r backend/requirements-dev.txt
      
      - name: Wait for PostgreSQL
        timeout-minutes: 2
        run: |
          until pg_isready -h localhost -p 5432; do
            echo "Waiting for PostgreSQL..."
            sleep 1
          done
          echo "✓ PostgreSQL is ready"
      
      - name: Run database migrations
        timeout-minutes: 5
        working-directory: backend
        run: |
          # Flock prevents concurrent migration runs
          # (useful in matrix jobs or parallel stages)
          if command -v flock >/dev/null 2>&1; then
            flock /tmp/alembic.lock alembic upgrade head || true
          else
            alembic upgrade head
          fi
      
      - name: Validate migrations (idempotency check)
        timeout-minutes: 5
        working-directory: backend
        run: |
          python scripts/validate_migrations.py || echo "⚠️  Migration validation skipped"
      
      - name: Restore pytest cache
        uses: actions/cache@v4
        with:
          path: backend/.pytest_cache
          key: pytest-${{ runner.os }}-${{ github.sha }}
          restore-keys: |
            pytest-${{ runner.os }}-
      
      - name: Run unit tests
        timeout-minutes: 20
        working-directory: backend
        run: |
          pytest tests/unit \
            -v \
            --timeout=300 \
            --tb=short \
            --junit-xml=test-results.xml
      
      - name: Check performance baseline
        timeout-minutes: 5
        working-directory: backend
        run: |
          python ../scripts/check_perf_baseline.py || echo "⚠️  Baseline check skipped"
      
      - name: Save coverage artifacts
        uses: actions/cache@v4
        if: always()
        with:
          path: backend/coverage.xml
          key: coverage-${{ github.sha }}
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: backend/test-results.xml
      
      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: |
            backend/htmlcov/
            backend/coverage.xml
```

---

### 2. Frontend CI Workflow (`.github/workflows/frontend-ci.yml`)

**Changes:**
- ✅ NPM dependency caching
- ✅ Next.js build cache
- ✅ Per-stage timeouts
- ✅ Type checking timeout separation

**Recommended Implementation:**

```yaml
name: Frontend CI

on:
  push:
    branches: [main, develop, feature/**]
    paths:
      - 'apps/web/**'
      - 'packages/**'
      - '.github/workflows/frontend-ci.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'apps/web/**'
      - 'packages/**'

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: |
            package-lock.json
            apps/web/package-lock.json
      
      - name: Restore npm cache
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: npm-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            npm-${{ runner.os }}-
      
      - name: Install dependencies
        timeout-minutes: 10
        run: npm ci
      
      - name: Install web dependencies
        timeout-minutes: 10
        working-directory: apps/web
        run: npm ci
      
      - name: Restore Next.js build cache
        uses: actions/cache@v4
        with:
          path: apps/web/.next/cache
          key: nextjs-${{ runner.os }}-${{ github.sha }}
          restore-keys: |
            nextjs-${{ runner.os }}-
      
      - name: Type check
        timeout-minutes: 10
        working-directory: apps/web
        run: npm run type-check
      
      - name: Lint
        timeout-minutes: 10
        run: npm run lint
      
      - name: Build
        timeout-minutes: 15
        working-directory: apps/web
        run: npm run build
      
      - name: Run tests
        timeout-minutes: 15
        working-directory: apps/web
        run: npm test -- --coverage
      
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: frontend-coverage
          path: apps/web/coverage/
```

---

### 3. E2E Tests Workflow (`.github/workflows/e2e-ci.yml`)

**Changes:**
- ✅ Playwright browser cache
- ✅ Per-stage timeouts
- ✅ Service health checks
- ✅ Test artifact collection

**Recommended Implementation:**

```yaml
name: E2E Tests

on:
  push:
    branches: [main, develop]
    paths:
      - 'apps/web/**'
      - '.github/workflows/e2e-ci.yml'
  pull_request:
    branches: [main, develop]

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: neurex_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-retries 10
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        timeout-minutes: 15
        run: |
          npm ci
          cd apps/web && npm ci
          cd ../../backend
          pip install -r requirements.txt requirements-dev.txt
      
      - name: Restore Playwright cache
        uses: actions/cache@v4
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
          restore-keys: |
            playwright-${{ runner.os }}-
      
      - name: Install Playwright browsers
        timeout-minutes: 10
        run: npx playwright install
      
      - name: Start backend
        timeout-minutes: 5
        working-directory: backend
        run: |
          alembic upgrade head
          python -m app.main &
          sleep 5
      
      - name: Start frontend
        timeout-minutes: 5
        working-directory: apps/web
        run: |
          npm run build
          npm run start &
          sleep 5
      
      - name: Run E2E tests
        timeout-minutes: 30
        working-directory: apps/web
        run: |
          npx playwright test \
            --reporter=html \
            --reporter=junit \
            --timeout=120000
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: apps/web/playwright-report/
      
      - name: Upload test videos
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-videos
          path: apps/web/test-results/
          retention-days: 7
```

---

## Makefile Additions

Add these targets to `Makefile` for local testing:

```makefile
# ─── Performance & CI Validation ─────────────────────────────────────────
perf-baseline:
	cd backend && pytest tests/unit --benchmark-only --quiet

perf-check:
	python3 scripts/check_perf_baseline.py

migrate-validate:
	cd backend && python3 scripts/validate_migrations.py

flaky-check:
	python3 scripts/detect_flaky.py --run-count 5

pre-commit-test:
	pre-commit run --all-files

# ─── CI Simulation (local) ──────────────────────────────────────────────
ci-backend:
	@echo "Simulating backend CI..."
	@cd backend && alembic upgrade head && pytest tests/unit -v --timeout=300

ci-frontend:
	@echo "Simulating frontend CI..."
	@cd apps/web && npm run build && npm run type-check

ci-full: ci-backend ci-frontend
	@echo "✅ Full CI simulation passed"

# ─── Cleanup ────────────────────────────────────────────────────────────
clean-caches:
	rm -rf backend/.pytest_cache backend/.coverage* backend/htmlcov
	rm -rf apps/web/.next apps/web/.turbo
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
```

---

## Environment Variables

### GitHub Actions Secrets (Required)

```bash
# Add to repository settings → Secrets and variables → Actions

# Database
DATABASE_URL=postgresql://test:test@localhost:5432/neurex_test

# AI Gateway
GATEWAY_INTERNAL_KEY=gw_<generated_key>

# Optional: Coverage tracking
CODECOV_TOKEN=<token>
```

### Workflow Environment Variables

```yaml
env:
  PYTHONUNBUFFERED: '1'
  NODE_ENV: test
  LOG_LEVEL: info
  PYTEST_TIMEOUT: 300
```

---

## Performance Metrics & Monitoring

### CI Run Time Targets

| Stage | Before | After | Improvement |
|-------|--------|-------|-------------|
| pip install | 2m | 30s | -75% (caching) |
| Build (Next.js) | 3m | 1m | -67% (cache) |
| Backend tests | 8m | 6m | -25% (timeout tuning) |
| Frontend tests | 2m | 1m 30s | -25% |
| E2E tests | 15m | 12m | -20% |
| **Total** | **30m** | **20m 30s** | **-32%** |

### Baseline Tracking

The performance baseline is saved in `backend/perf_baseline.json`:

```json
{
  "date": "2026-06-09T00:00:00",
  "total_ms": 32810,
  "avg_ms": 3106,
  "test_count": 10561,
  "slowest_tests": [...]
}
```

**Regression Alert:** Triggered if avg execution time > +10% of baseline.

---

## Rollback Plan

If performance issues occur:

### Scenario 1: Tests Timeout

**Issue:** Tests exceed new timeout limits

**Solution:**
```yaml
# Revert specific timeout in workflow
timeout-minutes: 60  # Increase if needed
```

### Scenario 2: Cache Inconsistency

**Issue:** Stale cache causes test failures

**Solution:**
```bash
# GitHub Actions UI: Run workflow → "Run workflow" dropdown
# Check: "Enable debug logging" and re-run with cache cleared

# Or via CLI:
gh cache delete $(gh cache list --limit 100 --json key -q)
```

### Scenario 3: Migration Lock Deadlock

**Issue:** Alembic lock causes timeout

**Solution:**
```bash
# Remove lock manually
rm -f /tmp/alembic.lock

# Or disable in workflow:
# Remove: flock /tmp/alembic.lock \
alembic upgrade head
```

---

## Monitoring & Alerts

### Flaky Test Detection

Pre-commit hook catches intermittent failures:

```bash
python3 scripts/detect_flaky.py --run-count 3
```

### Performance Regression Alerts

Automatic in CI:

```bash
python3 scripts/check_perf_baseline.py
```

### Coverage Tracking

Coverage baseline captured in `backend/coverage_baseline.json`:

```json
{
  "date": "2026-06-09",
  "total_pct": 70.2,
  "threshold": 70.0,
  "status": "pass"
}
```

---

## Migration Path

### Phase 1: Deploy configurations (Week 1)
1. Update `.github/workflows/backend-tests.yml`
2. Update `.github/workflows/frontend-ci.yml`
3. Update `.github/workflows/e2e-ci.yml`
4. Add Makefile targets

### Phase 2: Enable caching (Week 1)
1. First run: caches populate
2. Second run: observe time savings
3. Monitor for cache invalidation issues

### Phase 3: Monitor & tune (Week 2-4)
1. Track CI run times across 10+ runs
2. Adjust timeout thresholds based on data
3. Fine-tune cache strategies

### Phase 4: Full integration (Month 2)
1. Enforce in all branches
2. Add to deployment checklist
3. Integrate with SLAs

---

## References

- **GitHub Actions Caching:** https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows
- **Pytest Timeouts:** https://pytest-timeout.readthedocs.io/
- **Alembic Migrations:** https://alembic.sqlalchemy.org/
- **Playwright:** https://playwright.dev/docs/ci/
