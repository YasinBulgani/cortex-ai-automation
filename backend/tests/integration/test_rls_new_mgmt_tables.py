"""RLS tenant isolation for new management tables (5 tables).

Tests that RLS policies correctly isolate multi-tenant data on:
  - test_management_shared_steps
  - mgmt_comments
  - test_management_exploration_sessions
  - mgmt_design_technique_runs
  - test_management_case_dependencies

Requires: live PostgreSQL with migration 20260609_0001 applied.
"""

from __future__ import annotations

import uuid
from typing import Optional

import pytest
from sqlalchemy import text

from app.infra.database import SessionLocal

pytestmark = pytest.mark.integration

# Tenants
TENANT_A = "00000000-0000-0000-0000-000000000001"
TENANT_B = "00000000-0000-0000-0000-000000000099"


@pytest.fixture
def db_session():
    """Provide a DB session and clean up after tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _ensure_tenant(db, tenant_id: str) -> None:
    """Create tenant if not exists."""
    db.execute(text("""
        INSERT INTO tenants (id, slug, display_name, plan)
        VALUES (:id, :slug, 'Test Tenant', 'free')
        ON CONFLICT (slug) DO NOTHING
    """), {"id": tenant_id, "slug": f"test-{tenant_id[:8]}"})
    db.commit()


def _query_with_tenant(db, tenant_id: str, query: str, params: dict = None) -> list:
    """Execute a query with tenant context set."""
    if params is None:
        params = {}

    # Set tenant context
    db.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))

    result = db.execute(text(query), params).fetchall()
    return result


def _create_project(db, tenant_id: str, project_id: Optional[str] = None) -> str:
    """Create a test management project; return project_id."""
    if project_id is None:
        project_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO test_management_projects (id, tenant_id, name, description)
        VALUES (:id, :tenant_id, :name, :desc)
        ON CONFLICT DO NOTHING
    """), {
        "id": project_id,
        "tenant_id": tenant_id,
        "name": f"Project {project_id[:8]}",
        "desc": "Test project",
    })
    db.commit()
    return project_id


def _create_case(db, project_id: str, case_id: Optional[str] = None) -> str:
    """Create a test_management_case; return case_id."""
    if case_id is None:
        case_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO test_management_cases (id, project_id, name, description)
        VALUES (:id, :project_id, :name, :desc)
        ON CONFLICT DO NOTHING
    """), {
        "id": case_id,
        "project_id": project_id,
        "name": f"Case {case_id[:8]}",
        "desc": "Test case",
    })
    db.commit()
    return case_id


class TestSharedStepsRLS:
    """RLS for test_management_shared_steps (has project_id)."""

    def test_shared_steps_visible_to_own_tenant(self, db_session) -> None:
        """User from tenant A can see shared steps in tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        project_a = _create_project(db_session, TENANT_A)

        # Insert step as tenant A
        step_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO test_management_shared_steps (id, project_id, name)
            VALUES (:id, :project_id, :name)
        """), {"id": step_id, "project_id": project_a, "name": "Test Step A"})
        db_session.commit()

        # Query as tenant A
        result = _query_with_tenant(
            db_session, TENANT_A,
            f"SELECT id FROM test_management_shared_steps WHERE id = '{step_id}'"
        )
        assert len(result) == 1, "Tenant A should see own shared step"

    def test_shared_steps_hidden_from_other_tenant(self, db_session) -> None:
        """User from tenant B cannot see shared steps from tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        _ensure_tenant(db_session, TENANT_B)

        project_a = _create_project(db_session, TENANT_A)

        # Insert step as tenant A
        step_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO test_management_shared_steps (id, project_id, name)
            VALUES (:id, :project_id, :name)
        """), {"id": step_id, "project_id": project_a, "name": "Secret Step A"})
        db_session.commit()

        # Query as tenant B
        result = _query_with_tenant(
            db_session, TENANT_B,
            f"SELECT id FROM test_management_shared_steps WHERE id = '{step_id}'"
        )
        assert len(result) == 0, "Tenant B should NOT see Tenant A's shared steps"


class TestMgmtCommentsRLS:
    """RLS for mgmt_comments (has project_id)."""

    def test_comments_visible_to_own_tenant(self, db_session) -> None:
        """User from tenant A can see comments in tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        project_a = _create_project(db_session, TENANT_A)

        # Insert comment as tenant A
        comment_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO mgmt_comments (id, tenant_id, project_id, entity_type, entity_id, body_md)
            VALUES (:id, :tenant_id, :project_id, :entity_type, :entity_id, :body)
        """), {
            "id": comment_id,
            "tenant_id": TENANT_A,
            "project_id": project_a,
            "entity_type": "case",
            "entity_id": str(uuid.uuid4()),
            "body": "Test comment",
        })
        db_session.commit()

        # Query as tenant A
        result = _query_with_tenant(
            db_session, TENANT_A,
            f"SELECT id FROM mgmt_comments WHERE id = '{comment_id}'"
        )
        assert len(result) == 1, "Tenant A should see own comments"

    def test_comments_hidden_from_other_tenant(self, db_session) -> None:
        """User from tenant B cannot see comments from tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        _ensure_tenant(db_session, TENANT_B)

        project_a = _create_project(db_session, TENANT_A)

        # Insert comment as tenant A
        comment_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO mgmt_comments (id, tenant_id, project_id, entity_type, entity_id, body_md)
            VALUES (:id, :tenant_id, :project_id, :entity_type, :entity_id, :body)
        """), {
            "id": comment_id,
            "tenant_id": TENANT_A,
            "project_id": project_a,
            "entity_type": "case",
            "entity_id": str(uuid.uuid4()),
            "body": "Secret comment",
        })
        db_session.commit()

        # Query as tenant B
        result = _query_with_tenant(
            db_session, TENANT_B,
            f"SELECT id FROM mgmt_comments WHERE id = '{comment_id}'"
        )
        assert len(result) == 0, "Tenant B should NOT see Tenant A's comments"


class TestExplorationSessionsRLS:
    """RLS for test_management_exploration_sessions (has project_id)."""

    def test_sessions_visible_to_own_tenant(self, db_session) -> None:
        """User from tenant A can see exploration sessions in tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        project_a = _create_project(db_session, TENANT_A)

        # Insert session as tenant A
        session_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO test_management_exploration_sessions
            (id, project_id, tester_id, duration_seconds)
            VALUES (:id, :project_id, :tester_id, :duration)
        """), {
            "id": session_id,
            "project_id": project_a,
            "tester_id": str(uuid.uuid4()),
            "duration": 3600,
        })
        db_session.commit()

        # Query as tenant A
        result = _query_with_tenant(
            db_session, TENANT_A,
            f"SELECT id FROM test_management_exploration_sessions WHERE id = '{session_id}'"
        )
        assert len(result) == 1, "Tenant A should see own exploration sessions"

    def test_sessions_hidden_from_other_tenant(self, db_session) -> None:
        """User from tenant B cannot see exploration sessions from tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        _ensure_tenant(db_session, TENANT_B)

        project_a = _create_project(db_session, TENANT_A)

        # Insert session as tenant A
        session_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO test_management_exploration_sessions
            (id, project_id, tester_id, duration_seconds)
            VALUES (:id, :project_id, :tester_id, :duration)
        """), {
            "id": session_id,
            "project_id": project_a,
            "tester_id": str(uuid.uuid4()),
            "duration": 3600,
        })
        db_session.commit()

        # Query as tenant B
        result = _query_with_tenant(
            db_session, TENANT_B,
            f"SELECT id FROM test_management_exploration_sessions WHERE id = '{session_id}'"
        )
        assert len(result) == 0, "Tenant B should NOT see Tenant A's exploration sessions"


class TestDesignTechniqueRunsRLS:
    """RLS for mgmt_design_technique_runs (has project_id)."""

    def test_runs_visible_to_own_tenant(self, db_session) -> None:
        """User from tenant A can see design technique runs in tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        project_a = _create_project(db_session, TENANT_A)

        # Insert run as tenant A
        run_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO mgmt_design_technique_runs
            (id, tenant_id, project_id, technique, source)
            VALUES (:id, :tenant_id, :project_id, :technique, :source)
        """), {
            "id": run_id,
            "tenant_id": TENANT_A,
            "project_id": project_a,
            "technique": "BVA",
            "source": "manual",
        })
        db_session.commit()

        # Query as tenant A
        result = _query_with_tenant(
            db_session, TENANT_A,
            f"SELECT id FROM mgmt_design_technique_runs WHERE id = '{run_id}'"
        )
        assert len(result) == 1, "Tenant A should see own design technique runs"

    def test_runs_hidden_from_other_tenant(self, db_session) -> None:
        """User from tenant B cannot see design technique runs from tenant A's project."""
        _ensure_tenant(db_session, TENANT_A)
        _ensure_tenant(db_session, TENANT_B)

        project_a = _create_project(db_session, TENANT_A)

        # Insert run as tenant A
        run_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO mgmt_design_technique_runs
            (id, tenant_id, project_id, technique, source)
            VALUES (:id, :tenant_id, :project_id, :technique, :source)
        """), {
            "id": run_id,
            "tenant_id": TENANT_A,
            "project_id": project_a,
            "technique": "BVA",
            "source": "manual",
        })
        db_session.commit()

        # Query as tenant B
        result = _query_with_tenant(
            db_session, TENANT_B,
            f"SELECT id FROM mgmt_design_technique_runs WHERE id = '{run_id}'"
        )
        assert len(result) == 0, "Tenant B should NOT see Tenant A's design technique runs"


class TestCaseDependenciesRLS:
    """RLS for test_management_case_dependencies (2-hop via case → project)."""

    def test_dependencies_visible_to_own_tenant(self, db_session) -> None:
        """User from tenant A can see case dependencies in tenant A's cases."""
        _ensure_tenant(db_session, TENANT_A)
        project_a = _create_project(db_session, TENANT_A)
        case_a1 = _create_case(db_session, project_a)
        case_a2 = _create_case(db_session, project_a)

        # Insert dependency as tenant A
        dep_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO test_management_case_dependencies
            (id, case_id, depends_on_id, dep_type)
            VALUES (:id, :case_id, :depends_on_id, :dep_type)
        """), {
            "id": dep_id,
            "case_id": case_a1,
            "depends_on_id": case_a2,
            "dep_type": "blocks",
        })
        db_session.commit()

        # Query as tenant A
        result = _query_with_tenant(
            db_session, TENANT_A,
            f"SELECT id FROM test_management_case_dependencies WHERE id = '{dep_id}'"
        )
        assert len(result) == 1, "Tenant A should see own case dependencies"

    def test_dependencies_hidden_from_other_tenant(self, db_session) -> None:
        """User from tenant B cannot see case dependencies from tenant A's cases."""
        _ensure_tenant(db_session, TENANT_A)
        _ensure_tenant(db_session, TENANT_B)

        project_a = _create_project(db_session, TENANT_A)
        case_a1 = _create_case(db_session, project_a)
        case_a2 = _create_case(db_session, project_a)

        # Insert dependency as tenant A
        dep_id = str(uuid.uuid4())
        db_session.execute(text(f"SET LOCAL app.current_tenant = '{TENANT_A}'"))
        db_session.execute(text("""
            INSERT INTO test_management_case_dependencies
            (id, case_id, depends_on_id, dep_type)
            VALUES (:id, :case_id, :depends_on_id, :dep_type)
        """), {
            "id": dep_id,
            "case_id": case_a1,
            "depends_on_id": case_a2,
            "dep_type": "blocks",
        })
        db_session.commit()

        # Query as tenant B
        result = _query_with_tenant(
            db_session, TENANT_B,
            f"SELECT id FROM test_management_case_dependencies WHERE id = '{dep_id}'"
        )
        assert len(result) == 0, "Tenant B should NOT see Tenant A's case dependencies"
