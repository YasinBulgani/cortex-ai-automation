"""Example tests demonstrating factory_boy usage patterns.

These are EXAMPLE tests showing how to use factories effectively in:
1. Unit tests (no DB, use .build())
2. Integration tests (with DB, use .create(session=...))
3. Fixtures (provide pre-built objects)

Run with: pytest tests/unit/test_factories_example.py -v
"""

from __future__ import annotations

import pytest


class TestFactoryBasicUsage:
    """Examples of basic factory_boy patterns."""

    def test_build_user_no_db(self):
        """In-memory user creation — no database needed."""
        from tests.factories import UserFactory

        user = UserFactory.build()

        assert user.id is not None
        assert user.email is not None
        assert user.full_name is not None
        assert user.is_active is True

    def test_build_with_custom_attributes(self):
        """Override default attributes."""
        from tests.factories import UserFactory

        user = UserFactory.build(
            email="alice@example.com",
            full_name="Alice",
            is_active=False,
        )

        assert user.email == "alice@example.com"
        assert user.full_name == "Alice"
        assert user.is_active is False

    def test_build_project(self):
        """Create a project with auto-generated fields."""
        from tests.factories import TestManagementProjectFactory

        project = TestManagementProjectFactory.build(
            name="E-Commerce Platform"
        )

        assert project.id is not None
        assert project.name == "E-Commerce Platform"
        assert project.status == "active"

    def test_subfactory_relationships(self):
        """SubFactory automatically creates related objects."""
        from tests.factories import TestCaseFactory

        # Project is automatically created via SubFactory
        test_case = TestCaseFactory.build(title="Login Test")

        assert test_case.project is not None
        assert test_case.project.id is not None
        assert test_case.title == "Login Test"

    def test_reuse_parent_in_subfactory(self):
        """Share the same parent object across multiple children."""
        from tests.factories import TestManagementProjectFactory, TestCaseFactory

        # Create parent once
        project = TestManagementProjectFactory.build()

        # Create multiple children pointing to same parent
        case1 = TestCaseFactory.build(project=project, title="Case 1")
        case2 = TestCaseFactory.build(project=project, title="Case 2")

        assert case1.project_id == case2.project_id == project.id

    def test_batch_creation(self):
        """Create multiple objects at once."""
        from tests.factories import UserFactory

        users = UserFactory.build_batch(5)

        assert len(users) == 5
        assert all(u.id is not None for u in users)
        # Emails are unique per sequence
        emails = {u.email for u in users}
        assert len(emails) == 5


class TestFactoryWithFixtures:
    """Using factories with pytest fixtures."""

    def test_with_user_factory_fixture(self, user_factory):
        """Use injected user factory fixture."""
        user = user_factory.build(email="bob@example.com")

        assert user.email == "bob@example.com"

    def test_with_project_factory_fixture(self, project_factory):
        """Use injected project factory fixture."""
        project = project_factory.build(name="Mobile App")

        assert project.name == "Mobile App"

    def test_with_test_case_factory_fixture(self, test_case_factory):
        """Use injected test case factory fixture."""
        test_case = test_case_factory.build(priority="critical")

        assert test_case.priority == "critical"

    def test_combining_multiple_factories(self, user_factory, project_factory):
        """Combine multiple factories in one test."""
        user = user_factory.build(full_name="Charlie")
        project = project_factory.build(name="Backend API")

        assert user.full_name == "Charlie"
        assert project.name == "Backend API"


class TestFactorySequenceGeneration:
    """Testing auto-generated sequences."""

    def test_email_sequence(self):
        """Emails auto-increment."""
        from tests.factories import UserFactory

        user1 = UserFactory.build()
        user2 = UserFactory.build()
        user3 = UserFactory.build()

        # Each gets unique email from sequence
        assert user1.email != user2.email != user3.email
        assert "user" in user1.email
        assert "@test.local" in user1.email

    def test_project_key_sequence(self):
        """Project keys auto-generate with sequence."""
        from tests.factories import TestManagementProjectFactory

        proj1 = TestManagementProjectFactory.build()
        proj2 = TestManagementProjectFactory.build()

        assert proj1.key.startswith("PROJ")
        assert proj2.key.startswith("PROJ")
        assert proj1.key != proj2.key

    def test_test_case_key_sequence(self):
        """Test case keys auto-increment."""
        from tests.factories import TestCaseFactory

        tc1 = TestCaseFactory.build()
        tc2 = TestCaseFactory.build()
        tc3 = TestCaseFactory.build()

        # Keys are like TC-00001, TC-00002, TC-00003
        assert "TC-" in tc1.case_key
        assert int(tc1.case_key.split("-")[1]) < int(tc2.case_key.split("-")[1])


class TestFactoryFakerIntegration:
    """Faker-generated realistic data."""

    def test_user_has_realistic_name(self):
        """Full names are realistic via Faker."""
        from tests.factories import UserFactory

        user = UserFactory.build()

        # Faker generates real-looking names
        assert user.full_name is not None
        assert len(user.full_name) > 0
        assert " " in user.full_name or len(user.full_name) > 3

    def test_project_has_realistic_description(self):
        """Descriptions are realistic paragraphs."""
        from tests.factories import TestManagementProjectFactory

        project = TestManagementProjectFactory.build()

        assert project.description is not None
        assert len(project.description) > 10

    def test_test_case_has_realistic_objective(self):
        """Test case objectives are realistic."""
        from tests.factories import TestCaseFactory

        test_case = TestCaseFactory.build()

        assert test_case.objective is not None

    def test_defect_priority_is_realistic(self):
        """Defect priorities cycle through realistic values."""
        from tests.factories import DefectFactory

        priorities = {DefectFactory.build().priority for _ in range(20)}

        # Should have multiple priority levels represented
        assert len(priorities) > 1
        assert priorities.issubset({"low", "medium", "high", "critical"})


class TestFactoryRandomization:
    """Testing randomized field generation."""

    def test_test_result_status_varies(self):
        """Test result status randomly varies."""
        from tests.factories import TestResultFactory

        statuses = {TestResultFactory.build().status for _ in range(20)}

        # Should generate different statuses
        assert len(statuses) > 1
        assert statuses.issubset({"passed", "failed", "skipped", "blocked"})

    def test_automation_run_kind_varies(self):
        """Automation run kind varies."""
        from tests.factories import AutomationRunFactory

        kinds = {AutomationRunFactory.build().kind for _ in range(20)}

        # Should have different automation kinds
        assert len(kinds) > 1

    def test_defect_severity_varies(self):
        """Defect severity varies."""
        from tests.factories import DefectFactory

        severities = {DefectFactory.build().severity for _ in range(20)}

        # Should have different severities represented
        assert len(severities) > 1


class TestBatchFactoryHelpers:
    """Testing batch helper functions."""

    def test_create_complete_project_hierarchy(self):
        """Helper creates full project hierarchy."""
        from tests.factories import create_complete_project_hierarchy

        hierarchy = create_complete_project_hierarchy()

        assert hierarchy["project"] is not None
        assert hierarchy["suite"] is not None
        assert len(hierarchy["folders"]) > 0
        assert len(hierarchy["cases"]) > 0

    def test_create_test_run_with_results(self):
        """Helper creates run with N results."""
        from tests.factories import create_test_run_with_results

        data = create_test_run_with_results(num_cases=10)

        assert data["run"] is not None
        assert len(data["results"]) == 10

    def test_create_test_run_with_custom_statuses(self):
        """Custom statuses in results."""
        from tests.factories import create_test_run_with_results

        data = create_test_run_with_results(
            num_cases=6,
            statuses=["passed", "failed"]
        )

        statuses = [r.status for r in data["results"]]
        # Should cycle through passed/failed
        assert "passed" in statuses
        assert "failed" in statuses


# ────────────────────────────────────────────────────────────────────────────
# Integration Tests (would need real DB) — examples only
# ────────────────────────────────────────────────────────────────────────────


class TestFactoryIntegrationExamples:
    """Examples of integration tests with database.

    These are NOT run by default because they require a real database.
    To enable: set DATABASE_URL env var and run:
        pytest tests/unit/test_factories_example.py::TestFactoryIntegrationExamples -v

    Requires: PostgreSQL with schema migrated.
    """

    @pytest.mark.skip(reason="Requires real database")
    def test_create_user_to_database(self, db_session):
        """Example: Create and persist a user."""
        from tests.factories import UserFactory

        # With real session, .create() persists
        user = UserFactory.create(
            session=db_session,
            email="persistence-test@example.com"
        )

        # Would be retrievable from database
        assert user.id is not None

    @pytest.mark.skip(reason="Requires real database")
    def test_create_project_hierarchy_to_database(self, db_session):
        """Example: Persist full hierarchy."""
        from tests.factories import create_complete_project_hierarchy

        hierarchy = create_complete_project_hierarchy(session=db_session)

        # All objects persisted
        assert hierarchy["project"].id is not None
        assert all(f.id is not None for f in hierarchy["folders"])
        assert all(c.id is not None for c in hierarchy["cases"])
