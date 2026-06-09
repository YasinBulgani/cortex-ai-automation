# Test Data Factories — Quick Reference

## What is factory_boy?

factory_boy is a Python library that provides lightweight object factories for creating test data. Instead of manually building test objects, factories generate consistent, realistic data with minimal code.

**Key benefit:** Tests are cleaner, more maintainable, and easier to write.

## Installation

```bash
pip install factory-boy
# Already in requirements.txt: factory-boy>=3.3.0
```

## Quickest Start

```python
from tests.factories import UserFactory, TestCaseFactory

# No database — just in-memory objects
user = UserFactory.build()
test_case = TestCaseFactory.build()

# With database (integration tests)
user = UserFactory.create(session=db_session)
```

## File Structure

```
backend/
├── tests/
│   ├── factories.py                        # ← 600+ lines: 20+ factory classes
│   ├── FACTORIES.md                        # ← Complete reference guide
│   ├── README_FACTORIES.md                 # ← This file (quick reference)
│   ├── conftest.py                         # ← 9 pytest fixtures (updated)
│   ├── unit/
│   │   ├── test_factories_example.py       # ← 30+ example tests
│   │   └── test_factories_integration.py   # ← 20+ integration examples
│   └── ...
├── scripts/
│   └── seed_factories.py                   # ← Data seeding script
├── FACTORY_BOY_IMPLEMENTATION.md           # ← Complete implementation summary
├── requirements.txt                        # ← Updated with factory-boy
└── ...
```

## Factory Classes at a Glance

| Factory | Purpose | Key Fields |
|---------|---------|-----------|
| **UserFactory** | Create users | email (unique), full_name, department, roles |
| **OrganizationFactory** | Create organizations | name, slug, plan_code |
| **TeamFactory** | Create teams | organization, name, slug |
| **TestManagementProjectFactory** | Create projects | name, key (unique), tenant_id |
| **TestSuiteFactory** | Create test suites | project, name, status |
| **TestCaseFactory** | Create test cases | project, title, priority, case_key |
| **TestPlanFactory** | Create test plans | project, name, plan_type |
| **TestRunFactory** | Create test runs | project, environment, os, browser |
| **TestResultFactory** | Create test results | test_run, test_case, status, duration_seconds |
| **DefectFactory** | Create defects | project, title, severity, status |
| **AutomationRunFactory** | Create automation runs | project_id, kind, status |
| **AutomationScheduleFactory** | Create schedules | project_id, cron_expression, is_active |
| **And 8 more...** | Various support classes | See FACTORIES.md |

## Three Ways to Use Factories

### 1. Build (No Database)
```python
# Pure in-memory object — no database access
user = UserFactory.build()
assert user.email is not None
```

### 2. Stub (Dict/Mock)
```python
# Plain dictionary — fastest for mocks
user_dict = UserFactory.stub()
# Returns: {"id": "...", "email": "...", ...}
```

### 3. Create (With Database)
```python
# Persist to database via session
user = UserFactory.create(session=db_session)
assert user.id is not None  # Now in database
```

## 30 Second Example

```python
import pytest
from tests.factories import UserFactory, TestManagementProjectFactory, TestCaseFactory

def test_user_creates_test_case():
    """User can create a test case in a project."""
    
    # Create fixtures using factories
    user = UserFactory.build(full_name="Alice")
    project = TestManagementProjectFactory.build(name="E-Commerce")
    test_case = TestCaseFactory.build(
        project=project,
        title="User can login",
        priority="critical"
    )
    
    # Assert relationships
    assert test_case.project.id == project.id
    assert test_case.priority == "critical"
```

## Common Patterns

### Pattern 1: Override Fields
```python
user = UserFactory.build(
    email="specific@test.com",  # Override default
    full_name="Bob",
    is_active=False
)
```

### Pattern 2: Relationships
```python
project = TestManagementProjectFactory.build()
case1 = TestCaseFactory.build(project=project, title="Case 1")
case2 = TestCaseFactory.build(project=project, title="Case 2")
# Both cases linked to same project
```

### Pattern 3: Batch Creation
```python
users = UserFactory.build_batch(5)
projects = TestManagementProjectFactory.create_batch(10, session=db)
```

### Pattern 4: Complex Hierarchies
```python
from tests.factories import create_complete_project_hierarchy

hierarchy = create_complete_project_hierarchy(session=db)
# Returns: {
#   "project": TestManagementProject,
#   "suite": TestSuite,
#   "folders": [TestFolder, ...],
#   "cases": [TestCase, ...]  (6 cases total)
# }
```

## Pytest Fixtures

All factories have pytest fixtures available:

```python
def test_user(user_factory):
    user = user_factory.build()
    assert user is not None

def test_project(project_factory):
    project = project_factory.build()
    assert project is not None
```

**Available fixtures:**
- `user_factory`, `project_factory`, `test_case_factory`, `test_run_factory`, `test_result_factory`
- `organization_factory`, `team_factory`, `defect_factory`, `automation_run_factory`
- Plus database session: `db_session`

## Realistic Data

Factories use **Faker** to generate realistic data:

```python
user = UserFactory.build()
# user.full_name: "Maria Garcia" (realistic name)
# user.email: "user1@test.local" (unique sequence)
# user.department: "Software Engineer" (realistic job)
# user.phone: "+1-541-754-3010" (realistic phone)

project = TestManagementProjectFactory.build()
# project.name: "Navigate innovative solutions" (realistic catch phrase)
# project.description: "Lorem ipsum..." (realistic paragraph)

test_case = TestCaseFactory.build()
# test_case.title: "Consider exactly kitchen..." (realistic sentence)
# test_case.priority: "medium" (random from [low, medium, high, critical])
```

## Database Seeding

Populate development database with realistic test data:

```bash
# Default: 5 projects, 10 users
python backend/scripts/seed_factories.py

# Custom: 20 projects, 50 users
python backend/scripts/seed_factories.py --projects 20 --users 50

# With verbose logging
python backend/scripts/seed_factories.py --verbose

# Clean up all seeded data
python backend/scripts/seed_factories.py --cleanup
```

Creates:
- 10 users with random departments
- 2 organizations with 3 teams each
- 5 test projects with full hierarchy (suites, folders, cases)
- 3 test runs per project with 5 results each
- 3 defects per project
- 2 automation runs per project

## Important: ADR-0013

All factories respect **ADR-0013: Test Isolation via Clean Event Loop**:

- Each test gets **fresh** database session
- No shared state between tests
- Safe for async/concurrent execution

```python
def test_with_isolation(db_session, user_factory):
    # db_session is fresh per test
    # clean_event_loop is guaranteed
    user = user_factory.create(session=db_session)
```

## Running Tests

```bash
# All example tests (no DB required)
pytest tests/unit/test_factories_example.py -v

# Integration tests (requires DB)
pytest tests/unit/test_factories_integration.py -v

# Specific test
pytest tests/unit/test_factories_example.py::TestFactoryBasicUsage::test_build_user_no_db -v
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'factory'` | `pip install factory-boy` |
| `sqlalchemy_session is None` | Always pass `session=db_session` to `.create()` |
| Unique constraint violation | Use different values or override default |
| Foreign key errors | SubFactory handles this automatically |
| Event loop pollution | Use `db_session` fixture (ADR-0013) |

## See Also

- **Complete Guide:** `tests/FACTORIES.md` (450+ lines)
- **Implementation Details:** `backend/FACTORY_BOY_IMPLEMENTATION.md`
- **Example Tests:** `tests/unit/test_factories_example.py` (30+ tests)
- **Integration Examples:** `tests/unit/test_factories_integration.py` (20+ tests)
- **Seeding Script:** `backend/scripts/seed_factories.py`
- **factory_boy Docs:** https://factoryboy.readthedocs.io/
- **Faker Docs:** https://faker.readthedocs.io/

## Next Steps

1. **Install:** `pip install factory-boy`
2. **Read:** `tests/FACTORIES.md` for complete reference
3. **Run examples:** `pytest tests/unit/test_factories_example.py -v`
4. **Explore fixtures:** See `tests/conftest.py` lines 498+
5. **Start writing tests:** Use factories in your own tests!

## Statistics

- **20+ Factory Classes** — All core models covered
- **600+ Lines** — factories.py implementation
- **450+ Lines** — FACTORIES.md documentation
- **30+ Example Tests** — Runnable demonstrations
- **9 Pytest Fixtures** — Easy integration
- **3 Batch Helpers** — Complex scenarios simplified

---

**Key Insight:** factory_boy makes test data management effortless. Instead of manual setup, factories generate realistic, consistent data in one line of code. This means tests are cleaner, faster to write, and easier to maintain.
