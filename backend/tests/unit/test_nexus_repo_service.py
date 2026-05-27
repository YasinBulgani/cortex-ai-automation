"""Unit tests for nexus_repo service layer.

No real database required — SQLAlchemy Session is fully mocked.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, call
    from app.domains.nexus_repo import service as svc
    from app.domains.nexus_repo.models import NexusProject, NexusScenario, NexusCrawlJob
    from app.domains.nexus_repo.schemas import (
        NexusProjectCreate,
        NexusProjectUpdate,
        NexusScenarioCreate,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="nexus_repo domain not importable")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _mock_db() -> MagicMock:
    """Return a fresh MagicMock that looks like a SQLAlchemy Session."""
    db = MagicMock()
    # Make query(...).filter(...).first() / .all() / .offset().limit().all() chainable
    chain = MagicMock()
    db.query.return_value = chain
    chain.filter.return_value = chain
    chain.order_by.return_value = chain
    chain.offset.return_value = chain
    chain.limit.return_value = chain
    return db, chain


# ── list_projects ──────────────────────────────────────────────────────────────

class TestListProjects:
    def test_returns_all_non_archived_by_default(self):
        db, chain = _mock_db()
        fake_projects = [MagicMock(spec=NexusProject), MagicMock(spec=NexusProject)]
        chain.all.return_value = fake_projects

        result = svc.list_projects(db)

        db.query.assert_called_once_with(NexusProject)
        assert result == fake_projects

    def test_offset_and_limit_forwarded(self):
        db, chain = _mock_db()
        chain.all.return_value = []

        svc.list_projects(db, skip=10, limit=5)

        chain.offset.assert_called_once_with(10)
        chain.limit.assert_called_once_with(5)

    def test_archived_flag_forwarded(self):
        db, chain = _mock_db()
        chain.all.return_value = []

        svc.list_projects(db, archived=True)

        # filter is called with the archived== expression; just confirm it was called
        assert chain.filter.called


# ── get_project ────────────────────────────────────────────────────────────────

class TestGetProject:
    def test_returns_project_when_found(self):
        db, chain = _mock_db()
        fake = MagicMock(spec=NexusProject)
        chain.first.return_value = fake

        result = svc.get_project(db, "proj-123")

        assert result is fake

    def test_returns_none_when_not_found(self):
        db, chain = _mock_db()
        chain.first.return_value = None

        result = svc.get_project(db, "nonexistent")

        assert result is None


# ── create_project ─────────────────────────────────────────────────────────────

class TestCreateProject:
    def _make_create_data(self) -> "NexusProjectCreate":
        return NexusProjectCreate(
            name="Demo Project",
            repo_url="https://github.com/acme/demo",
        )

    def test_adds_commits_and_refreshes(self):
        db, _chain = _mock_db()

        data = self._make_create_data()
        result = svc.create_project(db, data, created_by="tester")

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_returns_refreshed_project(self):
        db, _chain = _mock_db()
        data = self._make_create_data()

        # db.refresh mutates the object in-place; the return value is the same instance
        result = svc.create_project(db, data)

        assert isinstance(result, NexusProject)

    def test_created_by_passed_through(self):
        db, _chain = _mock_db()
        data = self._make_create_data()

        project = svc.create_project(db, data, created_by="alice")

        assert project.created_by == "alice"


# ── update_project ─────────────────────────────────────────────────────────────

class TestUpdateProject:
    def test_sets_fields_and_commits(self):
        db, _chain = _mock_db()
        project = NexusProject(
            name="Old Name",
            repo_url="https://github.com/acme/old",
        )
        update_data = NexusProjectUpdate(name="New Name")

        result = svc.update_project(db, project, update_data)

        assert result.name == "New Name"
        db.commit.assert_called_once()
        db.refresh.assert_called_once()


# ── archive_project ────────────────────────────────────────────────────────────

class TestArchiveProject:
    def test_sets_archived_true(self):
        db, _chain = _mock_db()
        project = NexusProject(
            name="P",
            repo_url="https://github.com/acme/p",
            archived=False,
        )

        svc.archive_project(db, project)

        assert project.archived is True
        db.commit.assert_called_once()


# ── list_scenarios ─────────────────────────────────────────────────────────────

class TestListScenarios:
    def test_filters_by_project_id(self):
        db, chain = _mock_db()
        chain.all.return_value = []

        svc.list_scenarios(db, "proj-abc")

        db.query.assert_called_once_with(NexusScenario)
        # filter must have been invoked at least for project_id
        assert chain.filter.called

    def test_type_filter_applies_second_filter(self):
        db, chain = _mock_db()
        chain.all.return_value = []

        svc.list_scenarios(db, "proj-abc", type_filter="automation")

        # filter called at least twice (project_id + type)
        assert chain.filter.call_count >= 2

    def test_status_filter_applies_additional_filter(self):
        db, chain = _mock_db()
        chain.all.return_value = []

        svc.list_scenarios(db, "proj-abc", status_filter="approved")

        assert chain.filter.call_count >= 2


# ── create_scenario ────────────────────────────────────────────────────────────

class TestCreateScenario:
    def test_adds_commits_and_refreshes(self):
        db, _chain = _mock_db()
        data = NexusScenarioCreate(
            title="Login happy path",
            type="automation",
        )

        result = svc.create_scenario(db, "proj-xyz", data, created_by="bot")

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_project_id_and_created_by_set(self):
        db, _chain = _mock_db()
        data = NexusScenarioCreate(title="Edge case", type="manual")

        scenario = svc.create_scenario(db, "proj-xyz", data, created_by="qa-bot")

        assert scenario.project_id == "proj-xyz"
        assert scenario.created_by == "qa-bot"


# ── delete_scenario ────────────────────────────────────────────────────────────

class TestDeleteScenario:
    def test_deletes_and_commits(self):
        db, _chain = _mock_db()
        scenario = MagicMock(spec=NexusScenario)

        svc.delete_scenario(db, scenario)

        db.delete.assert_called_once_with(scenario)
        db.commit.assert_called_once()
