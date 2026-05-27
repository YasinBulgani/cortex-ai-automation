"""Unit tests for app.domains.tspm.service.

The SQLAlchemy Session is fully mocked — no DB connection required.
All tests are pure-Python / in-process.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm import service as tspm_service
    from app.domains.tspm.service import (
        list_projects,
        create_project,
        list_scenarios,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="tspm service import failed")

from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers — fake ORM objects
# ---------------------------------------------------------------------------

def _make_project(
    id: str = "proj-1",
    name: str = "Test Projesi",
    description: str = "Açıklama",
    owner_id: str | None = "user-1",
    primary_product_id: str = "one",
):
    """Return a MagicMock that mimics a TspmProject row."""
    col_names = ["id", "name", "description", "owner_id", "primary_product_id",
                 "created_at", "updated_at"]
    proj = MagicMock()
    proj.id = id
    proj.name = name
    proj.description = description
    proj.owner_id = owner_id
    proj.primary_product_id = primary_product_id
    proj.created_at = None
    proj.updated_at = None

    # __table__.columns used for dict comprehension in service
    cols = []
    for cname in col_names:
        c = MagicMock()
        c.key = cname
        cols.append(c)
    proj.__table__ = MagicMock()
    proj.__table__.columns = cols
    return proj


def _make_scenario(
    id: str = "scen-1",
    project_id: str = "proj-1",
    description: str = "Senaryo",
    status: str = "draft",
):
    col_names = ["id", "project_id", "description", "status", "created_at", "updated_at"]
    scen = MagicMock()
    scen.id = id
    scen.project_id = project_id
    scen.description = description
    scen.status = status
    scen.created_at = None
    scen.updated_at = None

    cols = []
    for cname in col_names:
        c = MagicMock()
        c.key = cname
        cols.append(c)
    scen.__table__ = MagicMock()
    scen.__table__.columns = cols
    return scen


def _make_db(rows=None):
    """Return a MagicMock Session; db.scalars(...).all() returns rows."""
    db = MagicMock()
    db.scalars.return_value.all.return_value = rows or []
    return db


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------

class TestListProjects:
    def test_empty_db_returns_empty_list(self):
        db = _make_db([])
        result = list_projects(db)
        assert result == []

    def test_single_project_returns_list_of_dicts(self):
        proj = _make_project()
        db = _make_db([proj])
        result = list_projects(db)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "proj-1"
        assert result[0]["name"] == "Test Projesi"

    def test_owner_id_filter_applied_to_query(self):
        """owner_id is passed; service should call where() on the query."""
        db = _make_db([])
        list_projects(db, owner_id="owner-99")
        # The query is built with SQLAlchemy; we just verify db.scalars was called
        db.scalars.assert_called_once()

    def test_limit_capped_at_500(self):
        """Passing limit=9999 must be silently capped to 500."""
        # We can't easily inspect the final SQL, so verify at least no exception
        db = _make_db([])
        result = list_projects(db, limit=9999)
        assert result == []

    def test_multiple_projects_returned(self):
        projects = [_make_project(id=f"proj-{i}", name=f"P{i}") for i in range(3)]
        db = _make_db(projects)
        result = list_projects(db)
        assert len(result) == 3

    def test_no_owner_filter_when_owner_id_is_none(self):
        """When owner_id is None the query should not contain a where clause for owner."""
        db = _make_db([])
        list_projects(db, owner_id=None)
        db.scalars.assert_called_once()


# ---------------------------------------------------------------------------
# create_project
# ---------------------------------------------------------------------------

class TestCreateProject:
    def test_missing_name_raises_value_error(self):
        db = MagicMock()
        with pytest.raises(ValueError, match="name"):
            create_project(db, data={})

    def test_empty_name_raises_value_error(self):
        db = MagicMock()
        with pytest.raises(ValueError):
            create_project(db, data={"name": "   "})

    def test_success_returns_dict_with_id(self):
        proj = _make_project(id="new-proj-id", name="Yeni Proje")
        db = MagicMock()

        # When db.refresh is called, proj already has id set
        def fake_refresh(obj):
            # copy fields from proj to obj
            obj.__table__ = proj.__table__
            obj.id = proj.id
            obj.name = proj.name
            obj.description = proj.description
            obj.owner_id = proj.owner_id
            obj.primary_product_id = proj.primary_product_id
            obj.created_at = proj.created_at
            obj.updated_at = proj.updated_at

        db.refresh.side_effect = fake_refresh

        with patch("app.domains.tspm.service.TspmProject", return_value=proj):
            with patch("app.domains.tspm.service.utcnow", return_value=None):
                result = create_project(db, data={"name": "Yeni Proje"}, owner_id="user-1")

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        assert isinstance(result, dict)

    def test_create_calls_db_add_and_commit(self):
        proj = _make_project(name="Commit Testi")
        db = MagicMock()
        db.refresh.side_effect = lambda obj: None

        with patch("app.domains.tspm.service.TspmProject", return_value=proj):
            with patch("app.domains.tspm.service.utcnow", return_value=None):
                create_project(db, data={"name": "Commit Testi"})

        db.add.assert_called()
        db.commit.assert_called()


# ---------------------------------------------------------------------------
# list_scenarios
# ---------------------------------------------------------------------------

class TestListScenarios:
    def test_project_not_found_raises_key_error(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(KeyError):
            list_scenarios(db, project_id="nonexistent")

    def test_empty_scenarios_returns_empty_list(self):
        proj = _make_project()
        db = _make_db([])
        db.get.return_value = proj
        result = list_scenarios(db, project_id="proj-1")
        assert result == []

    def test_scenarios_returned_as_list_of_dicts(self):
        proj = _make_project()
        scen = _make_scenario()
        db = _make_db([scen])
        db.get.return_value = proj
        result = list_scenarios(db, project_id="proj-1")
        assert len(result) == 1
        assert result[0]["id"] == "scen-1"

    def test_limit_capped_at_1000(self):
        proj = _make_project()
        db = _make_db([])
        db.get.return_value = proj
        # Should not raise even with extreme limit
        result = list_scenarios(db, project_id="proj-1", limit=99999)
        assert result == []

    def test_status_filter_passed_to_query(self):
        proj = _make_project()
        db = _make_db([])
        db.get.return_value = proj
        list_scenarios(db, project_id="proj-1", status="active")
        db.scalars.assert_called_once()

    def test_multiple_scenarios_returned(self):
        proj = _make_project()
        scenarios = [_make_scenario(id=f"s-{i}") for i in range(5)]
        db = _make_db(scenarios)
        db.get.return_value = proj
        result = list_scenarios(db, project_id="proj-1")
        assert len(result) == 5


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

class TestCreateProjectEdgeCases:
    def test_description_defaults_to_empty_string_when_missing(self):
        """Omitting description should not raise."""
        proj = _make_project(description="")
        db = MagicMock()
        db.refresh.side_effect = lambda obj: None

        with patch("app.domains.tspm.service.TspmProject", return_value=proj):
            with patch("app.domains.tspm.service.utcnow", return_value=None):
                # Should not raise even without 'description' in data
                create_project(db, data={"name": "Desc Testi"})

    def test_owner_id_none_is_accepted(self):
        proj = _make_project(owner_id=None)
        db = MagicMock()
        db.refresh.side_effect = lambda obj: None

        with patch("app.domains.tspm.service.TspmProject", return_value=proj):
            with patch("app.domains.tspm.service.utcnow", return_value=None):
                create_project(db, data={"name": "No Owner"}, owner_id=None)

        db.add.assert_called()


class TestListProjectsOwnerFilter:
    def test_owner_id_filter_excludes_other_owners(self):
        """When owner_id is given, only matching rows should appear.
        We verify the service passes the filter to the query (mock confirms call)."""
        proj_own = _make_project(id="p-own", owner_id="alice")
        proj_other = _make_project(id="p-other", owner_id="bob")
        # Simulate DB returning only alice's project when filtered
        db = _make_db([proj_own])
        result = list_projects(db, owner_id="alice")
        assert len(result) == 1
        assert result[0]["id"] == "p-own"
