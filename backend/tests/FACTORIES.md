# factory_boy Test Data Factories

This document describes the factory_boy pattern implementation for Neurex QA platform test data generation.

## Overview

**factories.py** provides lightweight, declarative factories for all core domain models:
- User, Organization, Team, Role (identity & auth)
- TestManagementProject, TestCase, TestRun, TestResult, Defect (test management)
- AutomationRun, AutomationSchedule (automation)

Factories are **pure** — they do NOT mutate the database by default. Use:
- `.build()` → In-memory object (no DB)
- `.stub()` → Plain dict (for mocks)
- `.create(session=db)` → Persist to DB

## Installation

```bash
pip install factory-boy faker
```

Both are already in `requirements.txt`:
```
factory-boy>=3.3.0
faker>=24.0.0
```

## Quick Start

### Unit Test (No DB)

```python
from tests.factories import UserFactory

def test_user_email():
    # In-memory object, no database
    user = UserFactory.build(email="alice@test.com")
    assert user.email == "alice@test.com"
```

### Integration Test (With DB)

```python
def test_user_persistence(db_session):
    # Persist to database via fixture
    user = UserFactory.create(session=db_session)
    assert user.id is not None
```

### Using Fixtures

```python
def test_project_creation(project_factory):
    project = project_factory.build(name="My Project")
    assert project.name == "My Project"
```

## Factory Classes

### Identity & Authorization

#### UserFactory
```python
user = UserFactory.build(
    email="alice@neurex.local",
    full_name="Alice",
    department="QA"
)
```

**Attributes:**
- `id` (UUID)
- `email` (unique sequence: user0@test.local, user1@test.local, ...)
- `password_hash` (placeholder)
- `full_name` (Faker.name)
- `phone` (Faker.phone_number)
- `department` (Faker.job)
- `tenant_id` (default: 00000000-0000-0000-0000-000000000001)
- `is_active` (True)
- `mfa_enabled` (False)
- `roles` (many-to-many via post_generation hook)

#### OrganizationFactory
```python
org = OrganizationFactory.build(name="ACME Corp")
```

**Attributes:**
- `id` (UUID)
- `name` (Faker.company)
- `slug` (Faker.slug)
- `plan_code` (free|pro|enterprise)
- `settings` (empty dict)

#### TeamFactory
```python
team = TeamFactory.build(
    organization=org,
    name="Frontend Team"
)
```

**Attributes:**
- `id` (UUID)
- `organization` (SubFactory)
- `name` (Faker.word)
- `slug` (auto-slugified from name)
- `description` (Faker.sentence)

#### RoleFactory
```python
role = RoleFactory.build(name="tester")
```

### Test Management

#### TestManagementProjectFactory
```python
project = TestManagementProjectFactory.build(
    name="E-commerce App",
    key="ECME"
)
```

**Attributes:**
- `id` (UUID)
- `name` (Faker.catch_phrase)
- `key` (sequence: PROJ-001, PROJ-002, ...)
- `description` (Faker.text)
- `status` (active|archived)
- `tenant_id` (default)
- `settings_data` (empty dict)

#### TestSuiteFactory
```python
suite = TestSuiteFactory.build(
    project=project,
    name="Smoke Tests"
)
```

**Attributes:**
- `id` (UUID)
- `project` (SubFactory)
- `name` (Faker.word)
- `description` (Faker.sentence)
- `status` (active|archived)
- `order_index` (sequence)

#### TestCaseFactory
```python
test_case = TestCaseFactory.build(
    project=project,
    title="User login with valid credentials",
    priority="high"
)
```

**Attributes:**
- `id` (UUID)
- `project` (SubFactory)
- `case_key` (sequence: TC-00001, TC-00002, ...)
- `title` (Faker.sentence)
- `priority` (low|medium|high|critical)
- `status` (active|archived)
- `test_type` (functional|regression|smoke|performance)
- `is_automated` (False)
- `tags` (empty list)
- `custom_attributes` (empty dict)

#### TestRunFactory
```python
run = TestRunFactory.build(
    project=project,
    name="Sprint 42 - Day 1",
    status="running"
)
```

**Attributes:**
- `id` (UUID)
- `project` (SubFactory)
- `name` (Faker.sentence)
- `status` (pending|running|passed|failed|completed)
- `run_type` (manual|automated|hybrid)
- `environment` (dev|staging|production)
- `os` (Windows|macOS|Linux)
- `browser` (Chrome|Firefox|Safari|Edge)
- `total_cases` (0, updated by results)
- `passed_cases` (0, updated by results)
- `duration_seconds` (None, set on completion)

#### TestResultFactory
```python
result = TestResultFactory.build(
    test_run=run,
    test_case=test_case,
    status="passed",
    duration_seconds=15
)
```

**Attributes:**
- `id` (UUID)
- `test_run` (SubFactory)
- `test_case` (SubFactory)
- `status` (passed|failed|skipped|blocked)
- `duration_seconds` (1-300)
- `start_time`, `end_time` (Faker.date_time)
- `error_message` (None)
- `actual_result` (Faker.paragraph)
- `attachments` (empty list)

#### DefectFactory
```python
defect = DefectFactory.build(
    project=project,
    title="Login button not responsive on mobile",
    severity="high",
    assigned_to=user
)
```

**Attributes:**
- `id` (UUID)
- `project` (SubFactory)
- `defect_key` (sequence: DEF-00001, DEF-00002, ...)
- `title` (Faker.sentence)
- `description` (Faker.paragraph)
- `severity` (low|medium|high|critical)
- `priority` (low|medium|high|critical)
- `status` (open|in_progress|resolved|closed)
- `assigned_to` (optional user)
- `environment` (dev|staging|production)
- `reproducibility` (always|sometimes|rarely)
- `root_cause` (None, set during investigation)

### Automation

#### AutomationRunFactory
```python
run = AutomationRunFactory.build(
    project_id="proj-123",
    kind="recorder",
    status="passed"
)
```

**Attributes:**
- `id` (sequence: run-0000000001, ...)
- `project_id` (string UUID)
- `kind` (recorder|autopilot|test_case)
- `name` (Faker.sentence)
- `status` (queued|running|passed|failed)
- `trigger` (manual|schedule|webhook)
- `environment` (dev|staging|production)
- `provenance` (fallback|<source>)
- `artifacts`, `metrics` (empty)
- `duration_ms` (None, set on completion)

#### AutomationScheduleFactory
```python
schedule = AutomationScheduleFactory.build(
    project_id="proj-123",
    cron_expression="0 0 * * *"  # Daily at midnight
)
```

**Attributes:**
- `id` (sequence: sched-0000000001, ...)
- `project_id` (string UUID)
- `kind` (recorder|autopilot)
- `name` (Faker.sentence)
- `cron_expression` (default: 0 0 * * *)
- `environment` (dev|staging)
- `is_active` (True)
- `next_run_at` (Faker.future_datetime, +1d)

## Batch Helpers

### create_test_project_with_suite()

Create a project and suite in one call:

```python
from tests.factories import create_test_project_with_suite

hierarchy = create_test_project_with_suite(
    session=db,
    name="My Project"
)
# Returns: {"project": TestManagementProject, "suite": TestSuite}
```

### create_test_run_with_results()

Create a test run with N results:

```python
from tests.factories import create_test_run_with_results

data = create_test_run_with_results(
    session=db,
    project_id="proj-123",
    num_cases=10,
    statuses=["passed", "failed", "skipped"]
)
# Returns: {"run": TestRun, "results": [TestResult, ...]}
```

### create_complete_project_hierarchy()

Create project + suite + folders + cases:

```python
from tests.factories import create_complete_project_hierarchy

hierarchy = create_complete_project_hierarchy(
    session=db,
    name="Full Project"
)
# Returns: {
#     "project": TestManagementProject,
#     "suite": TestSuite,
#     "folders": [TestFolder, TestFolder],
#     "cases": [TestCase, ...] (6 cases, 3 per folder)
# }
```

## Pytest Fixtures

All factories are wrapped in pytest fixtures in `conftest.py`:

```python
def test_with_factory(user_factory):
    user = user_factory.build()
    assert user is not None

def test_with_db_session(db_session, project_factory):
    project_factory._meta.sqlalchemy_session = db_session
    project = project_factory.create()
    # project now persisted to mock db_session
```

**Available fixtures:**
- `db_session` → Fresh mocked session (ADR-0013)
- `user_factory`, `project_factory`, `test_case_factory`, `test_run_factory`, `test_result_factory`
- `organization_factory`, `team_factory`, `defect_factory`, `automation_run_factory`

## Data Seeding

Use `scripts/seed_factories.py` to populate development database:

```bash
# Default: 5 projects, 10 users, 3 runs per project
python backend/scripts/seed_factories.py

# Custom counts
python backend/scripts/seed_factories.py --projects 20 --users 50

# Cleanup all seeded data
python backend/scripts/seed_factories.py --cleanup

# Verbose logging
python backend/scripts/seed_factories.py --verbose
```

## Best Practices

### 1. Use `.build()` for Unit Tests

Unit tests should NOT touch the database:

```python
def test_user_validation():
    user = UserFactory.build()  # No DB
    assert user.email is not None
```

### 2. Use `.create(session=...)` for Integration Tests

Integration tests need real database objects:

```python
def test_user_persistence(db_session):
    user = UserFactory.create(session=db_session)
    db_session.flush()
    assert user.id is not None
```

### 3. Override Attributes

Pass kwargs to customize any field:

```python
user = UserFactory.build(
    email="specific@test.com",
    is_active=False
)
```

### 4. Use SubFactory for Relations

Factories automatically create related objects:

```python
# Automatically creates a project
test_case = TestCaseFactory.build(title="My Test")
assert test_case.project is not None
```

To reuse the same parent:

```python
project = TestManagementProjectFactory.build()
case1 = TestCaseFactory.build(project=project)
case2 = TestCaseFactory.build(project=project)
```

### 5. Leverage post_generation for M2M

For many-to-many relationships:

```python
user = UserFactory.create(roles=[admin_role, tester_role])
```

### 6. Batch Creation

Create multiple instances:

```python
users = UserFactory.build_batch(5)  # 5 users in-memory
projects = ProjectFactory.create_batch(10, session=db)  # 10 persisted projects
```

### 7. Clean Event Loop (ADR-0013)

Each test gets a fresh event loop via `clean_event_loop` fixture:

```python
def test_async_operation(clean_event_loop, user_factory):
    user = user_factory.build()
    # clean_event_loop ensures async state is isolated
```

## Troubleshooting

### Import Error: factory-boy not installed

```bash
pip install factory-boy
```

### `sqlalchemy_session = None` error

Always pass `session=db_session` when using `.create()`:

```python
user = UserFactory.create(session=db_session)  # Correct
user = UserFactory.create()  # ERROR: session not set
```

### Unique constraint violations

Use unique attributes or change the default:

```python
user1 = UserFactory.build(email="alice@test.com")
user2 = UserFactory.build(email="bob@test.com")  # Different email
```

### Foreign key constraint errors

SubFactory fields are automatically populated. If you need to override:

```python
case = TestCaseFactory.build(project_id=existing_project.id)
```

## See Also

- [factory_boy Documentation](https://factoryboy.readthedocs.io/)
- [Faker Documentation](https://faker.readthedocs.io/)
- [ADR-0013: Test Isolation via Clean Event Loop](../../docs/adr/ADR-0013-test-isolation.md)
- [conftest.py](./conftest.py) — Fixture definitions
- [scripts/seed_factories.py](../scripts/seed_factories.py) — Data seeding script
