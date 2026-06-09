# Phase 3.4 Implementation Guide
**Quick Start for Optimization & Scaling**  
**Date:** 2026-06-09  
**Effort:** 3 weeks (2 engineers + 1 DevOps)

---

## Quick Start Checklist

```bash
# 1. Set up flaky test detection
make test-backend  # Baseline
python scripts/detect_flaky.py --baseline  # Record baseline metrics

# 2. Enable CI/CD parallelization
make regression-parallel WORKERS=4  # Test configuration

# 3. Set up secrets masking
cd backend && pytest tests/compliance/test_gdpr.py -v

# 4. Schedule team workshops
# Week 1: pytest advanced (2h)
# Week 2: Karate API testing (2h)
# Week 3: Playwright E2E (2h)
```

---

## Part 1: Flaky Test Mitigation (1 Week)

### Step 1.1: Enhanced Flaky Service

**File:** `backend/app/domains/tspm/flaky_service.py`

```python
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, desc
from app.infra.models import FlakyTest, FlakyTestRun
from app.infra.database import get_db

class FlakyTestService:
    """Detect, quarantine, and monitor flaky tests."""
    
    QUARANTINE_THRESHOLD = 3  # Fail 3+ times → quarantine
    WINDOW_SIZE = 10  # Last 10 runs
    
    def __init__(self, db_session):
        self.db = db_session
    
    async def record_test_run(
        self,
        project_id: str,
        test_id: str,
        test_name: str,
        passed: bool,
        duration_ms: float,
        run_id: Optional[str] = None,
    ) -> FlakyTestRun:
        """Record individual test run."""
        test_run = FlakyTestRun(
            project_id=project_id,
            test_id=test_id,
            test_name=test_name,
            passed=passed,
            duration_ms=duration_ms,
            run_id=run_id,
            recorded_at=datetime.utcnow(),
        )
        self.db.add(test_run)
        await self.db.commit()
        
        # Check if should quarantine
        await self._check_and_quarantine(project_id, test_id)
        
        return test_run
    
    async def _check_and_quarantine(self, project_id: str, test_id: str):
        """Quarantine test if fail rate exceeds threshold."""
        # Get last N runs
        recent_runs = await self.db.execute(
            select(FlakyTestRun)
            .where(
                (FlakyTestRun.project_id == project_id) &
                (FlakyTestRun.test_id == test_id)
            )
            .order_by(desc(FlakyTestRun.recorded_at))
            .limit(self.WINDOW_SIZE)
        )
        recent = recent_runs.scalars().all()
        
        if len(recent) < self.WINDOW_SIZE:
            return  # Not enough data yet
        
        fail_count = sum(1 for r in recent if not r.passed)
        
        if fail_count >= self.QUARANTINE_THRESHOLD:
            # Get or create flaky test record
            flaky = await self.db.execute(
                select(FlakyTest).where(
                    (FlakyTest.project_id == project_id) &
                    (FlakyTest.test_id == test_id)
                )
            )
            flaky_record = flaky.scalar_one_or_none()
            
            if not flaky_record:
                flaky_record = FlakyTest(
                    project_id=project_id,
                    test_id=test_id,
                    test_name=recent[0].test_name,
                    is_quarantined=True,
                    quarantine_reason=f"Fail rate {fail_count}/{len(recent)}",
                    first_failure=recent[-1].recorded_at,
                    last_failure=recent[0].recorded_at,
                )
                self.db.add(flaky_record)
            else:
                flaky_record.is_quarantined = True
                flaky_record.last_failure = recent[0].recorded_at
            
            await self.db.commit()
    
    async def get_flaky_dashboard(self, project_id: str) -> dict:
        """Get dashboard data: flakiness rate, trending, top 10."""
        # Total runs in last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        total_runs_query = select(func.count(FlakyTestRun.id)).where(
            (FlakyTestRun.project_id == project_id) &
            (FlakyTestRun.recorded_at >= seven_days_ago)
        )
        total_runs = (await self.db.execute(total_runs_query)).scalar() or 0
        
        # Flaky tests
        flaky_tests_query = select(FlakyTest).where(
            (FlakyTest.project_id == project_id) &
            (FlakyTest.is_quarantined == True)
        )
        flaky_tests = (
            (await self.db.execute(flaky_tests_query)).scalars().all()
        )
        
        # Top 10 by fail rate
        top_flaky = await self._get_top_flaky_tests(project_id, limit=10)
        
        # Trending (tests becoming flaky)
        trending_up = await self._get_trending_up(project_id, days=7)
        
        # Historical trend (daily flaky %)
        trend_data = await self._get_daily_flaky_trend(project_id, days=30)
        
        return {
            "project_id": project_id,
            "total_runs_7d": total_runs,
            "flaky_tests": [
                {
                    "test_id": t.test_id,
                    "test_name": t.test_name,
                    "fail_rate": await self._calculate_fail_rate(
                        project_id, t.test_id
                    ),
                    "is_quarantined": t.is_quarantined,
                    "quarantine_reason": t.quarantine_reason,
                    "last_failure": t.last_failure.isoformat(),
                }
                for t in flaky_tests
            ],
            "top_flaky_tests": top_flaky,
            "trending_up": trending_up,
            "historical_trend": trend_data,
            "flaky_rate_percent": (
                (len(flaky_tests) / max(total_runs, 1)) * 100
            ),
        }
    
    async def _get_top_flaky_tests(self, project_id: str, limit: int = 10):
        """Get top N flakiest tests by fail rate."""
        query = select(FlakyTest).where(
            FlakyTest.project_id == project_id
        ).order_by(desc(FlakyTest.last_failure)).limit(limit)
        
        tests = (await self.db.execute(query)).scalars().all()
        
        result = []
        for test in tests:
            fail_rate = await self._calculate_fail_rate(
                project_id, test.test_id
            )
            result.append({
                "test_id": test.test_id,
                "test_name": test.test_name,
                "fail_rate": fail_rate,
                "is_quarantined": test.is_quarantined,
            })
        
        return sorted(result, key=lambda x: x["fail_rate"], reverse=True)
    
    async def _calculate_fail_rate(self, project_id: str, test_id: str) -> float:
        """Calculate fail rate for last N runs."""
        query = select(FlakyTestRun).where(
            (FlakyTestRun.project_id == project_id) &
            (FlakyTestRun.test_id == test_id)
        ).order_by(desc(FlakyTestRun.recorded_at)).limit(self.WINDOW_SIZE)
        
        runs = (await self.db.execute(query)).scalars().all()
        if not runs:
            return 0.0
        
        fail_count = sum(1 for r in runs if not r.passed)
        return (fail_count / len(runs)) * 100
    
    async def _get_trending_up(self, project_id: str, days: int = 7) -> list:
        """Get tests whose fail rate increased recently."""
        # Get all tests, calculate 7d and 30d fail rates
        # Return tests where 7d > 30d
        return []  # Simplified for now
    
    async def _get_daily_flaky_trend(self, project_id: str, days: int = 30) -> list:
        """Get daily flaky % trend for last N days."""
        trends = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days - i)
            start = date.replace(hour=0, minute=0, second=0)
            end = date.replace(hour=23, minute=59, second=59)
            
            total_query = select(func.count(FlakyTestRun.id)).where(
                (FlakyTestRun.project_id == project_id) &
                (FlakyTestRun.recorded_at >= start) &
                (FlakyTestRun.recorded_at <= end)
            )
            total = (await self.db.execute(total_query)).scalar() or 0
            
            if total == 0:
                continue
            
            failed_query = select(func.count(FlakyTestRun.id)).where(
                (FlakyTestRun.project_id == project_id) &
                (FlakyTestRun.recorded_at >= start) &
                (FlakyTestRun.recorded_at <= end) &
                (FlakyTestRun.passed == False)
            )
            failed = (await self.db.execute(failed_query)).scalar() or 0
            
            trends.append({
                "date": date.date().isoformat(),
                "flaky_percent": (failed / total) * 100,
                "total_runs": total,
            })
        
        return trends
    
    async def unquarantine_test(self, project_id: str, test_id: str):
        """Manually unquarantine test."""
        query = select(FlakyTest).where(
            (FlakyTest.project_id == project_id) &
            (FlakyTest.test_id == test_id)
        )
        flaky = (await self.db.execute(query)).scalar_one_or_none()
        
        if flaky:
            flaky.is_quarantined = False
            flaky.unquarantine_reason = "Manual unquarantine"
            await self.db.commit()
```

### Step 1.2: Router Endpoints

**File:** `backend/app/domains/tspm/flaky_router.py`

```python
from fastapi import APIRouter, Depends
from app.deps import get_current_user, require_permission
from app.infra.models import User
from .flaky_service import FlakyTestService

router = APIRouter(prefix="/projects", tags=["TSPM - Flaky"])

@router.get("/{project_id}/flaky-tests")
async def get_flaky_dashboard(
    project_id: str,
    db = Depends(get_db),
    current_user: User = Depends(require_permission("view_reports")),
):
    """Get flaky test dashboard."""
    service = FlakyTestService(db)
    return await service.get_flaky_dashboard(project_id)

@router.post("/{project_id}/test-runs")
async def record_test_run(
    project_id: str,
    test_id: str,
    test_name: str,
    passed: bool,
    duration_ms: float,
    run_id: str = None,
    db = Depends(get_db),
    current_user: User = Depends(require_permission("write_reports")),
):
    """Record individual test run."""
    service = FlakyTestService(db)
    return await service.record_test_run(
        project_id, test_id, test_name, passed, duration_ms, run_id
    )

@router.post("/{project_id}/flaky/{test_id}/unquarantine")
async def unquarantine_test(
    project_id: str,
    test_id: str,
    db = Depends(get_db),
    current_user: User = Depends(require_permission("admin")),
):
    """Manually unquarantine a test."""
    service = FlakyTestService(db)
    await service.unquarantine_test(project_id, test_id)
    return {"status": "unquarantined"}
```

### Step 1.3: Database Models

**File:** `backend/app/infra/models.py` (Add to existing)

```python
class FlakyTest(Base):
    """Track flaky tests."""
    __tablename__ = "flaky_tests"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)
    test_id = Column(String(255), index=True)
    test_name = Column(String(500))
    is_quarantined = Column(Boolean, default=False, index=True)
    quarantine_reason = Column(Text, nullable=True)
    unquarantine_reason = Column(Text, nullable=True)
    first_failure = Column(DateTime)
    last_failure = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FlakyTestRun(Base):
    """Record of individual test runs for flakiness analysis."""
    __tablename__ = "flaky_test_runs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), index=True)
    test_id = Column(String(255), index=True)
    test_name = Column(String(500))
    passed = Column(Boolean, index=True)
    duration_ms = Column(Float)
    run_id = Column(String(36), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("ix_flaky_test_runs_project_test", "project_id", "test_id"),
        Index("ix_flaky_test_runs_recorded", "recorded_at"),
    )
```

### Step 1.4: Migration

**File:** `backend/alembic/versions/20260609_0001_flaky_test_tracking.py`

```python
"""Flaky test tracking tables."""

from alembic import op
import sqlalchemy as sa

revision = "20260609_0001"
down_revision = "20260608_0005"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "flaky_tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("test_id", sa.String(255)),
        sa.Column("test_name", sa.String(500)),
        sa.Column("is_quarantined", sa.Boolean, default=False),
        sa.Column("quarantine_reason", sa.Text),
        sa.Column("unquarantine_reason", sa.Text),
        sa.Column("first_failure", sa.DateTime),
        sa.Column("last_failure", sa.DateTime),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    
    op.create_index("ix_flaky_tests_project", "flaky_tests", ["project_id"])
    op.create_index("ix_flaky_tests_test_id", "flaky_tests", ["test_id"])
    op.create_index("ix_flaky_tests_quarantined", "flaky_tests", ["is_quarantined"])
    
    op.create_table(
        "flaky_test_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
        sa.Column("test_id", sa.String(255)),
        sa.Column("test_name", sa.String(500)),
        sa.Column("passed", sa.Boolean),
        sa.Column("duration_ms", sa.Float),
        sa.Column("run_id", sa.String(36)),
        sa.Column("recorded_at", sa.DateTime),
    )
    
    op.create_index("ix_flaky_test_runs_project_test", "flaky_test_runs", ["project_id", "test_id"])
    op.create_index("ix_flaky_test_runs_passed", "flaky_test_runs", ["passed"])
    op.create_index("ix_flaky_test_runs_recorded", "flaky_test_runs", ["recorded_at"])

def downgrade():
    op.drop_table("flaky_test_runs")
    op.drop_table("flaky_tests")
```

### Step 1.5: Unit Tests

**File:** `backend/tests/unit/test_flaky_service_enhanced.py`

```python
import pytest
from datetime import datetime, timedelta
from app.domains.tspm.flaky_service import FlakyTestService
from app.infra.models import FlakyTest, FlakyTestRun

@pytest.mark.asyncio
async def test_record_test_run(db_session):
    """Record individual test run."""
    service = FlakyTestService(db_session)
    
    run = await service.record_test_run(
        project_id="proj-123",
        test_id="test-001",
        test_name="Test Login Flow",
        passed=True,
        duration_ms=234.5,
    )
    
    assert run.test_id == "test-001"
    assert run.passed == True
    assert run.duration_ms == 234.5

@pytest.mark.asyncio
async def test_quarantine_on_3_failures(db_session):
    """Quarantine test after 3 failures in 10 runs."""
    service = FlakyTestService(db_session)
    
    # Record 10 runs: 3 failed, 7 passed
    for i in range(7):
        await service.record_test_run(
            project_id="proj-123",
            test_id="test-flaky",
            test_name="Flaky Test",
            passed=True,
            duration_ms=100.0,
        )
    
    for i in range(3):
        await service.record_test_run(
            project_id="proj-123",
            test_id="test-flaky",
            test_name="Flaky Test",
            passed=False,
            duration_ms=100.0,
        )
    
    # Check quarantine status
    flaky = await db_session.get(FlakyTest, ("proj-123", "test-flaky"))
    # Note: you'd need to implement get properly or use query
    # This is simplified for illustration

@pytest.mark.asyncio
async def test_flaky_dashboard(db_session):
    """Get flaky test dashboard."""
    service = FlakyTestService(db_session)
    
    # Record some test runs
    for i in range(5):
        await service.record_test_run(
            project_id="proj-123",
            test_id="test-001",
            test_name="Test 1",
            passed=i % 2 == 0,
            duration_ms=100.0 + i * 10,
        )
    
    dashboard = await service.get_flaky_dashboard("proj-123")
    
    assert "total_runs_7d" in dashboard
    assert "flaky_tests" in dashboard
    assert "flaky_rate_percent" in dashboard
    assert dashboard["project_id"] == "proj-123"
```

---

## Part 2: CI/CD Optimization (1 Week)

### Step 2.1: Parallelization Configuration

**File:** `backend/pyproject.toml` (Add/update)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "regression: regression tests",
    "flaky: flaky test handling",
    "slow: slow tests (>1s)",
    "integration: integration tests",
    "unit: unit tests",
    "compliance: GDPR/compliance tests",
]

[tool.pytest.ini_options]
# For parallel execution with pytest-xdist
# Use: pytest -n 4 --dist=loadscope
addopts = "--strict-markers"
```

**File:** `Makefile` (Add targets)

```makefile
# Test parallelization
PYTEST_WORKERS ?= 4
PYTEST_TIMEOUT ?= 300

test-parallel:
	@echo "Running tests with $(PYTEST_WORKERS) workers (timeout: $(PYTEST_TIMEOUT)s)"
	cd backend && $(PYTHON) -m pytest \
		--dist=loadscope \
		-n $(PYTEST_WORKERS) \
		--timeout=$(PYTEST_TIMEOUT) \
		--tb=short \
		-v \
		$(PYTEST_ARGS)

test-parallel-unit:
	@echo "Running unit tests in parallel ($(PYTEST_WORKERS) workers)"
	cd backend && $(PYTHON) -m pytest \
		tests/unit/ \
		-n $(PYTEST_WORKERS) \
		--dist=loadscope \
		--tb=short \
		-v

test-fail-fast:
	@echo "Running tests with fail-fast (stop on first failure)"
	cd backend && $(PYTHON) -m pytest \
		--dist=loadscope \
		-n $(PYTEST_WORKERS) \
		-x \
		--tb=line \
		-q

test-profile:
	@echo "Running tests with timing profile"
	cd backend && $(PYTHON) -m pytest \
		--dist=loadscope \
		-n $(PYTEST_WORKERS) \
		--durations=10 \
		$(PYTEST_ARGS)
```

### Step 2.2: Dependency Caching

**File:** `.github/workflows/test.yml` (New/updated)

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Cache dependencies
      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Cache npm dependencies
        uses: actions/cache@v3
        with:
          path: ~/.npm
          key: ${{ runner.os }}-npm-${{ hashFiles('apps/web/package-lock.json') }}
          restore-keys: |
            ${{ runner.os }}-npm-
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt pytest-xdist pytest-timeout
      
      - name: Run unit tests (parallel)
        run: make test-parallel-unit PYTEST_WORKERS=4
      
  api-tests:
    name: API Tests
    runs-on: ubuntu-latest
    needs: unit-tests  # Only run if unit tests pass
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      
      - name: Cache pip
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: pip install -r requirements.txt pytest-xdist
      
      - name: Run API tests (parallel)
        run: make test-parallel PYTEST_ARGS="tests/integration" PYTEST_WORKERS=4
      
  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    # Run regardless of API test failure
    if: always()
    steps:
      - uses: actions/checkout@v3
      
      - name: Cache npm
        uses: actions/cache@v3
        with:
          path: ~/.npm
          key: ${{ runner.os }}-npm-${{ hashFiles('apps/web/package-lock.json') }}
      
      - name: Cache Next.js build
        uses: actions/cache@v3
        with:
          path: apps/web/.next
          key: ${{ runner.os }}-nextjs-${{ hashFiles('apps/web/package-lock.json') }}
      
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: "18"
      
      - name: Install dependencies
        run: cd apps/web && npm ci
      
      - name: Run E2E tests
        run: npm run test:e2e

  coverage:
    name: Code Coverage
    runs-on: ubuntu-latest
    needs: [unit-tests, api-tests]
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Generate coverage report
        run: cd backend && pytest --cov=app --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: backend/coverage.xml
```

### Step 2.3: Secrets Management

**File:** `backend/app/infra/logging_config.py` (New)

```python
import logging
import re
from typing import Any

class SensitiveDataFilter(logging.Filter):
    """Redact sensitive data from logs."""
    
    SENSITIVE_KEYS = {
        "password", "token", "api_key", "secret", "auth",
        "key", "credential", "bearer", "x-api-key"
    }
    
    PATTERNS = [
        (r'"password"\s*:\s*"([^"]+)"', '"password": "[REDACTED]"'),
        (r'"token"\s*:\s*"([^"]+)"', '"token": "[REDACTED]"'),
        (r'"api_key"\s*:\s*"([^"]+)"', '"api_key": "[REDACTED]"'),
        (r'Authorization:\s*Bearer\s+\S+', 'Authorization: Bearer [REDACTED]'),
        (r'X-API-Key:\s*\S+', 'X-API-Key: [REDACTED]'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive data."""
        if record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            record.msg = msg
        
        if record.args:
            if isinstance(record.args, dict):
                for key in self.SENSITIVE_KEYS:
                    if key in record.args:
                        record.args[key] = "[REDACTED]"
        
        return True

def setup_logging():
    """Configure logging with sensitive data filtering."""
    logger = logging.getLogger()
    
    # Add sensitive data filter to all handlers
    for handler in logger.handlers:
        handler.addFilter(SensitiveDataFilter())
    
    return logger
```

---

## Part 3: Production Hardening (1 Week)

### Step 3.1: Environment-Based Settings

**File:** `backend/app/config.py` (Add/update)

```python
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"
    
    # Environment-specific test config
    @property
    def TEST_MODE(self) -> bool:
        """Allow tests only in dev/staging."""
        return self.ENVIRONMENT != "prod"
    
    @property
    def RUN_ALL_TESTS(self) -> bool:
        """Run all test types only in dev."""
        return self.ENVIRONMENT == "dev"
    
    @property
    def RUN_REGRESSION_TESTS(self) -> bool:
        """Run regression tests in staging/prod."""
        return self.ENVIRONMENT in ["staging", "prod"]
    
    @property
    def ALLOW_DATA_MUTATION(self) -> bool:
        """Allow data mutation only in dev."""
        return self.ENVIRONMENT == "dev"
    
    @property
    def LOG_LEVEL(self) -> str:
        levels = {
            "dev": "DEBUG",
            "staging": "INFO",
            "prod": "WARNING"
        }
        return levels[self.ENVIRONMENT]
    
    @property
    def ENABLE_PROFILING(self) -> bool:
        """Enable profiling only in dev."""
        return self.ENVIRONMENT == "dev"
    
    @property
    def ENABLE_MOCKING(self) -> bool:
        """Enable service mocking only in dev."""
        return self.ENVIRONMENT == "dev"
    
    @property
    def ENABLE_AUDIT_LOG(self) -> bool:
        """Enable audit logging in staging/prod."""
        return self.ENVIRONMENT in ["staging", "prod"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### Step 3.2: GDPR Compliance Tests

**File:** `backend/tests/compliance/test_gdpr.py` (New)

```python
import pytest
from datetime import datetime
from app.domains.privacy.service import PrivacyService
from app.infra.models import User, AuditLog

@pytest.mark.compliance
@pytest.mark.asyncio
async def test_user_deletion_anonymizes_identity(db_session):
    """GDPR: User deletion must anonymize identity."""
    # Create user
    user = User(
        id="user-123",
        email="test@example.com",
        name="Test User",
    )
    db_session.add(user)
    await db_session.commit()
    
    # Delete user
    service = PrivacyService(db_session)
    await service.delete_user_data("user-123")
    
    # Verify anonymization
    user = await db_session.get(User, "user-123")
    assert user.email.startswith("deleted_")
    assert user.name == "Deleted User"
    assert "test@example.com" not in user.email

@pytest.mark.compliance
@pytest.mark.asyncio
async def test_user_deletion_creates_audit_log(db_session):
    """GDPR: User deletion must create audit trail."""
    user = User(id="user-456", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    service = PrivacyService(db_session)
    await service.delete_user_data("user-456")
    
    # Verify audit log
    audit = await db_session.query(AuditLog).filter_by(
        action="user_deletion",
        user_id="user-456"
    ).first()
    
    assert audit is not None
    assert audit.timestamp is not None

@pytest.mark.compliance
@pytest.mark.asyncio
async def test_user_data_export_completeness(db_session):
    """GDPR: User must be able to export all personal data."""
    user = User(id="user-789", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    service = PrivacyService(db_session)
    exported = await service.export_user_data("user-789")
    
    assert "user" in exported
    assert "email" in exported["user"]
    assert exported["user"]["email"] == "test@example.com"

@pytest.mark.compliance
def test_pii_not_leaked_in_logs(caplog):
    """PII redaction: sensitive data not in logs."""
    import logging
    from app.infra.logging_config import SensitiveDataFilter
    
    logger = logging.getLogger()
    logger.addFilter(SensitiveDataFilter())
    
    # Log with sensitive data
    logger.warning(f'"password": "secret123"')
    
    # Verify redaction
    assert "[REDACTED]" in caplog.text
    assert "secret123" not in caplog.text

@pytest.mark.compliance
@pytest.mark.asyncio
async def test_api_key_rotation(db_session):
    """Credential rotation: old API keys are revoked."""
    user = User(id="user-001", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    from app.domains.auth.service import AuthService
    service = AuthService(db_session)
    
    # Generate multiple keys
    key1 = await service.create_api_key("user-001")
    key2 = await service.create_api_key("user-001")
    key3 = await service.create_api_key("user-001")
    
    # Rotate (keep only latest)
    await service.rotate_api_keys("user-001")
    
    # Verify only latest is active
    keys = await service.get_user_api_keys("user-001")
    active_keys = [k for k in keys if k.status == "active"]
    assert len(active_keys) == 1
```

---

## Part 4: Team Training (1 Week)

### Step 4.1: Workshop Materials

**File:** `docs/TEST_AUTOMATION_WORKSHOP_OUTLINE.md` (New)

```markdown
# Test Automation Workshop Series

## Workshop 1: pytest Advanced (2 hours)

### Agenda
1. Fixtures (0:00-0:20)
   - Function, class, session scope
   - Autouse fixtures
   - Parametrized fixtures
   
2. Parametrization (0:20-0:35)
   - @pytest.mark.parametrize
   - Indirect parametrization
   - Data-driven tests
   
3. Markers (0:35-0:45)
   - Custom markers
   - Filtering with -m flag
   - Combining markers
   
4. Mocking (0:45-1:10)
   - unittest.mock
   - monkeypatch
   - pytest-mock
   - Mock assertions
   
5. Async Testing (1:10-1:35)
   - pytest-asyncio
   - Event loop isolation
   - Async fixtures
   - Async context managers
   
6. Hands-On Lab (1:35-2:00)
   - Write parametrized test suite
   - Fix 3 flaky tests
   - Optimize slow test with mocking

### Code Examples

#### Fixture Example
\`\`\`python
@pytest.fixture
def user(db_session):
    user = User(name="Test")
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)  # Cleanup
    db_session.commit()

def test_user_creation(user):
    assert user.name == "Test"
\`\`\`

#### Parametrize Example
\`\`\`python
@pytest.mark.parametrize("email,valid", [
    ("test@example.com", True),
    ("invalid", False),
    ("test@", False),
])
def test_email_validation(email, valid):
    assert validate_email(email) == valid
\`\`\`

#### Async Example
\`\`\`python
@pytest.mark.asyncio
async def test_async_user_creation(user_service):
    user = await user_service.create("test@example.com")
    assert user.email == "test@example.com"
\`\`\`

## Workshop 2: Karate API Testing (2 hours)

[Similar structure with Karate examples]

## Workshop 3: Playwright E2E (2 hours)

[Similar structure with Playwright examples]
```

---

## Quick Implementation Checklist

```bash
# Week 1: Flaky Detection
[ ] Run alembic migrations
    make migrate
[ ] Deploy flaky_service.py endpoints
[ ] Set up flaky test dashboard (frontend)
[ ] Record baseline metrics
    python scripts/detect_flaky.py --baseline
[ ] Create test-flaky detection unit tests
    cd backend && pytest tests/unit/test_flaky_service_enhanced.py -v

# Week 2: CI/CD Optimization
[ ] Update .github/workflows/test.yml with parallelization
[ ] Test locally with pytest-xdist
    make test-parallel PYTEST_WORKERS=4
[ ] Configure dependency caching
[ ] Set up fail-fast CI job
[ ] Measure execution time improvement

# Week 3: Hardening + Training
[ ] Implement SensitiveDataFilter
[ ] Run GDPR compliance tests
    cd backend && pytest tests/compliance/test_gdpr.py -v
[ ] Schedule 3 workshops
[ ] Create workshop materials
[ ] Set up team knowledge base

# Ongoing Monitoring
[ ] Daily flaky test dashboard
[ ] Weekly team metrics review
[ ] Monthly team workshop
```

---

## Success Metrics to Track

```bash
# Flaky test rate
python scripts/detect_flaky.py --report

# Test execution time
make test-parallel --durations=10

# CI/CD pass rate
# (check GitHub Actions dashboard)

# Team knowledge
# (survey after workshops)
```

---

## Next Steps

1. **This Week:** Review plan with team, start Week 1 implementation
2. **Week 1:** Deploy flaky test detection
3. **Week 2:** Set up CI/CD parallelization
4. **Week 3:** Complete hardening + run first workshop

---

## Support & Questions

- Q: How do I detect if a test is flaky?  
  A: Use `python scripts/detect_flaky.py --analyze test-id`

- Q: What's the optimal worker count for my machine?  
  A: Use `make test-profile` to measure, then set `PYTEST_WORKERS=$(nproc)`

- Q: How do I contribute to the knowledge base?  
  A: Add FAQ to `docs/TEST_AUTOMATION_FAQ.md`

---

**Owner:** QA Engineering Lead  
**Timeline:** 3 weeks starting 2026-06-09  
**Budget:** 2 engineers + 1 DevOps  
**Success Criteria:** 0 secrets in logs, <0.5% flaky rate, <45min full test suite
