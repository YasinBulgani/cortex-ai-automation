"""
tests/unit/test_tm_routes.py
==============================
Test Management blueprint (/api/tm/…) için birim testler.

Tüm core.db fonksiyonları monkeypatch ile stub'lanır; Flask test client
üzerinden HTTP katmanı doğrulanır.
"""
from __future__ import annotations

import importlib
import sys
import pytest


# ── DB stub defaults ──────────────────────────────────────────────────────────

_DEFAULT_DB = {
    "create_project": lambda name, desc, uid: 1,
    "get_projects": lambda: [],
    "get_project": lambda pid: None,
    "update_project": lambda pid, name, desc: None,
    "delete_project": lambda pid: None,
    "create_module": lambda pid, name, desc: 10,
    "get_modules": lambda pid: [],
    "update_module": lambda mid, name, desc: None,
    "delete_module": lambda mid: None,
    "create_test_case": lambda **kw: 100,
    "get_test_cases": lambda mid: [],
    "get_test_case": lambda tc_id: None,
    "update_test_case": lambda tc_id, **kw: None,
    "delete_test_case": lambda tc_id: None,
    "add_test_case_step": lambda tc_id, action, expected: 50,
    "delete_test_case_step": lambda step_id: None,
    "bulk_create_test_cases": lambda mid, cases, uid: list(range(len(cases))),
    "create_sprint": lambda pid, name, rv, sd, ed: 20,
    "get_sprints": lambda pid: [],
    "delete_sprint": lambda sid: None,
    "create_manual_test_run": lambda **kw: 30,
    "get_manual_test_runs": lambda pid: [],
    "get_manual_test_run_results": lambda run_id: [],
    "update_run_result": lambda result_id, **kw: None,
    "close_manual_test_run": lambda run_id: None,
    "create_bug": lambda **kw: 40,
    "get_bugs": lambda pid: [],
    "update_bug_status": lambda bug_id, status: None,
    "delete_bug": lambda bug_id: None,
    "get_project_report": lambda pid: {"summary": {}},
}


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tm_client(monkeypatch):
    """Flask test client with all core.db functions stubbed."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-internal")

    # Remove cached modules so re-import picks up patches
    for mod_name in list(sys.modules.keys()):
        if "tm_routes" in mod_name or mod_name == "app":
            sys.modules.pop(mod_name, None)

    for fn_name, fn in _DEFAULT_DB.items():
        monkeypatch.setattr(f"core.db.{fn_name}", fn, raising=False)

    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


def _tm_client_with_db(monkeypatch, overrides: dict):
    """Helper — returns a function that yields client with custom DB overrides."""
    db = {**_DEFAULT_DB, **overrides}
    for fn_name, fn in db.items():
        monkeypatch.setattr(f"core.db.{fn_name}", fn, raising=False)


# ── GET /api/tm/projects ──────────────────────────────────────────────────────

def test_list_projects_empty(tm_client):
    """GET /api/tm/projects returns empty list when no projects exist."""
    r = tm_client.get("/api/tm/projects")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


def test_list_projects_with_data(monkeypatch, tm_client):
    """GET /api/tm/projects returns project list."""
    projects = [{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Beta"}]
    monkeypatch.setattr("core.db.get_projects", lambda: projects, raising=False)

    r = tm_client.get("/api/tm/projects")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 2
    assert data[0]["name"] == "Alpha"


# ── POST /api/tm/projects ─────────────────────────────────────────────────────

def test_create_project_missing_name_returns_400(tm_client):
    """POST /api/tm/projects without name returns 400."""
    r = tm_client.post(
        "/api/tm/projects",
        json={"description": "No name provided"},
        content_type="application/json",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_create_project_empty_name_returns_400(tm_client):
    """POST /api/tm/projects with empty name returns 400."""
    r = tm_client.post(
        "/api/tm/projects",
        json={"name": "   "},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_create_project_success(tm_client):
    """POST /api/tm/projects with valid name returns 201 and id."""
    r = tm_client.post(
        "/api/tm/projects",
        json={"name": "My Project", "description": "A project"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "id" in data


# ── GET /api/tm/projects/<id> ─────────────────────────────────────────────────

def test_get_project_not_found_returns_404(tm_client):
    """GET /api/tm/projects/<id> for missing project returns 404."""
    r = tm_client.get("/api/tm/projects/9999")
    assert r.status_code == 404
    data = r.get_json()
    assert "error" in data


def test_get_project_found_returns_data(monkeypatch, tm_client):
    """GET /api/tm/projects/<id> returns project when found."""
    project = {"id": 1, "name": "Alpha", "description": ""}
    monkeypatch.setattr("core.db.get_project", lambda pid: project, raising=False)

    r = tm_client.get("/api/tm/projects/1")
    assert r.status_code == 200
    data = r.get_json()
    assert data["name"] == "Alpha"


# ── PUT /api/tm/projects/<id> ─────────────────────────────────────────────────

def test_update_project_missing_name_returns_400(tm_client):
    """PUT /api/tm/projects/<id> without name returns 400."""
    r = tm_client.put(
        "/api/tm/projects/1",
        json={"description": "Updated"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_update_project_success(tm_client):
    """PUT /api/tm/projects/<id> with valid name returns ok."""
    r = tm_client.put(
        "/api/tm/projects/1",
        json={"name": "Updated Project"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── DELETE /api/tm/projects/<id> ──────────────────────────────────────────────

def test_delete_project_success(tm_client):
    """DELETE /api/tm/projects/<id> returns ok."""
    r = tm_client.delete("/api/tm/projects/1")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── GET /api/tm/projects/<id>/modules ────────────────────────────────────────

def test_list_modules_empty(tm_client):
    """GET /api/tm/projects/<id>/modules returns empty list."""
    r = tm_client.get("/api/tm/projects/1/modules")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


def test_list_modules_with_data(monkeypatch, tm_client):
    """GET /api/tm/projects/<id>/modules returns modules."""
    modules = [{"id": 10, "name": "Login Module"}]
    monkeypatch.setattr("core.db.get_modules", lambda pid: modules, raising=False)

    r = tm_client.get("/api/tm/projects/1/modules")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["name"] == "Login Module"


# ── POST /api/tm/projects/<id>/modules ───────────────────────────────────────

def test_create_module_missing_name_returns_400(tm_client):
    """POST /api/tm/projects/<id>/modules without name returns 400."""
    r = tm_client.post(
        "/api/tm/projects/1/modules",
        json={},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_create_module_success(tm_client):
    """POST /api/tm/projects/<id>/modules with valid name returns 201."""
    r = tm_client.post(
        "/api/tm/projects/1/modules",
        json={"name": "Auth Module"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "id" in data


# ── GET /api/tm/modules/<id>/testcases ───────────────────────────────────────

def test_list_testcases_empty(tm_client):
    """GET /api/tm/modules/<id>/testcases returns empty list."""
    r = tm_client.get("/api/tm/modules/10/testcases")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


def test_list_testcases_with_data(monkeypatch, tm_client):
    """GET /api/tm/modules/<id>/testcases returns test cases."""
    cases = [{"id": 100, "title": "Login with valid creds"}]
    monkeypatch.setattr("core.db.get_test_cases", lambda mid: cases, raising=False)

    r = tm_client.get("/api/tm/modules/10/testcases")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1


# ── POST /api/tm/modules/<id>/testcases ──────────────────────────────────────

def test_create_testcase_missing_title_returns_400(tm_client):
    """POST /api/tm/modules/<id>/testcases without title returns 400."""
    r = tm_client.post(
        "/api/tm/modules/10/testcases",
        json={"description": "No title"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_create_testcase_success(tm_client):
    """POST /api/tm/modules/<id>/testcases with valid payload returns 201."""
    r = tm_client.post(
        "/api/tm/modules/10/testcases",
        json={"title": "TC-001: Valid login", "priority": "P1"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "id" in data


def test_create_testcase_with_steps(tm_client):
    """POST /api/tm/modules/<id>/testcases with steps succeeds."""
    r = tm_client.post(
        "/api/tm/modules/10/testcases",
        json={
            "title": "TC-002: Full flow",
            "steps": [
                {"action": "Click login", "expected": "Login page shown"},
                {"action": "Enter creds", "expected": "Redirected to dashboard"},
            ],
        },
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


# ── GET /api/tm/testcases/<id> ────────────────────────────────────────────────

def test_get_testcase_not_found(tm_client):
    """GET /api/tm/testcases/<id> for missing case returns 404."""
    r = tm_client.get("/api/tm/testcases/9999")
    assert r.status_code == 404


def test_get_testcase_found(monkeypatch, tm_client):
    """GET /api/tm/testcases/<id> returns test case data."""
    tc = {"id": 100, "title": "TC-001", "steps": []}
    monkeypatch.setattr("core.db.get_test_case", lambda tc_id: tc, raising=False)

    r = tm_client.get("/api/tm/testcases/100")
    assert r.status_code == 200
    data = r.get_json()
    assert data["title"] == "TC-001"


# ── GET /api/tm/projects/<id>/report ─────────────────────────────────────────

def test_project_report_returns_data(monkeypatch, tm_client):
    """GET /api/tm/projects/<id>/report returns report structure."""
    report = {"summary": {"total": 10, "passed": 7, "failed": 3}}
    monkeypatch.setattr("core.db.get_project_report", lambda pid: report, raising=False)

    r = tm_client.get("/api/tm/projects/1/report")
    assert r.status_code == 200
    data = r.get_json()
    assert "summary" in data


def test_project_report_empty_project(tm_client):
    """GET /api/tm/projects/<id>/report for project with no data returns 200."""
    r = tm_client.get("/api/tm/projects/1/report")
    assert r.status_code == 200


# ── POST /api/tm/projects/<id>/runs ──────────────────────────────────────────

def test_create_run_missing_name_returns_400(tm_client):
    """POST /api/tm/projects/<id>/runs without name returns 400."""
    r = tm_client.post(
        "/api/tm/projects/1/runs",
        json={},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_create_run_success(tm_client):
    """POST /api/tm/projects/<id>/runs with valid name returns 201."""
    r = tm_client.post(
        "/api/tm/projects/1/runs",
        json={"name": "Sprint-1 Run"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "id" in data


# ── GET /api/tm/projects/<id>/runs ───────────────────────────────────────────

def test_list_runs_empty(tm_client):
    """GET /api/tm/projects/<id>/runs returns empty list."""
    r = tm_client.get("/api/tm/projects/1/runs")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


# ── GET /api/tm/projects/<id>/bugs ───────────────────────────────────────────

def test_list_bugs_empty(tm_client):
    """GET /api/tm/projects/<id>/bugs returns empty list."""
    r = tm_client.get("/api/tm/projects/1/bugs")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


def test_list_bugs_with_data(monkeypatch, tm_client):
    """GET /api/tm/projects/<id>/bugs returns bug list."""
    bugs = [{"id": 40, "title": "Login fails on Firefox", "severity": "High"}]
    monkeypatch.setattr("core.db.get_bugs", lambda pid: bugs, raising=False)

    r = tm_client.get("/api/tm/projects/1/bugs")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 1
    assert data[0]["severity"] == "High"


# ── POST /api/tm/bugs ─────────────────────────────────────────────────────────

def test_create_bug_missing_title_returns_400(tm_client):
    """POST /api/tm/bugs without title returns 400."""
    r = tm_client.post(
        "/api/tm/bugs",
        json={"severity": "Critical"},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_create_bug_success(tm_client):
    """POST /api/tm/bugs with valid title returns 201."""
    r = tm_client.post(
        "/api/tm/bugs",
        json={"title": "Button not clickable", "severity": "High"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert "id" in data


# ── PUT /api/tm/bugs/<id> ─────────────────────────────────────────────────────

def test_update_bug_status_missing_status_returns_400(tm_client):
    """PUT /api/tm/bugs/<id> without status returns 400."""
    r = tm_client.put(
        "/api/tm/bugs/40",
        json={},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_update_bug_status_success(tm_client):
    """PUT /api/tm/bugs/<id> with status returns ok."""
    r = tm_client.put(
        "/api/tm/bugs/40",
        json={"status": "Resolved"},
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── DELETE /api/tm/bugs/<id> ──────────────────────────────────────────────────

def test_delete_bug_success(tm_client):
    """DELETE /api/tm/bugs/<id> returns ok."""
    r = tm_client.delete("/api/tm/bugs/40")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True


# ── GET /api/tm/projects/<id>/sprints ────────────────────────────────────────

def test_list_sprints_empty(tm_client):
    """GET /api/tm/projects/<id>/sprints returns empty list."""
    r = tm_client.get("/api/tm/projects/1/sprints")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


def test_create_sprint_missing_name_returns_400(tm_client):
    """POST /api/tm/projects/<id>/sprints without name returns 400."""
    r = tm_client.post(
        "/api/tm/projects/1/sprints",
        json={},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_create_sprint_success(tm_client):
    """POST /api/tm/projects/<id>/sprints with name returns 201."""
    r = tm_client.post(
        "/api/tm/projects/1/sprints",
        json={"name": "Sprint 1", "release_version": "v1.0"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


# ── POST /api/tm/modules/<id>/testcases/bulk ─────────────────────────────────

def test_bulk_create_testcases_empty_returns_400(tm_client):
    """POST /api/tm/modules/<id>/testcases/bulk with no cases returns 400."""
    r = tm_client.post(
        "/api/tm/modules/10/testcases/bulk",
        json={"cases": []},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_bulk_create_testcases_success(tm_client):
    """POST /api/tm/modules/<id>/testcases/bulk with cases returns 201."""
    r = tm_client.post(
        "/api/tm/modules/10/testcases/bulk",
        json={"cases": [{"title": "TC-A"}, {"title": "TC-B"}]},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True
    assert data["created"] == 2


# ── POST /api/tm/testcases/<id>/steps ────────────────────────────────────────

def test_add_step_missing_fields_returns_400(tm_client):
    """POST /api/tm/testcases/<id>/steps without action returns 400."""
    r = tm_client.post(
        "/api/tm/testcases/100/steps",
        json={"action": ""},
        content_type="application/json",
    )
    assert r.status_code == 400


def test_add_step_success(tm_client):
    """POST /api/tm/testcases/<id>/steps with valid fields returns 201."""
    r = tm_client.post(
        "/api/tm/testcases/100/steps",
        json={"action": "Click submit", "expected": "Form submitted"},
        content_type="application/json",
    )
    assert r.status_code == 201
    data = r.get_json()
    assert data["ok"] is True


# ── GET /api/tm/runs/<id>/results ────────────────────────────────────────────

def test_get_run_results_empty(tm_client):
    """GET /api/tm/runs/<id>/results returns empty list."""
    r = tm_client.get("/api/tm/runs/30/results")
    assert r.status_code == 200
    data = r.get_json()
    assert data == []


# ── POST /api/tm/runs/<id>/close ─────────────────────────────────────────────

def test_close_run_success(tm_client):
    """POST /api/tm/runs/<id>/close returns ok."""
    r = tm_client.post("/api/tm/runs/30/close")
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
