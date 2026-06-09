"""Test data factories using factory_boy for Neurex QA platform.

Provides lightweight factories for User, Project, TestCase, TestRun, and related
models. Factories are pure — they do not mutate the database. Use:
    - .create() to persist to DB (requires active session)
    - .build() to get in-memory object (no DB)
    - .stub() to get plain dict (fastest for mocks)

IMPORTANT: All factories must be paired with a pytest fixture that handles
session teardown. See conftest.py for integration examples.

ADR-0013: Factories must NOT share fixtures across tests. Each test gets
a fresh instance to prevent async event-loop pollution.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone as _tz
from typing import Any, Optional

try:
    import factory
    from factory.sqlalchemy import SQLAlchemyModelFactory
except ImportError:
    raise ImportError(
        "factory-boy not installed. Run: pip install factory-boy\n"
        "This is required for test data factories."
    )

from faker import Faker

from app.infra.models import (
    Organization,
    Role,
    RolePermission,
    Team,
    TeamMember,
    User,
    ProjectMember,
    Invitation,
    RefreshToken,
    AutomationRun,
    AutomationSchedule,
)
from app.domains.test_management.models import (
    TestManagementProject,
    TestSuite,
    TestFolder,
    TestCase,
    TestPlan,
    TestRun,
    TestResult,
    Defect,
)

fake = Faker(["tr_TR", "en_US"])


def _uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(_tz.utc)


# ────────────────────────────────────────────────────────────────────────────
# Core Identity & Authorization Factories
# ────────────────────────────────────────────────────────────────────────────


class RoleFactory(SQLAlchemyModelFactory):
    """Factory for Role model (core RBAC role)."""

    class Meta:
        model = Role
        # In tests, pass session=db_session to .create()
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    name = factory.Sequence(lambda n: f"role_{n}")


class RolePermissionFactory(SQLAlchemyModelFactory):
    """Factory for RolePermission model."""

    class Meta:
        model = RolePermission
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    role_id = factory.LazyFunction(_uuid)
    permission = factory.Sequence(lambda n: f"permission_{n}")
    role = factory.SubFactory(RoleFactory)


class OrganizationFactory(SQLAlchemyModelFactory):
    """Factory for Organization model."""

    class Meta:
        model = Organization
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    name = factory.Faker("company")
    slug = factory.LazyAttribute(lambda o: fake.slug())
    plan_code = factory.Faker("random_element", elements=["free", "pro", "enterprise"])
    settings = {}


class TeamFactory(SQLAlchemyModelFactory):
    """Factory for Team model."""

    class Meta:
        model = Team
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    organization = factory.SubFactory(OrganizationFactory)
    organization_id = factory.SelfAttribute("organization.id")
    name = factory.Faker("word")
    slug = factory.LazyAttribute(lambda t: t.name.lower().replace(" ", "-"))
    description = factory.Faker("sentence")


class UserFactory(SQLAlchemyModelFactory):
    """Factory for User model with password hashing.

    Usage:
        user = UserFactory.create(session=db)  # Persist
        user = UserFactory.build()  # In-memory only
        user_dict = UserFactory.stub()  # Plain dict (fastest)
    """

    class Meta:
        model = User
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    email = factory.Sequence(lambda n: f"user{n}@test.local")
    password_hash = "hashed_password_placeholder"  # Use mocks for real testing
    full_name = factory.Faker("name")
    phone = factory.Faker("phone_number")
    department = factory.Faker("job")
    tenant_id = "00000000-0000-0000-0000-000000000001"
    is_active = True
    mfa_enabled = False
    totp_secret = None
    mfa_backup_codes = None
    created_at = factory.LazyFunction(_utcnow)

    @factory.post_generation
    def roles(obj, create, extracted, **kwargs):
        """Add roles to user (many-to-many)."""
        if not create:
            return
        if extracted:
            for role in extracted:
                obj.roles.append(role)


class TeamMemberFactory(SQLAlchemyModelFactory):
    """Factory for TeamMember model."""

    class Meta:
        model = TeamMember
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    team = factory.SubFactory(TeamFactory)
    team_id = factory.SelfAttribute("team.id")
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    role = factory.Faker("random_element", elements=["member", "lead", "admin"])
    joined_at = factory.LazyFunction(_utcnow)


class ProjectMemberFactory(SQLAlchemyModelFactory):
    """Factory for ProjectMember model."""

    class Meta:
        model = ProjectMember
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    project = factory.SubFactory("tests.factories.TestManagementProjectFactory")
    project_id = factory.SelfAttribute("project.id")
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    role = factory.Faker("random_element", elements=["viewer", "editor", "tester", "admin"])
    added_at = factory.LazyFunction(_utcnow)


class InvitationFactory(SQLAlchemyModelFactory):
    """Factory for Invitation model."""

    class Meta:
        model = Invitation
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    organization = factory.SubFactory(OrganizationFactory)
    organization_id = factory.SelfAttribute("organization.id")
    team = factory.SubFactory(TeamFactory)
    team_id = factory.SelfAttribute("team.id")
    email = factory.Sequence(lambda n: f"invite{n}@test.local")
    role = "member"
    token_hash = factory.LazyFunction(lambda: fake.sha1())
    invited_by = None
    expires_at = factory.Faker("future_datetime", end_date="+30d", tzinfo=_tz.utc)
    accepted_at = None
    revoked_at = None
    created_at = factory.LazyFunction(_utcnow)


class RefreshTokenFactory(SQLAlchemyModelFactory):
    """Factory for RefreshToken model."""

    class Meta:
        model = RefreshToken
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    token_hash = factory.LazyFunction(lambda: fake.sha256())
    expires_at = factory.Faker("future_datetime", end_date="+7d", tzinfo=_tz.utc)
    revoked = False
    created_at = factory.LazyFunction(_utcnow)
    user_agent = factory.Faker("user_agent")


# ────────────────────────────────────────────────────────────────────────────
# Test Management Factories
# ────────────────────────────────────────────────────────────────────────────


class TestManagementProjectFactory(SQLAlchemyModelFactory):
    """Factory for TestManagementProject model."""

    class Meta:
        model = TestManagementProject
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    tenant_id = "00000000-0000-0000-0000-000000000001"
    name = factory.Faker("catch_phrase")
    key = factory.LazyAttribute(lambda p: fake.bothify(text="???-####", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    description = factory.Faker("text", max_nb_chars=200)
    status = "active"
    created_by = None
    created_at = factory.LazyFunction(_utcnow)
    updated_at = factory.LazyFunction(_utcnow)
    settings_data = {}


class TestSuiteFactory(SQLAlchemyModelFactory):
    """Factory for TestSuite model."""

    class Meta:
        model = TestSuite
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    project = factory.SubFactory(TestManagementProjectFactory)
    project_id = factory.SelfAttribute("project.id")
    name = factory.Faker("word")
    description = factory.Faker("sentence")
    order_index = factory.Sequence(lambda n: n)
    status = "active"
    created_at = factory.LazyFunction(_utcnow)


class TestFolderFactory(SQLAlchemyModelFactory):
    """Factory for TestFolder model."""

    class Meta:
        model = TestFolder
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    suite = factory.SubFactory(TestSuiteFactory)
    suite_id = factory.SelfAttribute("suite.id")
    parent_id = None
    name = factory.Faker("word")
    path = factory.LazyAttribute(lambda f: f"{f.name}/")
    order_index = 0
    created_at = factory.LazyFunction(_utcnow)


class TestCaseFactory(SQLAlchemyModelFactory):
    """Factory for TestCase model."""

    class Meta:
        model = TestCase
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    project = factory.SubFactory(TestManagementProjectFactory)
    project_id = factory.SelfAttribute("project.id")
    suite = None
    suite_id = None
    folder = None
    folder_id = None
    case_key = factory.Sequence(lambda n: f"TC-{n:05d}")
    title = factory.Faker("sentence")
    objective = factory.Faker("paragraph")
    preconditions = factory.Faker("sentence")
    test_data = {}
    step_instructions = factory.Faker("text", max_nb_chars=300)
    expected_result = factory.Faker("text", max_nb_chars=200)
    priority = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])
    status = "active"
    archived = False
    is_automated = False
    automation_framework = None
    test_type = factory.Faker("random_element", elements=["functional", "regression", "smoke", "performance"])
    tags = []
    custom_attributes = {}
    coverage_areas = []
    created_by = None
    created_at = factory.LazyFunction(_utcnow)
    updated_at = factory.LazyFunction(_utcnow)


class TestPlanFactory(SQLAlchemyModelFactory):
    """Factory for TestPlan model."""

    class Meta:
        model = TestPlan
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    project = factory.SubFactory(TestManagementProjectFactory)
    project_id = factory.SelfAttribute("project.id")
    name = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("paragraph")
    plan_type = factory.Faker("random_element", elements=["manual", "automated", "hybrid"])
    status = "draft"
    start_date = factory.Faker("date_time", tzinfo=_tz.utc)
    end_date = factory.Faker("future_datetime", end_date="+30d", tzinfo=_tz.utc)
    created_by = None
    created_at = factory.LazyFunction(_utcnow)
    updated_at = factory.LazyFunction(_utcnow)


class TestRunFactory(SQLAlchemyModelFactory):
    """Factory for TestRun model."""

    class Meta:
        model = TestRun
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    project = factory.SubFactory(TestManagementProjectFactory)
    project_id = factory.SelfAttribute("project.id")
    plan = None
    plan_id = None
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("paragraph")
    status = "pending"
    run_type = "manual"
    assigned_tester = None
    assigned_tester_id = None
    environment = factory.Faker("random_element", elements=["dev", "staging", "production"])
    os = factory.Faker("random_element", elements=["Windows", "macOS", "Linux"])
    browser = factory.Faker("random_element", elements=["Chrome", "Firefox", "Safari", "Edge"])
    start_date = None
    end_date = None
    total_cases = 0
    passed_cases = 0
    failed_cases = 0
    skipped_cases = 0
    duration_seconds = None
    created_by = None
    created_at = factory.LazyFunction(_utcnow)
    updated_at = factory.LazyFunction(_utcnow)


class TestResultFactory(SQLAlchemyModelFactory):
    """Factory for TestResult model."""

    class Meta:
        model = TestResult
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    test_run = factory.SubFactory(TestRunFactory)
    test_run_id = factory.SelfAttribute("test_run.id")
    test_case = factory.SubFactory(TestCaseFactory)
    test_case_id = factory.SelfAttribute("test_case.id")
    status = factory.Faker("random_element", elements=["passed", "failed", "skipped", "blocked"])
    start_time = factory.Faker("date_time", tzinfo=_tz.utc)
    end_time = factory.Faker("date_time", tzinfo=_tz.utc)
    duration_seconds = factory.Faker("pyint", min_value=1, max_value=300)
    error_message = None
    actual_result = factory.Faker("paragraph")
    attachments = []
    created_by = None
    created_at = factory.LazyFunction(_utcnow)


class DefectFactory(SQLAlchemyModelFactory):
    """Factory for Defect model."""

    class Meta:
        model = Defect
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(_uuid)
    project = factory.SubFactory(TestManagementProjectFactory)
    project_id = factory.SelfAttribute("project.id")
    test_case = None
    test_case_id = None
    test_result = None
    test_result_id = None
    title = factory.Faker("sentence")
    description = factory.Faker("paragraph")
    defect_key = factory.Sequence(lambda n: f"DEF-{n:05d}")
    severity = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])
    priority = factory.Faker("random_element", elements=["low", "medium", "high", "critical"])
    status = "open"
    assigned_to = None
    assigned_to_id = None
    discovered_date = factory.Faker("date_time", tzinfo=_tz.utc)
    target_fix_date = factory.Faker("future_datetime", end_date="+30d", tzinfo=_tz.utc)
    resolution_date = None
    root_cause = None
    environment = factory.Faker("random_element", elements=["dev", "staging", "production"])
    reproducibility = factory.Faker("random_element", elements=["always", "sometimes", "rarely"])
    attachments = []
    custom_attributes = {}
    created_by = None
    created_at = factory.LazyFunction(_utcnow)
    updated_at = factory.LazyFunction(_utcnow)


# ────────────────────────────────────────────────────────────────────────────
# Automation & Integration Factories
# ────────────────────────────────────────────────────────────────────────────


class AutomationRunFactory(SQLAlchemyModelFactory):
    """Factory for AutomationRun model."""

    class Meta:
        model = AutomationRun
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: f"run-{n:010d}")
    project_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    kind = factory.Faker("random_element", elements=["recorder", "autopilot", "test_case"])
    name = factory.Faker("sentence")
    status = "queued"
    trigger = factory.Faker("random_element", elements=["manual", "schedule", "webhook"])
    environment = factory.Faker("random_element", elements=["dev", "staging", "production"])
    device = None
    target = None
    provenance = "fallback"
    created_by = None
    retry_of = None
    error = None
    artifacts = []
    metrics = {}
    next_action = None
    run_metadata = {}
    created_at = factory.LazyFunction(_utcnow)
    started_at = None
    finished_at = None
    duration_ms = None


class AutomationScheduleFactory(SQLAlchemyModelFactory):
    """Factory for AutomationSchedule model."""

    class Meta:
        model = AutomationSchedule
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: f"sched-{n:010d}")
    project_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    kind = "recorder"
    name = factory.Faker("sentence")
    cron_expression = "0 0 * * *"  # Daily at midnight
    environment = factory.Faker("random_element", elements=["dev", "staging"])
    device = None
    target = None
    run_metadata = {}
    is_active = True
    created_by = None
    created_at = factory.LazyFunction(_utcnow)
    last_run_at = None
    next_run_at = factory.Faker("future_datetime", end_date="+1d", tzinfo=_tz.utc)


# ────────────────────────────────────────────────────────────────────────────
# Batch Factory Helpers
# ────────────────────────────────────────────────────────────────────────────


def create_test_project_with_suite(session=None, **overrides) -> dict[str, Any]:
    """Create a project with an associated suite in one shot.

    Returns:
        {
            "project": TestManagementProject,
            "suite": TestSuite,
        }
    """
    project = TestManagementProjectFactory.create(session=session, **overrides)
    suite = TestSuiteFactory.create(session=session, project_id=project.id)
    return {"project": project, "suite": suite}


def create_test_run_with_results(
    session=None,
    num_cases: int = 5,
    statuses: Optional[list[str]] = None,
    **overrides,
) -> dict[str, Any]:
    """Create a test run with associated results.

    Args:
        session: SQLAlchemy session for persistence.
        num_cases: Number of test results to create.
        statuses: List of statuses to use cyclically. Default: ["passed", "failed", "skipped"].
        **overrides: Kwargs to pass to TestRunFactory.

    Returns:
        {
            "run": TestRun,
            "results": [TestResult, ...],
        }
    """
    if statuses is None:
        statuses = ["passed", "failed", "skipped"]

    run = TestRunFactory.create(session=session, **overrides)
    results = []
    for i in range(num_cases):
        result = TestResultFactory.create(
            session=session,
            test_run_id=run.id,
            status=statuses[i % len(statuses)],
        )
        results.append(result)

    return {"run": run, "results": results}


def create_complete_project_hierarchy(session=None, **overrides) -> dict[str, Any]:
    """Create a full project hierarchy: project → suite → folder → cases.

    Returns:
        {
            "project": TestManagementProject,
            "suite": TestSuite,
            "folders": [TestFolder, ...],
            "cases": [TestCase, ...],
        }
    """
    project = TestManagementProjectFactory.create(session=session, **overrides)
    suite = TestSuiteFactory.create(session=session, project_id=project.id)

    # Create 2 folders
    folders = [
        TestFolderFactory.create(session=session, suite_id=suite.id, name="Smoke Tests"),
        TestFolderFactory.create(session=session, suite_id=suite.id, name="Regression Tests"),
    ]

    # Create 3 cases per folder
    cases = []
    for folder in folders:
        for i in range(3):
            case = TestCaseFactory.create(
                session=session,
                project_id=project.id,
                suite_id=suite.id,
                folder_id=folder.id,
                title=f"{folder.name} - Case {i+1}",
            )
            cases.append(case)

    return {
        "project": project,
        "suite": suite,
        "folders": folders,
        "cases": cases,
    }
