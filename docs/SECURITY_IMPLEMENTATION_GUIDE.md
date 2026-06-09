# Security & Contract Testing Implementation Guide

## Overview

This guide covers the implementation of a comprehensive security test suite (Phase 2.4) for the Neurex Platform API. Total effort: ~40-60 hours over 1-2 weeks (2 engineers).

---

## Test Suite Architecture

### Layer 1: Unit-Level Security Tests (Python pytest)

```
backend/tests/security/
├── test_sql_injection.py     # 15 test methods
├── test_xss_prevention.py    # 20 test methods
├── test_csrf_protection.py   # 12 test methods
├── test_auth_bypass.py       # 24 test methods
└── test_rate_limiting.py     # 6 test methods
                              ─────────────
Total: 77 pytest test methods
```

**Features:**
- No external dependencies beyond pytest, FastAPI, TestClient
- Run in ~30 seconds against running backend
- Generate JUnit XML reports for CI/CD
- Parametrized tests for payload variations
- Markers for selective execution (@owasp_a03, @security, etc.)

### Layer 2: Contract Testing (OpenAPI)

```
backend/tests/contracts/
├── test_openapi_compliance.py      # 20 test methods
└── test_request_validation.py      # 18 test methods
                                    ─────────────
Total: 38 pytest test methods
```

**Features:**
- Validates API against OpenAPI spec
- Detects breaking changes (removed fields, status code shifts)
- Validates request/response schemas
- Tests pagination, error formats, headers

### Layer 3: BDD Features (Optional)

```
backend/features/security/
├── sql_injection.feature           # 10 scenarios (Gherkin)
└── xss_prevention.feature          # 12 scenarios (Gherkin)
                                    ─────────────
Total: 22 BDD scenarios (requires pytest-bdd)
```

**Features:**
- Readable business-friendly test descriptions
- Easy to maintain without code knowledge
- Can be run by QA engineers
- Integrates with ALM tools

---

## Implementation Timeline

### Week 1: Core Security Tests (40 hours)

| Day | Task | Hours | Deliverables |
|-----|------|-------|--------------|
| 1-2 | SQL Injection tests setup | 8 | test_sql_injection.py, conftest.py |
| 2-3 | XSS Prevention tests | 8 | test_xss_prevention.py |
| 3 | CSRF Protection tests | 6 | test_csrf_protection.py |
| 4 | Auth & Authorization tests | 8 | test_auth_bypass.py |
| 5 | Rate Limiting tests | 6 | test_rate_limiting.py |
| 5 | Documentation | 4 | SECURITY_TEST_SUITE.md |

### Week 2: Contract Testing (20 hours)

| Day | Task | Hours | Deliverables |
|-----|------|-------|--------------|
| 1-2 | OpenAPI Compliance tests | 10 | test_openapi_compliance.py |
| 2-3 | Request Validation tests | 8 | test_request_validation.py |
| 4 | BDD Feature files | 4 | sql_injection.feature, xss_prevention.feature |

---

## Setup Instructions

### 1. Create Directory Structure

```bash
cd backend/tests
mkdir -p security contracts
touch security/__init__.py contracts/__init__.py
```

### 2. Install Dependencies

```bash
cd backend
pip install pytest pytest-asyncio pytest-cov pytest-xdist
# Optional for BDD:
pip install pytest-bdd behave
```

### 3. Configure pytest Markers

Add to `backend/pytest.ini`:

```ini
[pytest]
markers =
    security: Security test (OWASP)
    owasp_a01: OWASP A01 - Broken Access Control
    owasp_a03: OWASP A03 - Injection
    owasp_a06: OWASP A06 - Vulnerable Components
    owasp_a07: OWASP A07 - Cross-Site Scripting
    contract: Contract/API compliance test
    openapi: OpenAPI specification test
    request_validation: Request schema validation
    integration: Integration test (slow)
```

### 4. Create Fixtures in conftest.py

```python
# backend/tests/conftest.py - already has basic fixtures
# Add security-specific ones in tests/security/conftest.py

@pytest.fixture
def sql_injection_payloads():
    return [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users--",
    ]

@pytest.fixture
def xss_payloads():
    return [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
    ]
```

---

## Running the Tests

### All Security Tests

```bash
cd backend
pytest tests/security/ -v

# With coverage
pytest tests/security/ -v --cov=app --cov-report=html

# In parallel (faster)
pytest tests/security/ -v -n auto
```

### Specific Categories

```bash
# SQL Injection only
pytest tests/security/ -v -m owasp_a03

# XSS only
pytest tests/security/ -v -m owasp_a07

# Auth/RBAC only
pytest tests/security/ -v -m owasp_a01

# Rate limiting
pytest tests/security/ -v -m owasp_a06
```

### Contract Tests

```bash
pytest tests/contracts/ -v

# OpenAPI spec compliance
pytest tests/contracts/test_openapi_compliance.py -v

# Request validation
pytest tests/contracts/test_request_validation.py -v
```

### BDD Features (if pytest-bdd installed)

```bash
pytest backend/features/security/ -v --gherkin-terminal-reporter
```

### Generate Reports

```bash
# JUnit XML for CI/CD
pytest tests/security/ tests/contracts/ --junitxml=test-results.xml

# Coverage HTML report
pytest tests/security/ tests/contracts/ --cov=app --cov-report=html
# Open htmlcov/index.html

# JSON report for dashboards
pytest tests/security/ tests/contracts/ --json-report --json-report-file=report.json
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/security-tests.yml
name: Security Tests

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -e .
          pip install pytest pytest-cov pytest-xdist

      - name: Run security tests
        run: |
          cd backend
          pytest tests/security/ -v --junitxml=security-results.xml
        
      - name: Run contract tests
        run: |
          cd backend
          pytest tests/contracts/ -v --junitxml=contract-results.xml

      - name: Upload results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: backend/*-results.xml

      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const results = fs.readFileSync('backend/security-results.xml', 'utf8');
            // Parse and comment results
```

### Pre-commit Hook

```bash
#!/bin/bash
# .husky/pre-commit

cd backend
echo "Running security tests..."
pytest tests/security/ tests/contracts/ \
  -m "not integration" \
  --tb=short \
  -q

if [ $? -ne 0 ]; then
  echo "Security tests failed! Fix before committing."
  exit 1
fi
```

### GitLab CI

```yaml
# .gitlab-ci.yml
security_tests:
  stage: test
  script:
    - cd backend
    - pip install -e . pytest pytest-cov
    - pytest tests/security/ -v --junitxml=security.xml
    - pytest tests/contracts/ -v --junitxml=contract.xml
  artifacts:
    reports:
      junit:
        - backend/security.xml
        - backend/contract.xml
```

---

## Test Maintenance & Updates

### When to Update Tests

1. **API spec changes:** Update contract tests to reflect OpenAPI changes
2. **New endpoints:** Add corresponding security tests
3. **Security incidents:** Add regression tests for disclosed vulnerabilities
4. **Framework upgrades:** Verify test compatibility with new versions

### Test Review Checklist

```markdown
- [ ] All payloads are from OWASP/CWE official sources
- [ ] Test isolation: no shared state between tests
- [ ] Coverage: all happy path + error cases
- [ ] Markers: properly tagged for filtering
- [ ] Documentation: docstrings for complex logic
- [ ] Performance: tests complete < 1 minute
- [ ] Assertions: clear, specific, not overly broad
- [ ] No hardcoded secrets in payloads
```

---

## Expected Results

### Passing Test Suite Output

```
tests/security/test_sql_injection.py::TestSQLInjection::test_project_list_sql_injection_or_payload PASSED [1%]
tests/security/test_sql_injection.py::TestSQLInjection::test_project_filter_union_based_injection PASSED [2%]
...
tests/security/ 77 passed in 35.23s
tests/contracts/ 38 passed in 28.45s

===================== 115 passed in 64.12s =====================
```

### Coverage Report

```
Name                    Stmts   Miss  Cover
────────────────────────────────────────────
app/__init__            5      0    100%
app/core/http.py        120    5    96%
app/core/runtime.py     95     3    97%
app/deps.py             110    2    98%
────────────────────────────────────────────
TOTAL                   2340   45    98%
```

---

## Troubleshooting

### Common Issues

1. **Tests hang on rate limiting tests**
   - Increase timeout: `pytest --timeout=10`
   - Skip: `pytest -m "not owasp_a06"`

2. **OpenAPI schema not found (404)**
   - Disable in production: tests check for 200 or 404
   - Dev/staging only: `if response.status_code == 200: ...`

3. **Concurrent test failures**
   - Use `clean_event_loop` fixture
   - Disable parallelization: remove `-n auto` flag

4. **Database not ready**
   - Check postgres service: `docker ps`
   - Run migrations: `alembic upgrade head`
   - Skip: `pytest -k "not db"`

### Debug Mode

```bash
# Verbose output + captured prints
pytest tests/security/ -vv -s

# Stop on first failure
pytest tests/security/ -x

# Show slowest tests
pytest tests/security/ --durations=10

# Run with pdb on failure
pytest tests/security/ --pdb
```

---

## Resources

### OWASP References
- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide v4.2](https://owasp.org/www-project-web-security-testing-guide/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)

### Standards & Best Practices
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OpenAPI 3.1.0 Spec](https://spec.openapis.org/oas/v3.1.0)

### FastAPI Security
- [FastAPI Security Docs](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/)

---

## Success Criteria

✓ All 77 security tests pass (100%)  
✓ All 38 contract tests pass (100%)  
✓ Code coverage > 95%  
✓ No false positives in test payload detection  
✓ Tests run in < 2 minutes  
✓ Documentation complete with examples  
✓ CI/CD integration working  
✓ Team trained on test execution/maintenance  

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-09  
**Maintained By:** QA Team
